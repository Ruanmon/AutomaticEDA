"""Utility for discovering and loading RTL source files from a directory."""

from __future__ import annotations

from pathlib import Path

# File extensions recognised as RTL source files.
RTL_EXTENSIONS: frozenset[str] = frozenset({".sv", ".v", ".svh", ".vh"})


def collect_rtl_files(directory: str | Path) -> dict[str, str]:
    """Recursively collect RTL source files from *directory*.

    Searches for files with extensions ``.sv``, ``.v``, ``.svh``, and ``.vh``
    and returns their contents keyed by their path relative to *directory*.

    Parameters
    ----------
    directory:
        Root directory to search.  The path must exist and be a directory.

    Returns
    -------
    dict[str, str]
        A mapping of ``relative_path_str → file_content`` for every RTL file
        found.  Returns an empty dict when no RTL files are found.

    Raises
    ------
    NotADirectoryError
        If *directory* does not exist or is not a directory.
    """
    root = Path(directory)
    if not root.is_dir():
        raise NotADirectoryError(f"RTL directory not found: {directory}")

    rtl_files: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.suffix.lower() in RTL_EXTENSIONS:
            rel = str(path.relative_to(root))
            rtl_files[rel] = path.read_text(encoding="utf-8", errors="replace")
    return rtl_files


def format_rtl_context(rtl_files: dict[str, str]) -> str:
    """Format a mapping of RTL files into a single string for LLM consumption.

    Parameters
    ----------
    rtl_files:
        Mapping returned by :func:`collect_rtl_files`.

    Returns
    -------
    str
        A string where each file is introduced by a header and its content
        follows verbatim, separated by blank lines.
    """
    if not rtl_files:
        return "(no RTL files found)"

    sections: list[str] = []
    for filename, content in rtl_files.items():
        sections.append(f"--- {filename} ---\n{content}")
    return "\n\n".join(sections)
