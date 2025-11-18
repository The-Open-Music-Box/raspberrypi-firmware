# Architecture Decision Records (ADRs)

This directory contains Architecture Decision Records for TheOpenMusicBox RPI Firmware.

## What is an ADR?

An Architecture Decision Record (ADR) captures an important architectural decision made along with its context and consequences. ADRs help document why certain design choices were made and provide guidance for future maintainers.

## ADR Index

| ADR | Title | Status | Date |
|-----|-------|--------|------|
| [001](001-unified-response-service-logging.md) | UnifiedResponseService Logging Behavior | Accepted | 2025-11-09 |
| [002](002-state-event-coordinator-throttling.md) | StateEventCoordinator Throttling Responsibility | Accepted | 2025-11-09 |

## ADR Lifecycle

- **Proposed**: Under discussion
- **Accepted**: Decision made and implemented
- **Deprecated**: No longer recommended (but still documented)
- **Superseded**: Replaced by another ADR

## Creating a New ADR

When making a significant architectural decision:

1. Copy the template (to be created)
2. Number sequentially (e.g., 003-your-decision.md)
3. Fill in the sections:
   - **Status**: Proposed/Accepted/Deprecated/Superseded
   - **Context**: What is the problem?
   - **Decision**: What did we decide?
   - **Rationale**: Why this decision?
   - **Consequences**: What are the trade-offs?
   - **Alternatives Considered**: What else did we evaluate?
4. Update this README index
5. Submit for review

## Related Documentation

- [Architecture Overview](../README.md) (to be created)
- [Clean Architecture Principles](../../ARCHITECTURE.md) (if exists)
- [Phase 6 Audit](../../../AUDIT_FIXES_TODO.md)

## Review Process

ADRs should be reviewed when:

- The context changes significantly
- New information contradicts the decision
- Performance or scalability issues arise
- Better alternatives become available

Each ADR includes a "Review" section specifying when it should be reconsidered.
