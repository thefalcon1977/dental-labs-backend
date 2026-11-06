"""Helpers shared by the DAL modules."""

LIKE_ESCAPE = "\\"


def like_prefix(search: str, lowercase: bool = True) -> str:
    """Build a LIKE prefix pattern with wildcards in the input escaped.

    Args:
        search: User-supplied search text.
        lowercase: Lowercase the text (for columns stored lowercase).

    Returns:
        Pattern such as ``jane%``.
    """
    value = search.strip().lower() if lowercase else search.strip()
    for char in (LIKE_ESCAPE, "%", "_"):
        value = value.replace(char, LIKE_ESCAPE + char)
    return f"{value}%"
