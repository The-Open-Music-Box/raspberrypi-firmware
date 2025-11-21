# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""DDD Naming Conventions Tests.

These tests verify that classes, files, and modules follow DDD naming conventions
to maintain consistency and clarity in the codebase.
"""

import pytest
import os
import re
from .helpers import (
    get_all_python_files,
    extract_class_names,
    get_project_root,
    check_naming_conventions
)


class TestNamingConventions:
    """Test suite for DDD naming conventions."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test environment."""
        self.project_root = get_project_root()

    def test_application_services_naming(self):
        """Verify application services follow naming conventions."""
        violations = []

        app_services_path = os.path.join(self.project_root, "app", "src", "application", "services")
        if os.path.exists(app_services_path):
            service_files = get_all_python_files(app_services_path)

            for file_path in service_files:
                if "__init__.py" in file_path:
                    continue

                # File naming convention - allow exceptions for coordinator and manager classes
                file_name = os.path.basename(file_path)
                if not (file_name.endswith("application_service.py") or
                       file_name.endswith("coordinator.py") or
                       file_name.endswith("manager.py")):
                    violations.append(f"❌ Application service file should end with 'application_service.py': {file_path}")

                # Class naming convention
                classes = extract_class_names(file_path)
                for class_name in classes:
                    # Allow exceptions for Coordinator, Manager, and Enum classes
                    if ("Service" in class_name and
                        not class_name.endswith("ApplicationService") and
                        not class_name.endswith("Coordinator") and
                        not class_name.endswith("Manager") and
                        not class_name.endswith("Type")):
                        violations.append(f"❌ Application service class should end with 'ApplicationService': {file_path}::{class_name}")

        assert len(violations) == 0, f"""
        ❌ APPLICATION SERVICE NAMING VIOLATIONS!

        Application services should follow these conventions:
        - File: *_application_service.py
        - Class: *ApplicationService

        Violations found:
        {chr(10).join(violations)}

        ✅ Examples:
        - File: playlist_application_service.py
        - Class: PlaylistApplicationService
        """

    def test_domain_services_naming(self):
        """Verify domain services follow naming conventions."""
        violations = []

        domain_services_path = os.path.join(self.project_root, "app", "src", "domain", "services")
        if os.path.exists(domain_services_path):
            service_files = get_all_python_files(domain_services_path)

            for file_path in service_files:
                if "__init__.py" in file_path:
                    continue

                classes = extract_class_names(file_path)
                for class_name in classes:
                    if "Service" in class_name:
                        # Domain services can end with "Service" or "DomainService"
                        if not (class_name.endswith("Service") or class_name.endswith("DomainService")):
                            violations.append(f"❌ Domain service should end with 'Service' or 'DomainService': {file_path}::{class_name}")

        assert len(violations) == 0, f"""
        ❌ DOMAIN SERVICE NAMING VIOLATIONS!

        Domain services should follow these conventions:
        - Class: *Service or *DomainService

        Violations found:
        {chr(10).join(violations)}

        ✅ Examples:
        - PlaylistService (simple)
        - PlaylistDomainService (explicit)
        """

    def test_repository_interfaces_naming(self):
        """Verify repository interfaces follow naming conventions."""
        violations = []

        # Check domain repositories (should be interfaces)
        domain_repos_path = os.path.join(self.project_root, "app", "src", "domain", "repositories")
        if os.path.exists(domain_repos_path):
            repo_files = get_all_python_files(domain_repos_path)

            for file_path in repo_files:
                if "__init__.py" in file_path:
                    continue

                classes = extract_class_names(file_path)
                for class_name in classes:
                    if "Repository" in class_name:
                        # Domain repositories should be protocols/interfaces
                        if not (class_name.endswith("Protocol") or
                                class_name.endswith("Interface") or
                                class_name.endswith("Repository")):
                            violations.append(f"❌ Domain repository should end with 'Protocol', 'Interface', or 'Repository': {file_path}::{class_name}")

        # Check infrastructure repositories (should be implementations)
        infra_repos_path = os.path.join(self.project_root, "app", "src", "infrastructure", "repositories")
        if os.path.exists(infra_repos_path):
            repo_files = get_all_python_files(infra_repos_path)

            for file_path in repo_files:
                if "__init__.py" in file_path:
                    continue

                classes = extract_class_names(file_path)
                for class_name in classes:
                    if "Repository" in class_name:
                        # Infrastructure repositories should indicate implementation
                        if class_name.endswith("Protocol") or class_name.endswith("Interface"):
                            violations.append(f"❌ Infrastructure repository should be concrete implementation: {file_path}::{class_name}")

        assert len(violations) == 0, f"""
        ❌ REPOSITORY NAMING VIOLATIONS!

        Repository naming conventions:
        - Domain: PlaylistRepositoryProtocol (interface)
        - Infrastructure: PlaylistRepository (implementation)

        Violations found:
        {chr(10).join(violations)}

        ✅ This ensures clear separation between contracts and implementations.
        """

    def test_entity_and_model_naming(self):
        """Verify entities and models follow naming conventions."""
        violations = []

        domain_models_path = os.path.join(self.project_root, "app", "src", "domain", "models")
        if os.path.exists(domain_models_path):
            model_files = get_all_python_files(domain_models_path)

            for file_path in model_files:
                if "__init__.py" in file_path:
                    continue

                # File naming: should be singular nouns
                file_name = os.path.basename(file_path).replace('.py', '')
                if re.search(r's$', file_name) and not file_name.endswith('ss'):
                    violations.append(f"⚠️ Model file should use singular noun: {file_path}")

                # Class naming: should be PascalCase nouns
                classes = extract_class_names(file_path)
                for class_name in classes:
                    # Check for proper PascalCase
                    if not re.match(r'^[A-Z][a-zA-Z0-9]*$', class_name):
                        violations.append(f"❌ Model class should be PascalCase: {file_path}::{class_name}")

                    # Check for inappropriate suffixes in domain models
                    inappropriate_suffixes = ["DTO", "DAO", "Table", "Entity"]
                    for suffix in inappropriate_suffixes:
                        if class_name.endswith(suffix):
                            violations.append(f"❌ Domain model should not have suffix '{suffix}': {file_path}::{class_name}")

        assert len(violations) == 0, f"""
        ❌ ENTITY/MODEL NAMING VIOLATIONS!

        Entity and model naming conventions:
        - File: singular_noun.py (e.g., playlist.py, track.py)
        - Class: PascalCase noun (e.g., Playlist, Track)
        - Avoid: DTO, DAO, Table suffixes in domain

        Violations found:
        {chr(10).join(violations)}

        ✅ Domain models represent business concepts, not database tables.
        """

    def test_controller_naming(self):
        """Verify controllers follow naming conventions."""
        violations = []

        # Check application controllers
        app_controllers_path = os.path.join(self.project_root, "app", "src", "application", "controllers")
        if os.path.exists(app_controllers_path):
            controller_files = get_all_python_files(app_controllers_path)

            for file_path in controller_files:
                if "__init__.py" in file_path:
                    continue

                # File naming
                file_name = os.path.basename(file_path)
                if not file_name.endswith("controller.py"):
                    violations.append(f"❌ Controller file should end with 'controller.py': {file_path}")

                # Class naming
                classes = extract_class_names(file_path)
                for class_name in classes:
                    if "Controller" in class_name and not class_name.endswith("Controller"):
                        violations.append(f"❌ Controller class should end with 'Controller': {file_path}::{class_name}")

        # Check routes (should not contain "Controller" in name)
        routes_path = os.path.join(self.project_root, "app", "src", "routes")
        if os.path.exists(routes_path):
            route_files = get_all_python_files(routes_path)

            for file_path in route_files:
                if "__init__.py" in file_path:
                    continue

                classes = extract_class_names(file_path)
                for class_name in classes:
                    if class_name.endswith("Controller"):
                        violations.append(f"⚠️ Route class should not be named 'Controller': {file_path}::{class_name}")

        assert len(violations) == 0, f"""
        ❌ CONTROLLER NAMING VIOLATIONS!

        Controller naming conventions:
        - Application Controllers: *Controller (unified_controller.py)
        - Route Handlers: *Routes or *Handler (playlist_routes.py)

        Violations found:
        {chr(10).join(violations)}

        ✅ This separates HTTP routing from application coordination.
        """

    def test_factory_naming(self):
        """Verify factories follow naming conventions."""
        violations = []

        all_paths = [
            os.path.join(self.project_root, "app", "src", "domain"),
            os.path.join(self.project_root, "app", "src", "application"),
            os.path.join(self.project_root, "app", "src", "infrastructure")
        ]

        for path in all_paths:
            if os.path.exists(path):
                files = get_all_python_files(path)
                for file_path in files:
                    if "factory" in file_path.lower():
                        # File naming
                        file_name = os.path.basename(file_path)
                        if not file_name.endswith("factory.py"):
                            violations.append(f"❌ Factory file should end with 'factory.py': {file_path}")

                        # Class naming
                        classes = extract_class_names(file_path)
                        for class_name in classes:
                            if "Factory" in class_name and not class_name.endswith("Factory"):
                                violations.append(f"❌ Factory class should end with 'Factory': {file_path}::{class_name}")

        assert len(violations) == 0, f"""
        ❌ FACTORY NAMING VIOLATIONS!

        Factory naming conventions:
        - File: *_factory.py
        - Class: *Factory

        Violations found:
        {chr(10).join(violations)}

        ✅ Examples: AudioFactory, PlaylistFactory
        """

    def test_exception_naming(self):
        """Verify exceptions follow naming conventions."""
        violations = []

        all_paths = [
            os.path.join(self.project_root, "app", "src", "domain"),
            os.path.join(self.project_root, "app", "src", "application"),
            os.path.join(self.project_root, "app", "src", "infrastructure"),
            os.path.join(self.project_root, "app", "src", "monitoring")
        ]

        for path in all_paths:
            if os.path.exists(path):
                files = get_all_python_files(path)
                for file_path in files:
                    if "exception" in file_path.lower() or "error" in file_path.lower():
                        classes = extract_class_names(file_path)
                        for class_name in classes:
                            # Skip non-exception classes (Enums, dataclasses, handlers, protocols, etc.)
                            if (class_name.endswith("Severity") or class_name.endswith("Category") or
                                class_name.endswith("Context") or class_name.endswith("Record") or
                                class_name.endswith("Handler") or class_name.endswith("Protocol")):
                                continue

                            # Exceptions should end with "Exception" or "Error"
                            if (class_name not in ["Exception", "Error"] and
                                not class_name.endswith("Exception") and
                                not class_name.endswith("Error") and
                                ("Exception" in class_name or "Error" in class_name)):
                                violations.append(f"❌ Exception class should end with 'Exception' or 'Error': {file_path}::{class_name}")

        assert len(violations) == 0, f"""
        ❌ EXCEPTION NAMING VIOLATIONS!

        Exception naming conventions:
        - Class: *Exception or *Error
        - Examples: PlaylistNotFoundException, ValidationError

        Violations found:
        {chr(10).join(violations)}

        ✅ Clear exception naming improves error handling.
        """

    def test_protocol_interface_naming(self):
        """Verify protocols and interfaces follow naming conventions."""
        violations = []

        domain_protocols_path = os.path.join(self.project_root, "app", "src", "domain", "protocols")
        if os.path.exists(domain_protocols_path):
            protocol_files = get_all_python_files(domain_protocols_path)

            for file_path in protocol_files:
                if "__init__.py" in file_path:
                    continue

                # File naming
                file_name = os.path.basename(file_path)
                if not file_name.endswith("protocol.py"):
                    violations.append(f"❌ Protocol file should end with 'protocol.py': {file_path}")

                # Class naming
                classes = extract_class_names(file_path)
                for class_name in classes:
                    # Skip support classes that aren't actual protocols
                    if (class_name.endswith("Event") or class_name.endswith("State") or
                        class_name.startswith("Mock") or class_name.endswith("Notifier")):
                        continue

                    if not (class_name.endswith("Protocol") or class_name.endswith("Interface")):
                        violations.append(f"❌ Protocol class should end with 'Protocol' or 'Interface': {file_path}::{class_name}")

        assert len(violations) == 0, f"""
        ❌ PROTOCOL/INTERFACE NAMING VIOLATIONS!

        Protocol naming conventions:
        - File: *_protocol.py
        - Class: *Protocol or *Interface

        Violations found:
        {chr(10).join(violations)}

        ✅ Examples: AudioBackendProtocol, AudioEngineProtocol
        """

    def test_overall_naming_consistency(self):
        """Run comprehensive naming convention check."""
        violations = check_naming_conventions()

        # Filter out warnings and only keep errors
        error_violations = [v for v in violations if v.startswith("❌")]

        assert len(error_violations) == 0, f"""
        ❌ NAMING CONVENTION VIOLATIONS!

        Comprehensive naming analysis found violations:

        {chr(10).join(error_violations)}

        ✅ Consistent naming improves code readability and maintainability.
        """

    def test_file_and_directory_naming(self):
        """Verify file and directory names follow conventions."""
        violations = []

        app_src_path = os.path.join(self.project_root, "app", "src")

        # Check directory naming (should be lowercase with underscores)
        for root, dirs, files in os.walk(app_src_path):
            for directory in dirs:
                if not re.match(r'^[a-z][a-z0-9_]*$', directory) and directory != "__pycache__":
                    violations.append(f"❌ Directory should be lowercase_with_underscores: {os.path.join(root, directory)}")

        # Check file naming (should be lowercase with underscores)
        python_files = get_all_python_files(app_src_path)
        for file_path in python_files:
            file_name = os.path.basename(file_path)
            if file_name != "__init__.py":
                name_without_ext = file_name.replace('.py', '')
                # Allow migration files with numeric prefixes (e.g., 001_migration_name.py)
                is_migration = 'migrations' in file_path
                if is_migration:
                    # For migration files, allow pattern: NNN_lowercase_name
                    if not re.match(r'^(\d{3}_)?[a-z][a-z0-9_]*$', name_without_ext):
                        violations.append(f"❌ Migration file should follow pattern NNN_lowercase_name: {file_path}")
                else:
                    if not re.match(r'^[a-z][a-z0-9_]*$', name_without_ext):
                        violations.append(f"❌ File should be lowercase_with_underscores: {file_path}")

        assert len(violations) == 0, f"""
        ❌ FILE/DIRECTORY NAMING VIOLATIONS!

        File and directory naming conventions:
        - Use lowercase_with_underscores
        - Avoid CamelCase or kebab-case

        Violations found:
        {chr(10).join(violations)}

        ✅ Consistent naming follows Python PEP 8 standards.
        """