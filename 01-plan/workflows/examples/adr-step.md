# Example: Architecture Decision Record Authoring

<!-- @verifies REQ-ARCH-01 -->
<!-- @verifies REQ-ARCH-02 -->

This example demonstrates a completed ADR embedded inside a plan.

```markdown
### 3.1 Architectural Decisions

#### ADR-001: Adopt JWT Authentication via EdDSA
- **Status**: Accepted
- **Context**: The existing session-cookie implementation does not scale to mobile clients and multi-region deployments.
- **Decision**: Migrate authentication tokens to RFC 7519 JSON Web Tokens signed with Ed25519 (EdDSA).
- **Consequences**:
  - *Positive*: Stateless authorization, zero database lookups per request, fast asymmetric verification.
  - *Negative*: Token revocation requires an in-memory or Redis deny-list for active sessions.
- **Alternatives Considered**:
  - *RSA-256*: Rejected due to larger token size and slower cryptographic signing benchmarks.
  - *Opaque Bearer Tokens*: Rejected due to high database lookup latency.
```
