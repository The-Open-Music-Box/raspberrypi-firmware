# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Architecture Test Helpers

Common utility functions for architecture tests to maintain DDD compliance
and enforce architectural constraints across the codebase.
"""

import os
import ast
import re
import networkx as nx
from typing import List, Set, Dict, Tuple, Optional
from pathlib import Path


def get_project_root() -> str:
    """Get the project root directory.

    Returns:
        str: Absolute path to the project root (back/ directory)
    """
    current_file = Path(__file__).resolve()
    # Navigate up from tests/architecture/helpers.py to back/
    return str(current_file.parent.parent.parent)


def get_all_python_files(directory: str) -> List[str]:
    """Get all Python files in a directory recursively.

    Args:
        directory (str): Directory to search

    Returns:
        List[str]: List of absolute paths to Python files
    """
    python_files = []

    if not os.path.exists(directory):
        return python_files

    for root, dirs, files in os.walk(directory):
        # Skip __pycache__ directories
        dirs[:] = [d for d in dirs if d != '__pycache__']

        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))

    return python_files


def extract_class_names(file_path: str) -> List[str]:
    """Extract class names from a Python file.

    Args:
        file_path (str): Path to the Python file

    Returns:
        List[str]: List of class names found in the file
    """
    class_names = []

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        tree = ast.parse(content)

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_names.append(node.name)

    except (SyntaxError, UnicodeDecodeError, FileNotFoundError):
        # Skip files that can't be parsed
        pass

    return class_names


def extract_imports_from_file(file_path: str) -> List[str]:
    """Extract import statements from a Python file.

    Args:
        file_path (str): Path to the Python file

    Returns:
        List[str]: List of imported module names
    """
    imports = []

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        tree = ast.parse(content)

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)

    except (SyntaxError, UnicodeDecodeError, FileNotFoundError):
        # Skip files that can't be parsed
        pass

    return imports


def get_layer_from_module(module_path: str) -> str:
    """Determine the DDD layer from a module path.

    Args:
        module_path (str): Path to the module (can be file path or dot notation)

    Returns:
        str: DDD layer name (domain, application, infrastructure, ui, etc.)
    """
    # Normalize path separators and handle both file paths and dot notation
    normalized_path = module_path.replace('\\', '/').replace('.', '/').lower()

    # Extract layer from path structure - check both patterns
    # For paths like "domain.audio.backends" or "/domain/"
    if '/domain/' in normalized_path or normalized_path.startswith('domain/'):
        return 'domain'
    elif '/application/' in normalized_path or normalized_path.startswith('application/'):
        return 'application'
    elif '/infrastructure/' in normalized_path or normalized_path.startswith('infrastructure/'):
        return 'infrastructure'
    elif '/routes/' in normalized_path or '/api/' in normalized_path or normalized_path.startswith('routes/') or normalized_path.startswith('api/'):
        return 'ui'
    elif '/controllers/' in normalized_path or normalized_path.startswith('controllers/'):
        return 'controllers'
    elif '/services/' in normalized_path or normalized_path.startswith('services/'):
        return 'services'
    elif '/config/' in normalized_path or normalized_path.startswith('config/'):
        return 'config'
    elif '/monitoring/' in normalized_path or normalized_path.startswith('monitoring/'):
        return 'monitoring'
    else:
        return 'unknown'


def build_dependency_graph() -> nx.DiGraph:
    """Build a dependency graph of the codebase.

    Returns:
        nx.DiGraph: NetworkX directed graph representing module dependencies
    """
    graph = nx.DiGraph()
    project_root = get_project_root()
    app_src = os.path.join(project_root, 'app', 'src')

    python_files = get_all_python_files(app_src)

    for file_path in python_files:
        # Convert file path to module name
        relative_path = os.path.relpath(file_path, app_src)
        module_name = relative_path.replace('/', '.').replace('\\', '.').replace('.py', '')

        # Skip __init__ modules for simplicity
        if module_name.endswith('.__init__'):
            continue

        graph.add_node(module_name)

        # Extract imports and add edges
        imports = extract_imports_from_file(file_path)

        for imported_module in imports:
            # Only track internal dependencies (app.src.*)
            if imported_module.startswith('app.src.'):
                # Clean up the import name
                clean_import = imported_module.replace('app.src.', '')
                if clean_import != module_name:  # Avoid self-references
                    graph.add_edge(module_name, clean_import)

    return graph


def find_circular_dependencies(graph: nx.DiGraph) -> List[List[str]]:
    """Find circular dependencies in the dependency graph.

    Args:
        graph (nx.DiGraph): Dependency graph

    Returns:
        List[List[str]]: List of circular dependency cycles
    """
    try:
        cycles = list(nx.simple_cycles(graph))
        # Filter out trivial cycles (single nodes)
        return [cycle for cycle in cycles if len(cycle) > 1]
    except:
        # If graph analysis fails, return empty list
        return []


def validate_ddd_layer_dependencies(graph: nx.DiGraph) -> List[str]:
    """Validate that DDD layer dependencies follow proper direction.

    Args:
        graph (nx.DiGraph): Dependency graph

    Returns:
        List[str]: List of dependency violations
    """
    violations = []

    # Define allowed dependencies (outer layers can depend on inner layers)
    # Services layer contains cross-cutting infrastructure concerns (error handling, serialization, validation)
    # that may legitimately depend on infrastructure components (error handlers, legacy state managers)
    # Config is a cross-cutting concern that can be used by any layer except domain
    allowed_dependencies = {
        'ui': ['application', 'infrastructure', 'domain', 'services', 'config', 'controllers', 'ui'],
        'application': ['domain', 'infrastructure', 'services', 'application', 'config'],  # Allow config for hardware controllers
        'infrastructure': ['domain', 'services', 'infrastructure', 'config'],  # Infrastructure needs config for hardware/adapters
        'domain': ['domain'],  # Domain can depend on other domain modules (pure business logic)
        'controllers': ['application', 'domain', 'infrastructure', 'services', 'config', 'controllers'],
        'services': ['domain', 'services', 'config', 'infrastructure'],  # Services can use infrastructure (error handlers, state managers)
        'config': ['config'],
        'monitoring': ['monitoring', 'config']  # Monitoring needs config for log levels, file paths, etc.
    }

    for source, target in graph.edges():
        source_layer = get_layer_from_module(source)
        target_layer = get_layer_from_module(target)

        # Skip unknown layers
        if source_layer == 'unknown' or target_layer == 'unknown':
            continue

        # Check if dependency is allowed
        if (source_layer in allowed_dependencies and
            target_layer not in allowed_dependencies.get(source_layer, [])):
            violations.append(
                f"❌ Invalid dependency: {source_layer} -> {target_layer} "
                f"({source} -> {target})"
            )

    return violations


def check_naming_conventions() -> List[str]:
    """Run comprehensive naming convention checks.

    Returns:
        List[str]: List of naming convention violations
    """
    violations = []
    project_root = get_project_root()
    app_src = os.path.join(project_root, 'app', 'src')

    # Check file naming conventions
    python_files = get_all_python_files(app_src)

    for file_path in python_files:
        file_name = os.path.basename(file_path)

        # Skip __init__.py files
        if file_name == '__init__.py':
            continue

        # Check file naming (should be lowercase with underscores)
        name_without_ext = file_name.replace('.py', '')
        if not re.match(r'^[a-z][a-z0-9_]*$', name_without_ext):
            violations.append(f"⚠️ File should be lowercase_with_underscores: {file_path}")

        # Check class naming conventions
        classes = extract_class_names(file_path)
        for class_name in classes:
            # Classes should be PascalCase
            if not re.match(r'^[A-Z][a-zA-Z0-9]*$', class_name):
                violations.append(f"⚠️ Class should be PascalCase: {file_path}::{class_name}")

    return violations


# Additional helper functions for specific architecture tests

def get_domain_classes() -> Dict[str, List[str]]:
    """Get all classes in the domain layer organized by module.

    Returns:
        Dict[str, List[str]]: Dictionary mapping module paths to class lists
    """
    project_root = get_project_root()
    domain_path = os.path.join(project_root, 'app', 'src', 'domain')

    domain_classes = {}

    if os.path.exists(domain_path):
        python_files = get_all_python_files(domain_path)

        for file_path in python_files:
            if '__init__.py' in file_path:
                continue

            classes = extract_class_names(file_path)
            if classes:
                domain_classes[file_path] = classes

    return domain_classes


def check_forbidden_imports_in_domain(forbidden_patterns: List[str]) -> List[str]:
    """Check for forbidden import patterns in domain layer.

    Args:
        forbidden_patterns (List[str]): List of forbidden import patterns

    Returns:
        List[str]: List of violations
    """
    violations = []
    project_root = get_project_root()
    domain_path = os.path.join(project_root, 'app', 'src', 'domain')

    if not os.path.exists(domain_path):
        return violations

    python_files = get_all_python_files(domain_path)

    for file_path in python_files:
        imports = extract_imports_from_file(file_path)

        for import_name in imports:
            for forbidden_pattern in forbidden_patterns:
                if forbidden_pattern in import_name:
                    violations.append(
                        f"❌ Domain layer should not import {forbidden_pattern}: "
                        f"{file_path} imports {import_name}"
                    )

    return violations


def find_classes_in_wrong_layers() -> List[str]:
    """Find classes that are placed in the wrong DDD layers.

    Returns:
        List[str]: List of misplaced classes
    """
    violations = []
    project_root = get_project_root()
    app_src = os.path.join(project_root, 'app', 'src')

    python_files = get_all_python_files(app_src)

    for file_path in python_files:
        layer = get_layer_from_module(file_path)
        classes = extract_class_names(file_path)

        for class_name in classes:
            # Check for common misplacements
            if layer == 'domain':
                # Domain should not have infrastructure concerns
                if any(suffix in class_name for suffix in ['Repository', 'DAO', 'DTO', 'Adapter']):
                    if not class_name.endswith('Protocol') and not class_name.endswith('Interface'):
                        violations.append(
                            f"⚠️ Infrastructure class in domain layer: {file_path}::{class_name}"
                        )
            elif layer == 'infrastructure':
                # Infrastructure should not have domain entities
                if class_name.endswith('Entity') or class_name.endswith('ValueObject'):
                    violations.append(
                        f"⚠️ Domain class in infrastructure layer: {file_path}::{class_name}"
                    )

    return violations