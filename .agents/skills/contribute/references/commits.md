# Commit message checks

Load this reference only when preparing or validating one commit message. Policy
discovery and branch validation do not need it.

## Shared message safety

Accept one bounded strict-UTF-8 message. Reject controls other than line feeds,
isolated Unicode surrogates, malformed bytes, sensitive credential-shaped
content, leading blank lines, multiple trailing blank lines, and unsafe file
inputs. Never echo rejected content or invent an author, signer, co-author,
issue, trailer value, or identity.

The subject is the first line. A body or footer block starts only after a blank
second line. Input may have one canonical terminal newline. A separator followed
only by blank or whitespace lines is an empty body; blank or whitespace-only
paragraphs after meaningful body/footer content are also rejected rather than
reported as content. Parse trailers from the
final contiguous trailer block using Git's `Token: value` or `Token #value`
forms. Enforce project-required trailer tokens exactly and require a supplied
non-empty value. Report an omission; do not fill it in.

Subject width 50 and body/footer width 72 are advisories unless explicit
repository policy makes a limit mandatory. Message meaning remains agent and
reviewer judgment. Warn about mechanical claims such as unobserved universal
test success; do not claim body truth from static parsing.

## Classic mode

Classic is the fallback and may also be confirmed or machine-selected policy.
Require a concrete, standalone, imperative subject rather than an issue ID,
vague label, diff narration, past-tense summary, or period-ended sentence. The
checker rejects a closed list of known placeholders such as `Fix bug`, `Update
code`, `Repair bug`, `Handle issue`, `Tweak code`, `Changes`, `WIP`, `Misc`, and
`Phase N`. It may advise review for other mechanically generic-looking phrases,
but it does not promise universal synonym detection or complete natural-language
understanding. The skill and reviewer judge whether wording is genuinely
concrete and imperative. A specific subject such as `Fix parser timeout` remains
valid. The optional body is separated by a blank line and explains material what
and why. A body is not mandatory when the standalone subject is sufficient.

Trailers supplied by the author or required by exact repository policy are
valid in classic mode. The kit never adds one merely by convention.

## Conventional Commits 1.0 mode

Activate this mode only when recognized project policy selects it, clearly
structured executable commitlint requires it, or an agent/user confirms relevant
free-form prose and supplies its source. The checker records that confirmation;
it never claims to have interpreted the prose. History never activates it.

Validate:

```text
<type>[optional scope][optional !]: <description>

[optional body]

[optional footer(s)]
```

Type is lowercase and may contain digits or hyphens after its first letter. Do
not impose a universal type allowlist. `feat` means a feature and `fix` means a
bug fix under Conventional Commits; their semantic truth is agent/reviewer
judgment. Scope is non-empty when parentheses are present. The description is
non-empty.

A breaking change is marked by `!` before the colon, a final `BREAKING CHANGE:
<description>` footer (`BREAKING-CHANGE` is equivalent as a token), or both. A
breaking footer requires exact `: <nonempty>` syntax and must belong to the
final contiguous trailer block; no body line may follow it. The generic ` #value`
trailer form is forbidden for these reserved tokens, and malformed or misplaced
attempts are neither body nor trailers. Other footer tokens use the
safe Git trailer grammar. Footer parsing never executes a configured parser or
hook.

## Local scope readiness

A commit proposal requires staged content. Inspect porcelain status, staged
diff whitespace checks, and added conflict markers. Repeated expected paths make
outside staged paths visible; they do not prove conceptual unrelatedness.
Unstaged and untracked files remain visible because they may indicate omitted or
unrelated work. The agent must decide whether the staged set is one logical
change and whether closely related tests belong in it.

## Commit discipline and best practices

- **Atomic commits:** Each commit must encapsulate exactly one logical, test-verified change. Never bundle unrelated formatting, refactoring, and feature work into one commit.
- **Imperative mood:** Write subjects in the imperative mood ("Add", "Fix", "Refactor", "Update", rather than "Added", "Fixing", or "Fixed").
- **Explain why in the body:** Use the commit body to explain *why* the change was required and what invariant it upholds. Do not merely narrate the diff lines.
- **Reference tracking IDs:** Link to issue, requirement, or task IDs when available (for example, `Fixes #123` or `Implements TASK-204`).
- **Clean diffs only:** Never commit unformatted code, commented-out dead code, failing tests, or unverified work.
