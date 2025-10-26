# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Unified Response Service

This service centralizes all API response formatting to eliminate the 140+ 
duplicated response patterns across the application.
"""

from typing import Dict, Any, Optional, List, Union
from fastapi.responses import JSONResponse
import time
import traceback
import logging
from app.src.monitoring import get_logger

logger = get_logger(__name__)


class UnifiedResponseService:
    """
    Service centralisé pour le formatage des réponses API.

    Remplace les patterns dupliqués:
    - create_success_response() répété dans 140+ endroits
    - create_error_response() avec formats inconsistants
    - Formatage manuel des réponses dans chaque handler
    """

    @staticmethod
    def success(
        message: str,
        data: Optional[Any] = None,
        status_code: int = 200,
        server_seq: Optional[int] = None,
        client_op_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> JSONResponse:
        """
        Crée une réponse de succès standardisée.

        Args:
            message: Message de succès
            data: Données à retourner
            status_code: Code HTTP (default: 200)
            server_seq: Sequence number pour synchronisation
            client_op_id: ID d'opération client pour tracking
            metadata: Métadonnées additionnelles

        Returns:
            JSONResponse avec format unifié
        """
        response_body = {"status": "success", "message": message, "timestamp": time.time()}

        # Add data if provided
        if data is not None:
            response_body["data"] = data

        # Add server sequence for state synchronization
        if server_seq is not None:
            response_body["server_seq"] = server_seq

        # Add client operation ID for tracking
        if client_op_id is not None:
            response_body["client_op_id"] = client_op_id

        # Add any additional metadata
        if metadata:
            response_body["metadata"] = metadata

        # Create response with anti-cache headers
        response = JSONResponse(content=response_body, status_code=status_code)

        # Add standard headers
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        response.headers["X-Content-Type-Options"] = "nosniff"

        return response

    @staticmethod
    def error(
        message: str,
        error_type: str = "error",
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
        client_op_id: Optional[str] = None,
        trace: bool = False,
    ) -> JSONResponse:
        """
        Crée une réponse d'erreur standardisée.

        Args:
            message: Message d'erreur
            error_type: Type d'erreur (error, validation_error, etc.)
            status_code: Code HTTP d'erreur
            details: Détails additionnels sur l'erreur
            client_op_id: ID d'opération client
            trace: Inclure la stack trace (dev mode only)

        Returns:
            JSONResponse avec format d'erreur unifié
        """
        response_body = {
            "status": "error",
            "error_type": error_type,
            "message": message,
            "timestamp": time.time(),
        }

        # Add error details if provided
        if details:
            response_body["details"] = details

        # Add client operation ID for tracking
        if client_op_id:
            response_body["client_op_id"] = client_op_id

        # Add stack trace in development mode
        if trace:
            response_body["trace"] = traceback.format_exc()

        # Log the error
        if status_code >= 500:
            logger.error(f"API Error: {error_type} - {message}", extra={"details": details, "status_code": status_code})
        else:
            logger.warning(f"API Error: {error_type} - {message}", extra={"details": details, "status_code": status_code})

        # Create response
        response = JSONResponse(content=response_body, status_code=status_code)

        # Add standard headers
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["X-Content-Type-Options"] = "nosniff"

        return response

    @staticmethod
    def validation_error(
        errors: Union[List[str], Dict[str, Any]],
        message: str = "Validation failed",
        status_code: int = 400,
        client_op_id: Optional[str] = None,
    ) -> JSONResponse:
        """
        Crée une réponse d'erreur de validation standardisée.

        Args:
            errors: Liste ou dictionnaire d'erreurs de validation
            message: Message principal
            status_code: Code HTTP (default: 400)
            client_op_id: ID d'opération client

        Returns:
            JSONResponse avec erreurs de validation
        """
        # Normalize errors to list format
        if isinstance(errors, dict):
            error_list = []
            for field, error in errors.items():
                if isinstance(error, list):
                    for e in error:
                        error_list.append({"field": field, "message": str(e)})
                else:
                    error_list.append({"field": field, "message": str(error)})
        else:
            error_list = [{"message": str(e)} for e in errors]

        response_body = {
            "status": "error",
            "error_type": "validation_error",
            "message": message,
            "errors": error_list,
            "timestamp": time.time(),
        }

        if client_op_id:
            response_body["client_op_id"] = client_op_id

        return JSONResponse(content=response_body, status_code=status_code)

    @staticmethod
    def not_found(
        resource: str,
        resource_id: Optional[str] = None,
        message: Optional[str] = None,
        client_op_id: Optional[str] = None,
    ) -> JSONResponse:
        """
        Crée une réponse 404 standardisée.

        Args:
            resource: Type de ressource non trouvée
            resource_id: ID de la ressource
            message: Message personnalisé
            client_op_id: ID d'opération client

        Returns:
            JSONResponse 404
        """
        if message is None:
            if resource_id:
                message = f"{resource} not found: {resource_id}"
            else:
                message = f"{resource} not found"

        return UnifiedResponseService.error(
            message=message,
            error_type="not_found",
            status_code=404,
            details={"resource": resource, "id": resource_id},
            client_op_id=client_op_id,
        )

    @staticmethod
    def unauthorized(
        message: str = "Unauthorized access",
        details: Optional[Dict[str, Any]] = None,
        client_op_id: Optional[str] = None,
    ) -> JSONResponse:
        """
        Crée une réponse 401 standardisée.

        Args:
            message: Message d'erreur
            details: Détails additionnels
            client_op_id: ID d'opération client

        Returns:
            JSONResponse 401
        """
        return UnifiedResponseService.error(
            message=message,
            error_type="unauthorized",
            status_code=401,
            details=details,
            client_op_id=client_op_id,
        )

    @staticmethod
    def forbidden(
        message: str = "Access forbidden",
        details: Optional[Dict[str, Any]] = None,
        client_op_id: Optional[str] = None,
    ) -> JSONResponse:
        """
        Crée une réponse 403 standardisée.

        Args:
            message: Message d'erreur
            details: Détails additionnels
            client_op_id: ID d'opération client

        Returns:
            JSONResponse 403
        """
        return UnifiedResponseService.error(
            message=message,
            error_type="forbidden",
            status_code=403,
            details=details,
            client_op_id=client_op_id,
        )

    @staticmethod
    def bad_request(
        message: str,
        details: Optional[Dict[str, Any]] = None,
        client_op_id: Optional[str] = None,
    ) -> JSONResponse:
        """
        Crée une réponse 400 Bad Request standardisée.

        Args:
            message: Message d'erreur
            details: Détails additionnels
            client_op_id: ID d'opération client

        Returns:
            JSONResponse 400
        """
        return UnifiedResponseService.error(
            message=message,
            error_type="bad_request",
            status_code=400,
            details=details,
            client_op_id=client_op_id,
        )

    @staticmethod
    def conflict(
        message: str,
        conflict_data: Optional[Dict[str, Any]] = None,
        client_op_id: Optional[str] = None,
    ) -> JSONResponse:
        """
        Crée une réponse 409 Conflict standardisée.

        Args:
            message: Message de conflit
            conflict_data: Données sur le conflit
            client_op_id: ID d'opération client

        Returns:
            JSONResponse 409
        """
        return UnifiedResponseService.error(
            message=message,
            error_type="conflict",
            status_code=409,
            details=conflict_data,
            client_op_id=client_op_id,
        )

    @staticmethod
    def rate_limit_exceeded(
        message: str = "Rate limit exceeded",
        retry_after: Optional[int] = None,
        client_op_id: Optional[str] = None,
    ) -> JSONResponse:
        """
        Crée une réponse 429 Too Many Requests standardisée.

        Args:
            message: Message d'erreur
            retry_after: Secondes avant retry
            client_op_id: ID d'opération client

        Returns:
            JSONResponse 429
        """
        details = {}
        if retry_after:
            details["retry_after"] = retry_after

        response = UnifiedResponseService.error(
            message=message,
            error_type="rate_limit",
            status_code=429,
            details=details,
            client_op_id=client_op_id,
        )

        if retry_after:
            response.headers["Retry-After"] = str(retry_after)

        return response

    @staticmethod
    def service_unavailable(
        service: str,
        message: Optional[str] = None,
        retry_after: Optional[int] = None,
        client_op_id: Optional[str] = None,
    ) -> JSONResponse:
        """
        Crée une réponse 503 Service Unavailable standardisée.

        Args:
            service: Nom du service indisponible
            message: Message personnalisé
            retry_after: Secondes avant retry
            client_op_id: ID d'opération client

        Returns:
            JSONResponse 503
        """
        if message is None:
            message = f"{service} service is currently unavailable"

        details = {"service": service}
        if retry_after:
            details["retry_after"] = retry_after

        response = UnifiedResponseService.error(
            message=message,
            error_type="service_unavailable",
            status_code=503,
            details=details,
            client_op_id=client_op_id,
        )

        if retry_after:
            response.headers["Retry-After"] = str(retry_after)

        return response

    @staticmethod
    def internal_error(
        message: str = "Internal server error",
        operation: Optional[str] = None,
        client_op_id: Optional[str] = None,
        trace: bool = False,
    ) -> JSONResponse:
        """
        Crée une réponse 500 Internal Server Error standardisée.

        Args:
            message: Message d'erreur
            operation: Opération qui a échoué
            client_op_id: ID d'opération client
            trace: Inclure stack trace (dev only)

        Returns:
            JSONResponse 500
        """
        details = {}
        if operation:
            details["operation"] = operation

        return UnifiedResponseService.error(
            message=message,
            error_type="internal_error",
            status_code=500,
            details=details if details else None,
            client_op_id=client_op_id,
            trace=trace,
        )

    @staticmethod
    def no_content(client_op_id: Optional[str] = None) -> JSONResponse:
        """
        Crée une réponse 204 No Content standardisée.

        Args:
            client_op_id: ID d'opération client

        Returns:
            JSONResponse 204 (empty body)
        """
        response = JSONResponse(content=None, status_code=204)

        if client_op_id:
            response.headers["X-Client-Op-Id"] = client_op_id

        return response

    @staticmethod
    def accepted(
        message: str = "Request accepted for processing",
        task_id: Optional[str] = None,
        client_op_id: Optional[str] = None,
    ) -> JSONResponse:
        """
        Crée une réponse 202 Accepted standardisée.

        Args:
            message: Message de confirmation
            task_id: ID de la tâche asynchrone
            client_op_id: ID d'opération client

        Returns:
            JSONResponse 202
        """
        data = {}
        if task_id:
            data["task_id"] = task_id

        return UnifiedResponseService.success(
            message=message, data=data if data else None, status_code=202, client_op_id=client_op_id
        )

    @staticmethod
    def created(
        message: str, data: Any, location: Optional[str] = None, client_op_id: Optional[str] = None
    ) -> JSONResponse:
        """
        Crée une réponse 201 Created standardisée.

        Args:
            message: Message de succès
            data: Ressource créée
            location: URL de la nouvelle ressource
            client_op_id: ID d'opération client

        Returns:
            JSONResponse 201
        """
        response = UnifiedResponseService.success(
            message=message, data=data, status_code=201, client_op_id=client_op_id
        )

        if location:
            response.headers["Location"] = location

        return response
