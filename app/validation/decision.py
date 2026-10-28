"""Turn validation flags into one of three outcomes."""

REJECT_FLAGS = {"duplicate"}


def decide(flags: list[str]) -> str:
    if not flags:
        return "approve"
    if REJECT_FLAGS & set(flags):
        return "reject"
    return "review"
