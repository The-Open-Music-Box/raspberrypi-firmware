# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Dependency Injection Container for TheOpenMusicBox.

Enhanced DI container with protocol support and proper lifecycle management.
Eliminates dynamic imports in favor of explicit registration.
"""

from typing import Dict, Any, Callable, TypeVar, Type, Optional, Protocol
from enum import Enum
import logging

T = TypeVar('T')

logger = logging.getLogger(__name__)


class ServiceLifetime(Enum):
    """Service lifetime options."""
    SINGLETON = "singleton"  # Single instance for application lifetime
    TRANSIENT = "transient"  # New instance on each request
    SCOPED = "scoped"        # Single instance per scope (future use)


class DependencyContainer:
    """Enhanced Dependency Injection Container following DDD principles.

    Features:
    - Protocol-based registration (type-safe)
    - Multiple lifetime strategies (singleton, transient, scoped)
    - Lazy initialization support
    - Constructor injection
    - No dynamic imports
    """

    def __init__(self):
        """Initialize the DI container."""
        self._services: Dict[str, Any] = {}
        self._singletons: Dict[str, Any] = {}
        self._factories: Dict[str, Callable] = {}
        self._lifetimes: Dict[str, ServiceLifetime] = {}
        self._protocol_map: Dict[Type, str] = {}  # Protocol -> service_name mapping

    def register_singleton(self, service_name: str, instance: Any) -> None:
        """Register a singleton instance.

        Args:
            service_name: Name of the service
            instance: The singleton instance
        """
        self._singletons[service_name] = instance
        self._lifetimes[service_name] = ServiceLifetime.SINGLETON
        logger.debug(f"Registered singleton: {service_name}")

    def register_factory(
        self,
        service_name: str,
        factory: Callable,
        lifetime: ServiceLifetime = ServiceLifetime.SINGLETON,
    ) -> None:
        """Register a factory function.

        Args:
            service_name: Name of the service
            factory: Factory function that creates the service
            lifetime: Service lifetime (singleton, transient, scoped)
        """
        self._factories[service_name] = factory
        self._lifetimes[service_name] = lifetime
        logger.debug(f"Registered factory: {service_name} ({lifetime.value})")

    def register_protocol(
        self,
        protocol: Type,
        implementation_factory: Callable,
        lifetime: ServiceLifetime = ServiceLifetime.SINGLETON,
    ) -> None:
        """Register a service by protocol/interface.

        Args:
            protocol: Protocol type (interface)
            implementation_factory: Factory that creates the implementation
            lifetime: Service lifetime
        """
        service_name = f"protocol_{protocol.__name__}"
        self._protocol_map[protocol] = service_name
        self.register_factory(service_name, implementation_factory, lifetime)
        logger.debug(f"Registered protocol: {protocol.__name__} -> {service_name}")

    def get(self, service_name: str) -> Any:
        """Get a service instance.

        Args:
            service_name: Name of the service

        Returns:
            The service instance

        Raises:
            KeyError: If service is not registered
        """
        # Check singletons first
        if service_name in self._singletons:
            return self._singletons[service_name]

        # Check if we have a factory
        if service_name in self._factories:
            lifetime = self._lifetimes.get(service_name, ServiceLifetime.SINGLETON)
            instance = self._factories[service_name]()

            # Cache as singleton if appropriate
            if lifetime == ServiceLifetime.SINGLETON:
                self._singletons[service_name] = instance

            return instance

        raise KeyError(f"Service '{service_name}' not registered")

    def get_by_protocol(self, protocol: Type[T]) -> T:
        """Get a service instance by protocol.

        Args:
            protocol: Protocol type

        Returns:
            Service implementation

        Raises:
            KeyError: If protocol is not registered
        """
        if protocol not in self._protocol_map:
            raise KeyError(f"Protocol '{protocol.__name__}' not registered")

        service_name = self._protocol_map[protocol]
        return self.get(service_name)

    def has(self, service_name: str) -> bool:
        """Check if a service is registered.

        Args:
            service_name: Name of the service

        Returns:
            True if service is registered
        """
        return service_name in self._singletons or service_name in self._factories

    def has_protocol(self, protocol: Type) -> bool:
        """Check if a protocol is registered.

        Args:
            protocol: Protocol type

        Returns:
            True if protocol is registered
        """
        return protocol in self._protocol_map

    def clear(self) -> None:
        """Clear all registered services."""
        self._services.clear()
        self._singletons.clear()
        self._factories.clear()
        self._lifetimes.clear()
        self._protocol_map.clear()
        logger.debug("Cleared all services from DI container")


# Global container instance
_container = DependencyContainer()


def get_container() -> DependencyContainer:
    """Get the global DI container instance.

    Returns:
        The global DI container
    """
    return _container


def register_core_infrastructure_services():
    """Register core infrastructure services in the DI container.

    This function registers only infrastructure-level services.
    Application and domain services should be registered in their respective containers.
    Services are registered with proper factories that use direct imports.
    """
    container = get_container()

    # Import core infrastructure services at registration time
    from app.src.services.response.unified_response_service import UnifiedResponseService
    from app.src.services.error.unified_error_decorator import (
        handle_errors,
        handle_http_errors,
        handle_service_errors,
        handle_repository_errors,
        handle_infrastructure_errors,
    )
    from app.src.domain.protocols.response_service_protocol import ResponseServiceProtocol
    from app.src.domain.protocols.error_handling_protocol import (
        ErrorHandlerProtocol,
        HTTPErrorHandlerProtocol,
        ServiceErrorHandlerProtocol,
    )
    from app.src.config.app_config import AppConfig
    from app.src.domain.bootstrap import DomainBootstrap

    # Register configuration
    container.register_factory("config", lambda: AppConfig(), ServiceLifetime.SINGLETON)

    # Register domain bootstrap (singleton instance - create new instance instead of using global)
    def domain_bootstrap_factory():
        return DomainBootstrap()
    container.register_factory("domain_bootstrap", domain_bootstrap_factory, ServiceLifetime.SINGLETON)

    # Register audio domain container (use existing domain-internal instance)
    def audio_domain_container_factory():
        from app.src.domain.audio.container import audio_domain_container
        return audio_domain_container
    container.register_factory("audio_domain_container", audio_domain_container_factory, ServiceLifetime.SINGLETON)

    # Register infrastructure services
    def player_state_service_factory():
        from app.src.services.player_state_service import PlayerStateService
        return PlayerStateService()
    container.register_factory("player_state_service", player_state_service_factory, ServiceLifetime.SINGLETON)

    def socket_config_factory():
        from app.src.config.socket_config import SocketConfig
        return SocketConfig()
    container.register_factory("socket_config", socket_config_factory, ServiceLifetime.SINGLETON)

    def monitoring_config_factory():
        from app.src.config.monitoring_config import MonitoringConfig
        app_config = container.get("config")
        return MonitoringConfig(app_config=app_config)
    container.register_factory("monitoring_config", monitoring_config_factory, ServiceLifetime.SINGLETON)

    # Register error handling infrastructure
    def error_tracker_factory():
        from app.src.services.error.unified_error_decorator import ErrorTracker
        return ErrorTracker()
    container.register_factory("error_tracker", error_tracker_factory, ServiceLifetime.SINGLETON)

    def unified_error_handler_factory():
        from app.src.infrastructure.error_handling.unified_error_handler import UnifiedErrorHandler
        return UnifiedErrorHandler()
    container.register_factory("unified_error_handler", unified_error_handler_factory, ServiceLifetime.SINGLETON)

    # Register response service by protocol
    container.register_protocol(
        ResponseServiceProtocol,
        lambda: UnifiedResponseService,
        ServiceLifetime.SINGLETON,
    )

    # Register error handlers
    container.register_singleton("error_handler", handle_errors)
    container.register_singleton("http_error_handler", handle_http_errors)
    container.register_singleton("service_error_handler", handle_service_errors)
    container.register_singleton("repository_error_handler", handle_repository_errors)
    container.register_singleton("infrastructure_error_handler", handle_infrastructure_errors)

    logger.info("✅ Core infrastructure services registered in DI container")


# Note: We don't auto-initialize on import anymore.
# Services must be explicitly registered by the application bootstrap.
# This gives better control and avoids circular import issues.
