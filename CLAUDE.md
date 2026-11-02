# O9-RD Multi-Agent Engineering Governance Rules (.cursorrules / CLAUDE.md)

You operate under the **O9-RD Software Engineering Governance Protocol**:

1. **G0.5 Two-Way Confirmation First**: Never write or modify business code immediately upon receiving a vague request. First restate: (a) Goal, (b) In-Scope, (c) Out-of-Scope, and (d) Testable Acceptance Criteria (AC). Wait for explicit user confirmation.
2. **G1/G3 Contract & Baseline Lock**: Update `o9_workspace/spec_and_contracts.md` (data schema, behavior invariants, test command) before coding. Never modify locked AC to make failing tests pass.
3. **G4 Scoped Write & Zero Stubbing**: Modify only files within the agreed scope. Never leave `TODO`/`FIXME` placeholders, hardcoded mock returns in production paths, or deleted test assertions (`assert True`).
4. **G5 Black-Box Verification First**: When acting as QA/Tester in a fresh session, test strictly against the external contract and test harness BEFORE inspecting implementation source code. Developers cannot mark their own bugs as closed.
5. **G7 Decoupled Release**: Passing tests does not authorize production deployment or destructive database actions without explicit human sign-off.
