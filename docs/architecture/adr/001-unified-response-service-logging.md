# ADR 001: UnifiedResponseService Logging Behavior

**Status:** Accepted

**Date:** 2025-11-09

**Context:**

During Phase 6 architecture audit, we identified that `UnifiedResponseService` handles both response formatting AND logging. This appears to violate the Single Responsibility Principle (SRP) since the service has two distinct concerns:

1. Formatting error responses (primary responsibility)
2. Logging errors (secondary responsibility)

The logging code in question:

```python
# app/src/services/response/unified_response_service.py:127-130
if status_code >= 500:
    logger.error(f"API Error: {error_type} - {message}", ...)
else:
    logger.warning(f"API Error: {error_type} - {message}", ...)
```

## Decision

**We accept this design and will KEEP the logging in UnifiedResponseService.**

## Rationale

### 1. Cohesion Over Purity

The logging is tightly coupled to the response formatting. Every error response should be logged with consistent context. Separating these concerns would require:

- Duplicate context gathering in two places
- Coordination between formatter and logger
- Risk of inconsistent logging (some errors logged, others not)

The cohesion benefit outweighs the theoretical SRP violation.

### 2. Single Point of Truth

Having logging in UnifiedResponseService ensures:

- **Consistency**: All API errors are logged with the same format
- **Completeness**: No API error can escape logging
- **Centralized Control**: Changing log levels/format happens in one place

### 3. Practical Observability

In production, every response created must be observable. The service is the natural place to enforce this requirement since it has full context:

- Error type and message
- HTTP status code
- Request details (client_op_id, etc.)
- Stack traces (in development)

### 4. Similar Patterns in Industry

Many production systems combine response formatting and logging:

- Django REST Framework's exception handlers log and format
- Spring Boot's @ControllerAdvice logs and formats
- Express.js error middleware typically does both

This is a well-established pattern for centralized error handling.

### 5. Alternatives Considered

**Option A: Extract to LoggingService**

```python
# Would require:
logging_service.log_error(error_type, message, status_code, details)
response = UnifiedResponseService.format_error(...)
```

**Rejected because:**
- Adds complexity without benefit
- Risk of forgetting to call logging_service
- Requires passing same context to two services

**Option B: Middleware-Level Logging**

```python
# Log in FastAPI middleware after response is created
```

**Rejected because:**
- Middleware doesn't have access to structured error context
- Would require reverse-engineering the response body
- Less accurate than logging at creation time

**Option C: Make Logging Optional Parameter**

```python
UnifiedResponseService.error(..., log=True)
```

**Rejected because:**
- Adds unnecessary complexity
- Default should always be "log everything"
- No valid use case for log=False

## Consequences

### Positive

- Simple, maintainable code
- Guaranteed logging for all API errors
- Consistent error observability
- No coordination complexity

### Negative

- Theoretical violation of SRP (accepted trade-off)
- Service has two responsibilities (formatting + logging)

### Mitigation

If in the future we need more sophisticated logging (e.g., sending to external services, rate limiting, etc.), we can:

1. Extract a `ErrorLogger` class
2. Inject it into UnifiedResponseService
3. Keep the call in the same place

This refactoring would be straightforward because logging is already centralized.

## Compliance Notes

This decision is **acceptable under DDD/Clean Architecture** because:

- The service is in the infrastructure layer (not domain)
- It handles cross-cutting concerns (error handling, observability)
- Logging is part of the "error response creation" use case
- No domain logic is affected

## References

- Phase 6 Architecture Audit: Issue 6.4A
- Related File: `/Users/jonathanpiette/github/theopenmusicbox/rpi-firmware/back/app/src/services/response/unified_response_service.py:127-130`

## Review

This ADR should be reviewed if:

- We need to send logs to external services (Sentry, DataDog, etc.)
- We need sophisticated log aggregation/filtering
- Performance profiling shows logging is a bottleneck
- We implement a separate audit log system
