"""
Pytest plugin to suppress all external library warnings at import time.
This ensures warnings are suppressed before any imports occur.
"""

import warnings


def pytest_configure(config):
    """Configure pytest with comprehensive warning suppression."""
    # Apply warning filters at the very start
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    warnings.filterwarnings("ignore", category=ResourceWarning)
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    warnings.filterwarnings("ignore", category=UserWarning)
    warnings.filterwarnings("ignore", category=FutureWarning)
    warnings.filterwarnings("ignore", category=ImportWarning)

    # Specifically target the rx library warning
    warnings.filterwarnings("ignore", message=".*utcfromtimestamp.*", category=DeprecationWarning)
    warnings.filterwarnings("ignore", module="rx.*")
    warnings.filterwarnings("ignore", module="rx.internal.*")


def pytest_collection_modifyitems(config, items):
    """Called after collection is completed."""
    # Ensure warnings are still suppressed
    warnings.filterwarnings("ignore", category=DeprecationWarning)


# Register the plugin functions to run as early as possible
pytest_plugins = []
