# Backend Contracts Integration

## Overview

The backend implements the API defined in the `tomb-contracts` repository. Contract tests validate that the implementation matches the OpenAPI specification.

## Structure

```
back/
├── app/src/api/              # API implementation
├── tests/contracts/          # Contract validation tests
└── ../contracts/             # Git submodule (OpenAPI schemas)
    └── schemas/
        └── openapi.yaml      # Source of truth for API
```

## Contract Testing

### Current Test Suite

Contract tests validate that API responses match the expected format:

```
back/tests/contracts/
├── test_health_api_contract.py
├── test_player_api_contract.py
├── test_playlist_api_contract.py
├── test_nfc_api_contract.py
├── test_system_api_contract.py
├── test_youtube_api_contract.py
└── test_upload_endpoints_contract.py
```

### Running Contract Tests

```bash
cd back

# Run all contract tests
pytest tests/contracts/ -v

# Run specific endpoint tests
pytest tests/contracts/test_player_api_contract.py -v

# Run with coverage
pytest tests/contracts/ --cov=app.src.api
```

## Validation Against OpenAPI Schema

### Option 1: OpenAPI Schema Validator (Recommended)

Install dependencies:

```bash
pip install openapi-spec-validator prance
```

Create validator script `back/tests/contracts/schema_validator.py`:

```python
"""Validate API responses against OpenAPI schema."""

import yaml
import json
from pathlib import Path
from openapi_spec_validator import validate_spec
from openapi_spec_validator.validation.exceptions import OpenAPIValidationError

def load_openapi_schema():
    """Load OpenAPI schema from contracts submodule."""
    schema_path = Path(__file__).parent.parent.parent.parent / "contracts" / "schemas" / "openapi.yaml"

    with open(schema_path) as f:
        schema = yaml.safe_load(f)

    return schema

def validate_openapi_schema():
    """Validate that OpenAPI schema itself is valid."""
    try:
        schema = load_openapi_schema()
        validate_spec(schema)
        print("✅ OpenAPI schema is valid")
        return True
    except OpenAPIValidationError as e:
        print(f"❌ OpenAPI schema validation failed: {e}")
        return False

def validate_response_against_schema(response_data, endpoint_path, method, status_code):
    """Validate API response against OpenAPI schema.

    Args:
        response_data: The actual response data from API
        endpoint_path: API endpoint path (e.g., "/api/player/status")
        method: HTTP method (e.g., "get", "post")
        status_code: Response status code (e.g., 200)

    Returns:
        bool: True if valid, False otherwise
    """
    schema = load_openapi_schema()

    # Navigate to response schema
    try:
        path_item = schema['paths'][endpoint_path]
        operation = path_item[method.lower()]
        response_schema = operation['responses'][str(status_code)]

        # Extract schema for response body
        content_schema = response_schema.get('content', {}).get('application/json', {}).get('schema', {})

        # Validate response against schema
        # Note: This is simplified - for production use jsonschema library
        print(f"✅ Schema found for {method.upper()} {endpoint_path} [{status_code}]")
        return True

    except KeyError as e:
        print(f"❌ Schema not found: {e}")
        return False

if __name__ == "__main__":
    validate_openapi_schema()
```

### Option 2: Use Generated Python Models

Use Pydantic models from generated contracts:

```python
# back/app/src/api/responses/player_responses.py

from contracts.generated.python.models import PlayerState, UnifiedResponse

def get_player_status_response(player_state_data: dict) -> dict:
    """
    Validate and format player status response using contracts.

    This ensures response matches the contract exactly.
    """
    # Validate using Pydantic model from contracts
    player_state = PlayerState(**player_state_data)

    # Wrap in unified response
    response = UnifiedResponse(
        status="success",
        message="Player status retrieved",
        data=player_state.model_dump(),
        timestamp=time.time(),
        server_seq=get_current_seq()
    )

    return response.model_dump()
```

## Updating Contracts When Backend Changes

### Workflow

When you add/modify an endpoint in the backend:

1. **Update implementation** in `back/app/src/api/`

2. **Update OpenAPI schema**:
   ```bash
   cd ../contracts
   vim schemas/openapi.yaml
   # Add/modify endpoint definition
   ```

3. **Regenerate contracts**:
   ```bash
   bash scripts/generate-all.sh
   ```

4. **Update contract tests**:
   ```bash
   cd ../back
   # Update or add test in tests/contracts/
   vim tests/contracts/test_new_endpoint_contract.py
   ```

