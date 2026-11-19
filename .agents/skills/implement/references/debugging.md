# Debugging loop

Use this loop when the cause is not already established:

1. Reproduce the failure reliably.
2. Minimize the reproducer and identify the failing boundary.
3. Gather evidence from logs, state, inputs, and recent changes.
4. Form one falsifiable hypothesis.
5. Run the smallest experiment that can disprove it.
6. Fix the root cause, not the visible symptom.
7. Add regression protection proportional to the risk.
8. Run neighboring checks and remove temporary instrumentation.

Do not stack speculative fixes. After a failed hypothesis, revert its incidental
changes before testing the next one.

## Circuit breaker protocol

Motivating failure: failure analyses of coding agents on SWE-bench Verified
report flawed reasoning and cognitive deadlocks as the main agentic failure
source: the agent keeps editing the same lines without revisiting its
assumptions ([arXiv:2509.13941](https://arxiv.org/abs/2509.13941)).

If a fix attempt fails twice consecutively:

1. **Halt code edits immediately.** Do not make a third attempt on the same code path.
2. **Step back and isolate runtime state.** Add targeted, temporary log statements or print statements to observe the actual execution values at the failure boundary.
3. **Re-read the caller's contract and stack trace.** Re-read the calling context, type definitions, and upstream invariants rather than focusing solely on the line of the exception.
4. **Formulate a negative hypothesis.** Explicitly state why the previous mental model of the bug was disproven by the observed failure before writing any new code.
5. **Revert failed speculative edits** before testing the new hypothesis.
