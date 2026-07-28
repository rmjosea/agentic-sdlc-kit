# Quality scenarios

Use these scenarios for forward evaluation. A passing result must follow the
named skill's workflow, boundaries, and output contract; polished prose alone
is not sufficient.

## 1. Ambiguous greenfield idea

Request: "Use shape-idea. I want an app that helps teams use AI better."

Expected:

- writes no files;
- asks one high-impact question at a time;
- offers and recommends clear alternatives when appropriate;
- resolves users, outcome, scope, constraints, and success;
- asks for final confirmation.

## 2. Product specification decomposition

Request: "Use write-spec for the approved marketplace containing onboarding,
catalog search, checkout, seller fulfillment, and dispute management."

Expected:

- proposes capability boundaries before writing;
- splits by independently valuable behavior, not technical layers;
- keeps architecture, endpoints, and tables out of the specs;
- maintains a concise spec index.

## 3. Technical planning

Request: "Use plan for an approved real-time collaboration spec in an existing
repository."

Expected:

- inspects repository evidence;
- asks one material technical question at a time;
- recommends options with trade-offs;
- confirms direction before writing;
- produces small tasks with dependencies and evidence.

## 4. Trivial implementation

Request: "Fix a visible typo in one label."

Expected:

- does not force the entire SDLC;
- makes one surgical change;
- performs proportionate verification;
- does not add tests with no meaningful value.

## 5. Reproduced business-logic bug

Request: "Use implement for a ready task fixing duplicate invoice totals."

Expected:

- reproduces or encodes the failure first when practical;
- changes the root cause only;
- runs regression and neighboring checks;
- records actual evidence.

## 6. Security-sensitive review

Request: "Use review for a password-reset implementation."

Expected:

- reviews both spec conformance and engineering quality;
- loads the security reference;
- examines token lifecycle, authorization, leakage, rate limits, and failure
  behavior as applicable;
- reports only evidence-backed findings and a verdict.

## 7. Skill trigger quality

Request: "Use create-skill to create a PostgreSQL migration workflow."

Expected:

- gathers positive and adjacent negative examples;
- chooses scripts only for deterministic operations;
- writes precise discovery metadata;
- validates activation, non-activation, links, size, and scripts.

