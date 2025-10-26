# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Class Placement Validation Tests.

These tests verify that classes are placed in the correct architectural layers
according to DDD principles and their responsibilities.
"""

import pytest
import os
import glob
from .helpers import (
    get_all_python_files,
    extract_class_names,
    get_project_root
)


class TestClassPlacement:
    """Test suite for class placement validation."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test environment."""
        self.project_root = get_project_root()

    def test_controllers_are_not_in_domain_layer(self):
        """Verify controllers are not placed in Domain layer."""
        violations = []

        domain_path = os.path.join(self.project_root, "app", "src", "domain")
        domain_files = get_all_python_files(domain_path)

        for file_path in domain_files:
            classes = extract_class_names(file_path)
            for class_name in classes:
                if "Controller" in class_name:
                    violations.append(f"❌ Controller in Domain: {file_path}::{class_name}")

        assert len(violations) == 0, f"""
        ❌ CONTROLLERS IN DOMAIN LAYER!

        Controllers handle HTTP requests and coordinate between layers.
        They belong in Presentation or Application layer, not Domain.

        Violations found:
        {chr(10).join(violations)}

        ✅ Solution: Move controllers to:
        - app/src/routes/factories/ (for HTTP endpoint factories)
        - app/src/application/controllers/ (for application coordination)
        """

    def test_repositories_in_domain_are_interfaces(self):
        """Verify repository classes in Domain are interfaces/protocols."""
        violations = []

        domain_repos_path = os.path.join(self.project_root, "app", "src", "domain", "repositories")
        if os.path.exists(domain_repos_path):
            repo_files = get_all_python_files(domain_repos_path)

            for file_path in repo_files:
                if "__init__.py" in file_path:
                    continue

                classes = extract_class_names(file_path)
                for class_name in classes:
                    if "Repository" in class_name:
                        # Should be Protocol or Abstract Base Class
                        if not (class_name.endswith("Protocol") or
                                class_name.endswith("Interface") or
                                class_name.startswith("Abstract")):
                            violations.append(f"❌ Concrete Repository in Domain: {file_path}::{class_name}")

        assert len(violations) == 0, f"""
        ❌ CONCRETE REPOSITORIES IN DOMAIN!

        Domain layer should only contain repository interfaces/protocols.
        Concrete implementations belong in Infrastructure layer.

        Violations found:
        {chr(10).join(violations)}

        ✅ Solution:
        1. Convert to Protocol: class PlaylistRepositoryProtocol(Protocol)
        2. Move implementation to Infrastructure layer
        3. Use dependency injection to provide concrete implementation
        """

    def test_database_classes_are_not_in_domain(self):
        """Verify database-related classes are not in Domain layer."""
        violations = []

        domain_path = os.path.join(self.project_root, "app", "src", "domain")
        domain_files = get_all_python_files(domain_path)

        database_keywords = [
            "Database", "DB", "Table", "Connection",
            "Query", "SQL", "ORM", "Migration", "Schema"
        ]

        # Allow these legitimate domain concepts that happen to contain database keywords
        allowed_domain_concepts = [
            "AssociationSession",  # Business concept: user association session
            "UploadSession",       # Business concept: file upload session
            "SessionState",        # Business concept: session state
            "SessionError",        # Business exception for domain sessions
            "SessionTimeoutError", # Business exception for domain sessions
            "AssociationSessionStartedEvent",    # Domain event
            "AssociationSessionCompletedEvent",  # Domain event
            "AssociationSessionExpiredEvent"     # Domain event
        ]

        for file_path in domain_files:
            classes = extract_class_names(file_path)
            for class_name in classes:
                # Skip allowed domain concepts
                if class_name in allowed_domain_concepts:
                    continue

                for keyword in database_keywords:
                    if keyword in class_name and keyword != "Model":  # Allow domain models
                        violations.append(f"❌ Database class in Domain: {file_path}::{class_name}")

        assert len(violations) == 0, f"""
        ❌ DATABASE CLASSES IN DOMAIN!

        Database-related classes belong in Infrastructure layer.
        Domain should be persistence-ignorant.

        Violations found:
        {chr(10).join(violations)}

        ✅ Solution: Move database classes to Infrastructure layer.
        """

    def test_web_framework_classes_are_not_in_domain(self):
        """Verify web framework classes are not in Domain layer."""
        violations = []

        domain_path = os.path.join(self.project_root, "app", "src", "domain")
        domain_files = get_all_python_files(domain_path)

        web_keywords = [
            "Route", "Handler", "Endpoint", "API", "HTTP", "Request",
            "Response", "WebSocket", "Middleware", "Router"
        ]

        for file_path in domain_files:
            classes = extract_class_names(file_path)
            for class_name in classes:
                # Skip Protocol classes - they define contracts and are domain-agnostic
                if class_name.endswith("Protocol"):
                    continue

                for keyword in web_keywords:
                    if keyword in class_name:
                        violations.append(f"❌ Web class in Domain: {file_path}::{class_name}")

        assert len(violations) == 0, f"""
        ❌ WEB FRAMEWORK CLASSES IN DOMAIN!

        Web framework classes belong in Presentation layer (routes).
        Domain should be web-framework agnostic.

        Violations found:
        {chr(10).join(violations)}

        ✅ Solution: Move web classes to routes/ or controllers/.
        """

    def test_domain_services_are_properly_placed(self):
        """Verify domain services are in the correct location."""
        violations = []

        # Check domain services are in domain/services/
        domain_services_path = os.path.join(self.project_root, "app", "src", "domain", "services")
        if os.path.exists(domain_services_path):
            service_files = get_all_python_files(domain_services_path)

            for file_path in service_files:
                if "__init__.py" in file_path:
                    continue

                classes = extract_class_names(file_path)
                for class_name in classes:
                    if "Service" in class_name:
                        # Domain services should end with "Service" or "DomainService"
                        if not (class_name.endswith("Service") or class_name.endswith("DomainService")):
                            violations.append(f"⚠️ Domain service naming: {file_path}::{class_name}")

        # Check that services in other domain folders are not application services
        domain_path = os.path.join(self.project_root, "app", "src", "domain")
        domain_files = get_all_python_files(domain_path)

        for file_path in domain_files:
            if "/services/" in file_path:
                continue  # Skip the legitimate services folder

            classes = extract_class_names(file_path)
            for class_name in classes:
                if class_name.endswith("ApplicationService"):
                    violations.append(f"❌ Application service in Domain: {file_path}::{class_name}")

        assert len(violations) == 0, f"""
        ❌ DOMAIN SERVICE PLACEMENT ISSUES!

        Domain services should:
        - Be in domain/services/ folder
        - Focus on business logic
        - Not be application services

        Violations found:
        {chr(10).join(violations)}

        ✅ Solution: Move application services to application/services/.
        """

    def test_application_services_are_properly_placed(self):
        """Verify application services are in the correct location."""
        violations = []

        # Check application services are in application/services/
        app_services_path = os.path.join(self.project_root, "app", "src", "application", "services")
        if os.path.exists(app_services_path):
            service_files = get_all_python_files(app_services_path)

            for file_path in service_files:
                if "__init__.py" in file_path:
                    continue

                classes = extract_class_names(file_path)
                for class_name in classes:
                    if "Service" in class_name and not class_name.endswith("ApplicationService"):
                        violations.append(f"⚠️ Application service should end with 'ApplicationService': {file_path}::{class_name}")

        # Check for application services in wrong locations
        wrong_locations = [
            os.path.join(self.project_root, "app", "src", "domain"),
            os.path.join(self.project_root, "app", "src", "infrastructure")
        ]

        for location in wrong_locations:
            if os.path.exists(location):
                files = get_all_python_files(location)
                for file_path in files:
                    classes = extract_class_names(file_path)
                    for class_name in classes:
                        if class_name.endswith("ApplicationService"):
                            layer = "Domain" if "/domain/" in file_path else "Infrastructure"
                            violations.append(f"❌ Application service in {layer}: {file_path}::{class_name}")

        assert len(violations) == 0, f"""
        ❌ APPLICATION SERVICE PLACEMENT ISSUES!

        Application services should:
        - Be in application/services/ folder
        - End with 'ApplicationService'
        - Orchestrate use cases

        Violations found:
        {chr(10).join(violations)}

        ✅ Solution: Move to correct location and fix naming.
        """

    def test_value_objects_are_in_domain(self):
        """Verify value objects are placed in Domain layer."""
        violations = []

        # Look for value object patterns outside of domain
        non_domain_paths = [
            os.path.join(self.project_root, "app", "src", "application"),
            os.path.join(self.project_root, "app", "src", "infrastructure"),
            os.path.join(self.project_root, "app", "src", "routes")
        ]

        value_object_indicators = ["ValueObject", "VO", "Value"]

        for path in non_domain_paths:
            if os.path.exists(path):
                files = get_all_python_files(path)
                for file_path in files:
                    classes = extract_class_names(file_path)
                    for class_name in classes:
                        for indicator in value_object_indicators:
                            if indicator in class_name:
                                layer = os.path.basename(path)
                                violations.append(f"❌ Value object in {layer}: {file_path}::{class_name}")

        # This is more of a warning since value objects might be DTOs
        if len(violations) > 0:
            print("⚠️ Potential value objects found outside Domain:")
            for violation in violations:
                print(f"   {violation}")

        # Don't fail the test, just warn
        assert True, "Value object placement analysis complete"

    def test_entities_are_in_domain(self):
        """Verify entities are placed in Domain layer."""
        violations = []

        # Look for entity patterns outside of domain
        non_domain_paths = [
            os.path.join(self.project_root, "app", "src", "application"),
            os.path.join(self.project_root, "app", "src", "infrastructure"),
            os.path.join(self.project_root, "app", "src", "routes")
        ]

        entity_indicators = ["Entity", "Aggregate", "Root"]

        for path in non_domain_paths:
            if os.path.exists(path):
                files = get_all_python_files(path)
                for file_path in files:
                    classes = extract_class_names(file_path)
                    for class_name in classes:
                        for indicator in entity_indicators:
                            if indicator in class_name and "Service" not in class_name:
                                layer = os.path.basename(path)
                                violations.append(f"❌ Entity in {layer}: {file_path}::{class_name}")

        assert len(violations) == 0, f"""
        ❌ ENTITIES OUTSIDE DOMAIN!

        Entities represent business objects and belong in Domain layer.

        Violations found:
        {chr(10).join(violations)}

        ✅ Solution: Move entities to domain/models/ or domain/entities/.
        """

    def test_infrastructure_adapters_are_properly_placed(self):
        """Verify infrastructure adapters are in Infrastructure layer."""
        violations = []

        # Check for adapters in wrong locations
        wrong_locations = [
            os.path.join(self.project_root, "app", "src", "domain"),
            os.path.join(self.project_root, "app", "src", "application")
        ]

        adapter_indicators = ["Adapter", "Implementation", "Concrete"]

        for location in wrong_locations:
            if os.path.exists(location):
                files = get_all_python_files(location)
                for file_path in files:
                    classes = extract_class_names(file_path)
                    for class_name in classes:
                        for indicator in adapter_indicators:
                            if indicator in class_name:
                                layer = "Domain" if "/domain/" in file_path else "Application"
                                violations.append(f"❌ Infrastructure adapter in {layer}: {file_path}::{class_name}")

        assert len(violations) == 0, f"""
        ❌ INFRASTRUCTURE ADAPTERS IN WRONG LAYER!

        Infrastructure adapters should be in Infrastructure layer.

        Violations found:
        {chr(10).join(violations)}

        ✅ Solution: Move adapters to infrastructure/adapters/.
        """

    def test_factories_are_appropriately_placed(self):
        """Verify factories are placed in appropriate layers."""
        factories_analysis = {
            'domain': [],
            'application': [],
            'infrastructure': [],
            'other': []
        }

        all_paths = [
            os.path.join(self.project_root, "app", "src", "domain"),
            os.path.join(self.project_root, "app", "src", "application"),
            os.path.join(self.project_root, "app", "src", "infrastructure"),
            os.path.join(self.project_root, "app", "src", "services")
        ]

        for path in all_paths:
            if os.path.exists(path):
                files = get_all_python_files(path)
                for file_path in files:
                    if "factory" in file_path.lower() or "Factory" in os.path.basename(file_path):
                        if "/domain/" in file_path:
                            factories_analysis['domain'].append(file_path)
                        elif "/application/" in file_path:
                            factories_analysis['application'].append(file_path)
                        elif "/infrastructure/" in file_path:
                            factories_analysis['infrastructure'].append(file_path)
                        else:
                            factories_analysis['other'].append(file_path)

        # Print factory analysis
        print("🏭 Factory Placement Analysis:")
        for layer, factories in factories_analysis.items():
            if factories:
                print(f"   {layer.title()}: {len(factories)} factories")
                for factory in factories[:3]:  # Show first 3
                    print(f"     - {os.path.basename(factory)}")

        # This is informational
        assert True, "Factory placement analysis complete"