5. **Run tests**:
   ```bash
   pytest tests/contracts/ -v
   ```

6. **Commit both repos**:
   ```bash
   # Commit contracts
   cd ../contracts
   git add schemas/
   git commit -m "feat(api): add new endpoint"
   git push origin main

   # Update submodule reference
   cd ../
   git add contracts/
   git commit -m "Update contracts with new endpoint"
   ```

## Example Contract Test

```python
"""Example contract test for a new endpoint."""

import pytest
from httpx import AsyncClient, ASGITransport

@pytest.mark.asyncio
async def test_new_endpoint_contract(app):
    """Test POST /api/new-endpoint contract.

    Contract (from openapi.yaml):
    - Request: { field: string }
    - Response 200: { status: "success", data: { result: string } }
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Test request
        response = await client.post(
            "/api/new-endpoint",
            json={"field": "test"}
        )

        # Validate response structure
        assert response.status_code == 200
        data = response.json()

        # Validate UnifiedResponse wrapper
        assert data["status"] == "success"
        assert "message" in data
        assert "timestamp" in data

        # Validate response data matches schema
        assert "data" in data
        assert "result" in data["data"]
        assert isinstance(data["data"]["result"], str)
```

## Contract Validation in CI/CD

Add to `.github/workflows/backend-tests.yml`:

```yaml
name: Backend Tests

on: [push, pull_request]

jobs:
  contract-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          submodules: recursive  # Important for contracts submodule!

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          cd back
          pip install -r requirements.txt
          pip install openapi-spec-validator

      - name: Validate OpenAPI schema
        run: |
          python back/tests/contracts/schema_validator.py

      - name: Run contract tests
        run: |
          cd back
          pytest tests/contracts/ -v --tb=short
```

## Benefits

✅ **Type Safety** - Pydantic models validate responses
✅ **Documentation** - OpenAPI schema documents all endpoints
✅ **Client Generation** - Other apps get typed clients
✅ **Contract First** - Define API before implementation
✅ **Breaking Change Detection** - Tests fail if contract changes

## Best Practices

### 1. Always Update Schema First

```bash
# ❌ Bad: Implement endpoint, forget to update schema
vim app/src/api/routes/player.py  # Add endpoint
# (forget schema)

# ✅ Good: Update schema, then implement
cd ../contracts
vim schemas/openapi.yaml          # Define endpoint
cd ../back
vim app/src/api/routes/player.py  # Implement endpoint
```

### 2. Use UnifiedResponse Everywhere

```python
from app.src.services.unified_response_service import UnifiedResponseService

@router.get("/status")
async def get_status():
    data = get_player_data()

    # Always use UnifiedResponseService
    return UnifiedResponseService.success_response(
        message="Player status retrieved",
        data=data
    )
```

### 3. Add Contract Tests for New Endpoints

Every new endpoint should have a contract test:

```python
# tests/contracts/test_player_api_contract.py

async def test_new_player_endpoint_contract(app):
    """Test new endpoint matches contract."""
    # Implementation...
```

### 4. Keep Sequence Numbers Consistent

```python
# Include server_seq in all stateful responses
{
    "status": "success",
    "data": { ... },
    "server_seq": current_sequence_number,
    "timestamp": time.time()
}
```

## Troubleshooting

### Contracts Submodule Not Found

```bash
cd /path/to/tomb-rpi
git submodule update --init --recursive
```

### OpenAPI Schema Changes Not Reflected

```bash
cd contracts
git pull origin main
bash scripts/generate-all.sh
cd ../back
pytest tests/contracts/
```

### Test Failures After Contract Update

1. Check what changed in schema:
   ```bash
   cd contracts
   git log -p schemas/openapi.yaml
   ```

2. Update implementation to match
3. Update tests if needed

## Migration Checklist

- [ ] Move contracts to separate repository
- [ ] Add contracts as submodule to tomb-rpi
- [ ] Update contract tests to reference submodule schemas
- [ ] Add OpenAPI schema validation script
- [ ] Consider using generated Pydantic models
- [ ] Update CI/CD to handle submodules
- [ ] Document process for team

## Reference

- **OpenAPI Spec:** `contracts/schemas/openapi.yaml`
- **Contract Tests:** `back/tests/contracts/`
- **Main Integration Guide:** `../CONTRACTS_INTEGRATION.md`
