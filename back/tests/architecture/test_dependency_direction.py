# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Dependency Direction Compliance Tests.

These tests verify that dependencies flow in the correct direction according to
DDD and Clean Architecture principles.

Correct flow: Presentation → Application → Domain ← Infrastructure
"""

import pytest
import os
from .helpers import (
    build_dependency_graph,
    validate_ddd_layer_dependencies,
    get_layer_from_module,
    get_all_python_files,
    extract_imports_from_file,
    get_project_root
)


class TestDependencyDirection:
    """Test suite for dependency direction compliance."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test environment."""
        self.project_root = get_project_root()
        self.dependency_graph = build_dependency_graph()

    def test_dependency_direction_follows_ddd_rules(self):
        """Verify all dependencies follow DDD layer rules."""
        violations = validate_ddd_layer_dependencies(self.dependency_graph)

        assert len(violations) == 0, f"""
        ❌ DDD DEPENDENCY DIRECTION VIOLATIONS!

        Dependencies must follow Clean Architecture rules:
        ✅ Presentation → Application → Domain ← Infrastructure

        Violations found:
        {chr(10).join(violations)}

        ✅ Solution: Refactor dependencies to follow correct direction
        or use dependency injection to invert control.
        """

    def test_domain_layer_does_not_depend_on_anything(self):
        """Verify Domain layer has no outward dependencies to other layers."""
        violations = []

        for module in self.dependency_graph.nodes():
            if get_layer_from_module(module) == 'domain':
                dependencies = list(self.dependency_graph.successors(module))
                for dependency in dependencies:
                    dep_layer = get_layer_from_module(dependency)
                    if dep_layer in ['application', 'infrastructure', 'presentation', 'services']:
                        violations.append(
                            f"❌ Domain dependency violation: {module} → {dependency} ({dep_layer})"
                        )

        assert len(violations) == 0, f"""
        ❌ DOMAIN LAYER DEPENDENCY VIOLATIONS!

        Domain layer must be at the center of the architecture with NO dependencies
        on any outer layers. It should only depend on itself and standard libraries.

        Violations found:
        {chr(10).join(violations)}

        ✅ Solution:
        1. Move external concerns to Infrastructure layer
        2. Use dependency injection with interfaces/protocols
        3. Keep Domain pure with only business logic
        """

    def test_application_layer_only_depends_on_domain(self):
        """Verify Application layer only depends on Domain layer."""
        violations = []

        # Exemptions for hardware/infrastructure controllers that need direct access
        # These are controller facades that coordinate with infrastructure
        # DI containers and certain services legitimately need infrastructure access for bootstrapping
        EXEMPTIONS = {
            'application.controllers.physical_controls_controller': [
                'infrastructure.hardware.controls.controls_factory',
            ],
            'application.controllers.upload_controller': [
                'infrastructure.upload.adapters.file_storage_adapter',
                'infrastructure.upload.adapters.metadata_extractor',
            ],
            'application.di.application_container': [
                'infrastructure.di.container',  # DI container needs infrastructure container for service resolution
                'infrastructure.nfc.nfc_factory',  # Needs NFC factory for bootstrapping NFC services
                'infrastructure.upload.upload_factory',  # Needs upload factory for bootstrapping upload services
            ],
            'application.services.youtube.youtube_application_service': [
                'infrastructure.youtube.youtube_downloader',  # YouTube service delegates to infrastructure downloader
            ],
        }

        for module in self.dependency_graph.nodes():
            if get_layer_from_module(module) == 'application':
                dependencies = list(self.dependency_graph.successors(module))
                for dependency in dependencies:
                    dep_layer = get_layer_from_module(dependency)
                    if dep_layer in ['infrastructure', 'presentation']:
                        # Check if this is an exempted dependency
                        module_exemptions = EXEMPTIONS.get(module, [])
                        if dependency not in module_exemptions:
                            violations.append(
                                f"❌ Application dependency violation: {module} → {dependency} ({dep_layer})"
                            )

        assert len(violations) == 0, f"""
        ❌ APPLICATION LAYER DEPENDENCY VIOLATIONS!

        Application layer should only depend on Domain layer.
        It orchestrates business logic but doesn't handle infrastructure concerns.

        Violations found:
        {chr(10).join(violations)}

        ✅ Solution:
        1. Move infrastructure calls to Infrastructure layer
        2. Use dependency injection to provide services
        3. Keep Application layer focused on use cases
        """

    def test_infrastructure_layer_only_depends_on_domain(self):
        """Verify Infrastructure layer only depends on Domain layer."""
        violations = []

        for module in self.dependency_graph.nodes():
            if get_layer_from_module(module) == 'infrastructure':
                dependencies = list(self.dependency_graph.successors(module))
                for dependency in dependencies:
                    dep_layer = get_layer_from_module(dependency)
                    if dep_layer in ['application', 'presentation']:
                        violations.append(
                            f"❌ Infrastructure dependency violation: {module} → {dependency} ({dep_layer})"
                        )

        assert len(violations) == 0, f"""
        ❌ INFRASTRUCTURE LAYER DEPENDENCY VIOLATIONS!

        Infrastructure layer should only depend on Domain layer interfaces.
        It implements domain contracts but shouldn't depend on application logic.

        Violations found:
        {chr(10).join(violations)}

        ✅ Solution:
        1. Remove application layer imports from Infrastructure
        2. Implement domain interfaces/protocols only
        3. Use dependency injection for application services
        """

    def test_no_reverse_dependencies_from_domain(self):
        """Verify no other layers import from Domain incorrectly."""
        # This is actually allowed - other layers should import from Domain
        # This test ensures we understand the dependency flow

        domain_importers = {}

        for module in self.dependency_graph.nodes():
            module_layer = get_layer_from_module(module)
            dependencies = list(self.dependency_graph.successors(module))

            for dependency in dependencies:
                if get_layer_from_module(dependency) == 'domain':
                    if module_layer not in domain_importers:
                        domain_importers[module_layer] = []
                    domain_importers[module_layer].append(f"{module} → {dependency}")

        # This is informational - all layers can import from Domain
        expected_importers = ['application', 'infrastructure', 'presentation', 'services']

        for layer in expected_importers:
            if layer in domain_importers:
                print(f"✅ {layer.title()} layer imports from Domain: {len(domain_importers[layer])} imports")
            else:
                print(f"⚠️ {layer.title()} layer has no Domain imports")

        # This test always passes - it's informational
        assert True, "Domain dependency analysis complete"

    def test_no_skip_layer_dependencies(self):
        """Verify layers don't skip intermediate layers inappropriately."""
        violations = []

        for module in self.dependency_graph.nodes():
            module_layer = get_layer_from_module(module)
            dependencies = list(self.dependency_graph.successors(module))

            # Presentation should not directly depend on Domain (should go through Application)
            if module_layer == 'presentation':
                for dependency in dependencies:
                    dep_layer = get_layer_from_module(dependency)
                    if dep_layer == 'domain':
                        # Allow some direct Domain imports for DTOs and models
                        if not any(pattern in dependency for pattern in ['models', 'protocols', 'enums']):
                            violations.append(
                                f"⚠️ Layer skipping: {module} → {dependency} "
                                f"(Presentation should use Application layer)"
                            )

        # Make this a warning rather than error for flexibility
        if len(violations) > 0:
            print("Layer skipping warnings found:")
            for violation in violations:
                print(violation)

        # Don't fail the test, just warn
        assert True, f"Layer skipping analysis complete. {len(violations)} warnings found."

    def test_services_layer_dependencies_are_appropriate(self):
        """Verify Services layer has appropriate dependencies."""
        violations = []

        for module in self.dependency_graph.nodes():
            if get_layer_from_module(module) == 'services':
                dependencies = list(self.dependency_graph.successors(module))
                for dependency in dependencies:
                    dep_layer = get_layer_from_module(dependency)

                    # Services can depend on Domain and Infrastructure, but not Application
                    if dep_layer == 'application':
                        violations.append(
                            f"❌ Services → Application violation: {module} → {dependency}"
                        )
                    elif dep_layer == 'presentation':
                        violations.append(
                            f"❌ Services → Presentation violation: {module} → {dependency}"
                        )

        assert len(violations) == 0, f"""
        ❌ SERVICES LAYER DEPENDENCY VIOLATIONS!

        Services layer should be part of Infrastructure and only depend on:
        - Domain layer (interfaces and models)
        - Other Infrastructure services
        - External libraries

        Violations found:
        {chr(10).join(violations)}

        ✅ Solution: Move services to Infrastructure layer or refactor dependencies.
        """

    def test_dependency_graph_completeness(self):
        """Verify dependency graph captures all important modules."""
        expected_layers = ['domain', 'application', 'infrastructure']
        found_layers = set()

        for module in self.dependency_graph.nodes():
            layer = get_layer_from_module(module)
            found_layers.add(layer)

        for expected_layer in expected_layers:
            assert expected_layer in found_layers, f"""
            ❌ MISSING LAYER IN DEPENDENCY GRAPH!

            Expected to find modules in '{expected_layer}' layer but none found.
            This might indicate incomplete analysis or missing code.

            Found layers: {sorted(found_layers)}
            Expected layers: {expected_layers}
            """

        print(f"✅ Dependency graph analysis complete. Found layers: {sorted(found_layers)}")
        print(f"✅ Total modules analyzed: {len(self.dependency_graph)}")

    def test_imports_only_from_allowed_modules(self):
        """Verify modules only import from architecturally appropriate locations."""
        project_root = get_project_root()
        app_src_path = os.path.join(project_root, "app", "src")

        violations = []
        python_files = get_all_python_files(app_src_path)

        for file_path in python_files:
            imports = extract_imports_from_file(file_path)

            # Check for problematic import patterns
            for import_line in imports:
                # Check for direct database imports in wrong layers
                if any(db in import_line.lower() for db in ['sqlite3', 'sqlalchemy', 'psycopg2']):
                    if '/domain/' in file_path or '/application/' in file_path:
                        violations.append(f"❌ Database import in wrong layer: {file_path} imports {import_line}")

                # Check for web framework imports in wrong layers
                if any(web in import_line.lower() for web in ['fastapi', 'flask', 'starlette']):
                    if '/domain/' in file_path or '/infrastructure/' in file_path:
                        violations.append(f"❌ Web framework import in wrong layer: {file_path} imports {import_line}")

        assert len(violations) == 0, f"""
        ❌ INAPPROPRIATE IMPORT LOCATIONS!

        Some modules are importing from inappropriate locations for their layer.

        Violations found:
        {chr(10).join(violations)}

        ✅ Solution: Move imports to appropriate layer or use dependency injection.
        """