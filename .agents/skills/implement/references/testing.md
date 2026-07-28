# Testing strategy

Select tests by risk and observable behavior.

- Use test-first development for reproduced bugs, business rules, contracts,
  transformations, and other deterministic behavior.
- Add regression evidence before fixing a bug when practical.
- Prefer tests through stable public seams over private implementation details.
- Use integration tests at boundaries that unit tests cannot represent.
- Use end-to-end tests only for critical cross-component journeys.
- For visual work, verify rendered behavior with the available browser or
  screenshot tooling instead of relying only on source inspection.
- Avoid tests that merely repeat type checks, framework behavior, or mocks.
- Keep each test focused on one meaningful behavior and failure message.

Use red-green-refactor when it improves feedback:

1. Create a focused failing test.
2. Run it and confirm it fails for the expected reason.
3. Implement the smallest passing change.
4. Run relevant neighboring tests.
5. Refactor only while all tests stay green.

