# Testing strategy

Select tests by risk and observable behavior, using the cheapest level that can
prove the outcome and its important failure modes.

## Choose the seam and level

- Prefer tests through stable public seams: public functions, commands, APIs,
  rendered behavior, or persisted boundaries that should survive refactoring.
- Agree the seam before proceeding when a new one would materially change a
  contract or architecture. Do not interrupt trivial repository-standard tests.
- Use focused unit or component tests for deterministic behavior, integration
  tests for boundaries a unit test cannot represent, and end-to-end tests only
  for critical cross-component journeys.
- For visual work, inspect rendered behavior with available browser or screenshot
  tooling instead of relying only on source text.
- Match evidence to risk: add regression and relevant failure-path coverage for
  medium risk, plus applicable rollback or recovery evidence for high risk.

## Build vertical evidence

Prefer a vertical slice or tracer bullet that crosses the smallest real path:
one test -> minimal implementation -> run -> repeat. This keeps behavior and
implementation feedback connected instead of building a whole test layer first.

Use red-green-refactor when a focused failure is valuable, especially for a
reproduced bug, business rule, public contract, or deterministic transformation:

1. Add one behavior-focused test and confirm red for the expected reason.
2. Implement the smallest change that makes it green.
3. Run neighboring outcome-relevant tests.
4. Refactor only while the evidence remains green, then repeat for the next
   behavior.

A trivial, reversible repository-standard change need not force a new test when
an existing check provides proportionate evidence.

## Avoid weak tests

- **Tautological tests** repeat the implementation, type declaration, fixture, or
  framework guarantee and cannot catch a meaningful defect.
- **Implementation-coupled tests** assert call order, private or internal state,
  or mocks of internals rather than stable behavior; they make safe refactoring
  look broken. Mock only an actual external boundary when needed.
- **Horizontal slicing** builds broad test or implementation layers before any
  behavior works, such as bulk controller, service, and repository tests. Prefer
  the vertical tracer-bullet loop above.

## Anti-mock tautology ("Real Boundaries Only")

Motivating failure: in a study of 1.2 million 2025 commits, 36% of coding-agent
commits added mocks versus 26% of other commits
([arXiv:2602.00409](https://arxiv.org/abs/2602.00409)). Tests that mock internal
code and assert only calls pass by construction and catch no regressions.

- Never mock the unit under test, domain entities, internal utility functions, or private state.
- Mock only uncontrollable external I/O boundaries: third-party network APIs, system wall-clock time, or hardware processes that cannot run in memory.
- Prefer lightweight in-memory fakes over dynamic mocks when representing stateful external services.
- Never write tests whose sole assertion is `assert_called_once()` or interaction counts. Tests must assert observable domain output, state transitions, or deterministic return values.

## Preserve existing tests

Motivating failure: when an existing test fails, agents sometimes delete, skip,
or weaken it to obtain a green run instead of fixing the regression.

- Never delete, silence, or weaken assertions in existing test files to make a change pass.
- A failing pre-existing test is authoritative evidence of an unintended regression introduced by the new change, not evidence that the test was obsolete.
- Any legitimate change to an existing test assertion requires confirmed upstream intent or an approved specification revision.

Keep each test focused on one meaningful behavior with a diagnostic failure.
