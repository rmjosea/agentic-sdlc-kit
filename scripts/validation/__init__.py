"""Source validation responsibility modules."""


def responsibility_modules() -> tuple[str, ...]:
    """Return the stable source-validator responsibility names."""
    return ("distribution", "artifacts", "documentation", "semantics")
