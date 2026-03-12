"""Utilities for writing generated source files to disk."""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..agent import EDAResult


def save_results(result: "EDAResult", output_dir: str = "output") -> dict[str, Path]:
    """Write all generated artefacts to *output_dir*.

    Creates the output directory if it does not already exist.

    Parameters
    ----------
    result:
        An :class:`~eda_agent.agent.EDAResult` instance returned by
        :meth:`~eda_agent.agent.EDAAgent.run`.
    output_dir:
        Directory path where the files will be written.

    Returns
    -------
    dict[str, Path]
        A mapping of artefact name to the absolute path of the written file.
        Keys: ``"rtl"``, ``"testbench"``, ``"sva"``.
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    files: dict[str, Path] = {
        "rtl": out / "design.sv",
        "testbench": out / "tb_design.sv",
        "sva": out / "design_sva.sv",
    }

    files["rtl"].write_text(result.rtl, encoding="utf-8")
    files["testbench"].write_text(result.testbench, encoding="utf-8")
    files["sva"].write_text(result.sva, encoding="utf-8")

    return {k: v.resolve() for k, v in files.items()}
