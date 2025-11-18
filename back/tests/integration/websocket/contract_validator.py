# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Contract Validator for TheOpenMusicBox integration tests.

This module provides automatic validation of Socket.IO events and HTTP responses
against the contract schemas defined in the contracts repository.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

from jsonschema import validate, ValidationError, Draft7Validator

logger = logging.getLogger(__name__)


class ContractValidator:
    """
    Validates Socket.IO events and HTTP responses against contract schemas.

    Features:
    - Loads schemas from contracts repository
    - Validates event envelope format
    - Validates event-specific data schemas
    - Validates server_seq monotonicity
    - Provides detailed error messages

    Example usage:
        validator = ContractValidator("/path/to/contracts/schemas/socketio_contracts.json")

        # Validate a state event
        validator.validate_event("state:player", {
            "event_type": "state:player",
            "server_seq": 42,
            "data": {...},
            "timestamp": 1234567890,
            "event_id": "abc-123"
        })

        # Validate server_seq monotonicity
        validator.validate_server_seq_monotonic(captured_events)
    """

    def __init__(self, socketio_contract_path: str, strict: bool = True):
        """
        Initialize contract validator.

        Args:
            socketio_contract_path: Path to socketio_contracts.json file
            strict: If True, raise on validation errors. If False, only log warnings.
        """
        self.contract_path = Path(socketio_contract_path)
        self.strict = strict

        if not self.contract_path.exists():
            raise FileNotFoundError(
                f"Contract file not found: {self.contract_path}"
            )

        # Load contracts
        with open(self.contract_path, 'r') as f:
            self.contracts = json.load(f)

        logger.info(f"Loaded contracts from {self.contract_path}")

        # Extract schemas
        self.envelope_schema = self.contracts.get('event_envelope_format', {}).get('schema', {})
        self.event_schemas: Dict[str, Dict] = {}

        # Parse all event schemas from contracts
        for category, details in self.contracts.get('contracts', {}).items():
            for event_name, event_spec in details.get('events', {}).items():
                # Some events have 'data_schema', others have 'payload'
                if 'data_schema' in event_spec:
                    self.event_schemas[event_name] = event_spec['data_schema']
                elif 'payload' in event_spec and event_spec['payload'] is not None:
                    self.event_schemas[event_name] = event_spec['payload']

        logger.info(f"Loaded {len(self.event_schemas)} event schemas")

        # Create validators
        self.envelope_validator = Draft7Validator(self.envelope_schema)

    def validate_event(self, event_type: str, payload: Dict[str, Any]):
        """
        Validate an event against its contract.

        Args:
            event_type: Type of the event (e.g., "state:player")
            payload: Event payload/envelope

        Raises:
            AssertionError: If validation fails and strict=True
        """
        try:
            # State events use envelope format
            if event_type.startswith('state:'):
                self._validate_state_event(event_type, payload)
            else:
                # Non-state events validate payload directly
                self._validate_payload(event_type, payload)

            logger.debug(f"✓ Contract validation passed for {event_type}")

        except (ValidationError, AssertionError) as e:
            error_msg = f"Contract validation failed for {event_type}: {e}"
            if self.strict:
                raise AssertionError(error_msg)
            else:
                logger.warning(error_msg)

    def _validate_state_event(self, event_type: str, envelope: Dict[str, Any]):
        """
        Validate a state event (uses envelope format).

        Args:
            event_type: Event type
            envelope: Event envelope containing event_type, server_seq, data, etc.
        """
        # Validate envelope structure
        try:
            validate(instance=envelope, schema=self.envelope_schema)
        except ValidationError as e:
            raise AssertionError(
                f"Envelope validation failed for {event_type}: {e.message}"
            ) from e

        # Validate envelope.event_type matches expected
        if envelope.get('event_type') != event_type:
            raise AssertionError(
                f"Event type mismatch: expected '{event_type}', "
                f"got '{envelope.get('event_type')}'"
            )

        # Validate data schema if available
        if event_type in self.event_schemas:
            data = envelope.get('data')
            if data is not None:
                try:
                    validate(instance=data, schema=self.event_schemas[event_type])
                except ValidationError as e:
                    raise AssertionError(
                        f"Data schema validation failed for {event_type}: {e.message}"
                    ) from e

    def _validate_payload(self, event_type: str, payload: Any):
        """
        Validate a non-state event payload.

        Args:
            event_type: Event type
            payload: Event payload
        """
        if event_type in self.event_schemas:
            try:
                validate(instance=payload, schema=self.event_schemas[event_type])
            except ValidationError as e:
                raise AssertionError(
                    f"Payload validation failed for {event_type}: {e.message}"
                ) from e
        else:
            logger.debug(
                f"No schema found for {event_type}, skipping validation"
            )

    def validate_server_seq_monotonic(self, events: list):
        """
        Validate that server_seq is monotonically increasing across events.

        Args:
            events: List of event dictionaries or CapturedEvent objects

        Raises:
            AssertionError: If server_seq is not monotonically increasing
        """
        # Extract server_seq values
        seqs = []
        for event in events:
            # Handle both dict and CapturedEvent objects
            if hasattr(event, 'data'):
                event_data = event.data
            else:
                event_data = event

            if 'server_seq' in event_data:
                seqs.append(event_data['server_seq'])

        if len(seqs) < 2:
            logger.debug(
                f"Not enough events with server_seq to validate monotonicity "
                f"(got {len(seqs)})"
            )
            return

        # Check if monotonically increasing
        for i in range(1, len(seqs)):
            if seqs[i] <= seqs[i-1]:
                error_msg = (
                    f"server_seq not monotonically increasing: "
                    f"seqs[{i-1}]={seqs[i-1]}, seqs[{i}]={seqs[i]}. "
                    f"Full sequence: {seqs}"
                )
                if self.strict:
                    raise AssertionError(error_msg)
                else:
                    logger.warning(error_msg)
                    return

        logger.info(
            f"✓ server_seq monotonicity validated: "
            f"{len(seqs)} events, range [{min(seqs)}, {max(seqs)}]"
        )

    def validate_client_op_id_correlation(
        self,
        client_op_id: str,
        http_response: Dict[str, Any],
        websocket_event: Dict[str, Any]
    ):
        """
        Validate that client_op_id is properly correlated between HTTP response
        and subsequent WebSocket broadcast.

        Args:
            client_op_id: The client operation ID sent in HTTP request
            http_response: HTTP response data
            websocket_event: WebSocket event data

        Raises:
            AssertionError: If correlation validation fails
        """
        # Check HTTP response contains client_op_id
        http_op_id = http_response.get('client_op_id')
        if http_op_id != client_op_id:
            error_msg = (
                f"HTTP response client_op_id mismatch: "
                f"expected '{client_op_id}', got '{http_op_id}'"
            )
            if self.strict:
                raise AssertionError(error_msg)
            else:
                logger.warning(error_msg)

        # Check WebSocket event contains client_op_id (in data or top-level)
        ws_data = websocket_event.get('data', {})
        ws_op_id = ws_data.get('client_op_id') or websocket_event.get('client_op_id')

        if ws_op_id != client_op_id:
            error_msg = (
                f"WebSocket event client_op_id mismatch: "
                f"expected '{client_op_id}', got '{ws_op_id}'"
            )
            if self.strict:
                raise AssertionError(error_msg)
            else:
                logger.warning(error_msg)

        logger.info(
            f"✓ client_op_id correlation validated: '{client_op_id}'"
        )

    def get_event_schema(self, event_type: str) -> Optional[Dict]:
        """
        Get the JSON schema for a specific event type.

        Args:
            event_type: Event type

        Returns:
            JSON schema dict or None if not found
        """
        return self.event_schemas.get(event_type)

    def list_event_types(self) -> list[str]:
        """
        List all event types with schemas.

        Returns:
            List of event type names
        """
        return list(self.event_schemas.keys())

    def __repr__(self) -> str:
        return (
            f"ContractValidator(schemas={len(self.event_schemas)}, "
            f"strict={self.strict})"
        )
