"""
Architecture Test: Validate App Module Export Configuration

This test ensures that the configured app_module in the configuration
actually points to a valid, importable ASGI application in the codebase.

This prevents deployment failures where uvicorn cannot find the configured
app module.
"""

import importlib
import pytest
from app.src.config import config


class TestAppModuleExport:
    """Test suite to validate app module exports match configuration."""

    def test_app_module_is_importable(self):
        """
        Test that the configured app_module can be imported.

        This validates that:
        1. The module exists
        2. The attribute exists in the module
        3. No import errors occur
        """
        # Get the configured app module (e.g., "app.main:app_sio")
        app_module_config = config.app_module

        # Parse module and attribute
        if ":" not in app_module_config:
            pytest.fail(
                f"Invalid app_module format: '{app_module_config}'. "
                f"Expected format: 'module.path:attribute'"
            )

        module_path, attribute_name = app_module_config.split(":", 1)

        # Try to import the module
        try:
            module = importlib.import_module(module_path)
        except ImportError as e:
            pytest.fail(
                f"Failed to import module '{module_path}' from app_module config: {e}"
            )

        # Check if the attribute exists in the module
        if not hasattr(module, attribute_name):
            available_attrs = [
                attr for attr in dir(module) if not attr.startswith("_")
            ]
            pytest.fail(
                f"Module '{module_path}' does not have attribute '{attribute_name}'. "
                f"Available public attributes: {available_attrs}"
            )

        # Get the attribute
        app_instance = getattr(module, attribute_name)

        # Validate it's not None
        assert app_instance is not None, (
            f"The configured app_module '{app_module_config}' exists but is None. "
            f"Ensure the module properly exports the ASGI application."
        )

    def test_app_module_is_asgi_application(self):
        """
        Test that the configured app_module is a valid ASGI application.

        This validates that the exported object is callable or has the
        expected ASGI application structure.
        """
        # Get the configured app module
        app_module_config = config.app_module
        module_path, attribute_name = app_module_config.split(":", 1)

        # Import and get the app
        module = importlib.import_module(module_path)
        app_instance = getattr(module, attribute_name)

        # ASGI apps should be callable (they accept scope, receive, send)
        # or be instances of specific ASGI app classes
        assert callable(app_instance) or hasattr(app_instance, "__call__"), (
            f"The configured app_module '{app_module_config}' is not callable. "
            f"ASGI applications must be callable. Type: {type(app_instance)}"
        )

    def test_production_and_dev_app_modules_are_consistent(self):
        """
        Test that both production and development configurations point to
        valid app modules.

        This ensures we don't have discrepancies between environments.
        """
        from app.src.config.config_factory import ConfigFactory, ConfigType

        # Test production config
        prod_config = ConfigFactory.create_config(ConfigType.PRODUCTION)
        prod_module_path, prod_attr = prod_config.app_module.split(":", 1)

        try:
            prod_module = importlib.import_module(prod_module_path)
            assert hasattr(prod_module, prod_attr), (
                f"Production app_module '{prod_config.app_module}' attribute not found"
            )
        except ImportError as e:
            pytest.fail(f"Production app_module import failed: {e}")

        # Test development config
        dev_config = ConfigFactory.create_config(ConfigType.DEVELOPMENT)
        dev_module_path, dev_attr = dev_config.app_module.split(":", 1)

        try:
            dev_module = importlib.import_module(dev_module_path)
            assert hasattr(dev_module, dev_attr), (
                f"Development app_module '{dev_config.app_module}' attribute not found"
            )
        except ImportError as e:
            pytest.fail(f"Development app_module import failed: {e}")

    def test_backwards_compatibility_with_app_export(self):
        """
        Test that 'app.main:app' is also available for backward compatibility.

        This ensures local development and tests continue to work.
        """
        try:
            module = importlib.import_module("app.main")
            assert hasattr(module, "app"), (
                "Module 'app.main' should export 'app' for backward compatibility"
            )
            app_instance = getattr(module, "app")
            assert app_instance is not None, "'app' export should not be None"
        except ImportError as e:
            pytest.fail(f"Failed to import app.main: {e}")
