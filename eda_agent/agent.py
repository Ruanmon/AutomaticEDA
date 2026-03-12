"""Main EDA agent orchestrator."""

from __future__ import annotations

from dataclasses import dataclass

from .generators.rtl_generator import RTLGenerator
from .generators.sva_generator import SVAGenerator
from .generators.testbench_generator import TestbenchGenerator
from .llm_client import LLMClient


@dataclass
class EDAResult:
    """Container for the artefacts produced by :class:`EDAAgent`.

    Attributes
    ----------
    specification:
        The original IC specification provided by the user.
    rtl:
        Generated SystemVerilog RTL source code.
    testbench:
        Generated SystemVerilog testbench source code.
    sva:
        Generated SystemVerilog Assertions (SVA) source code.
    """

    specification: str
    rtl: str
    testbench: str
    sva: str


class EDAAgent:
    """Agent that understands an IC specification and generates RTL, testbench,
    and SVA artefacts using a large language model.

    Parameters
    ----------
    llm_client:
        A pre-configured :class:`~eda_agent.llm_client.LLMClient`.  When
        *None* (default) a new client is created from the remaining keyword
        arguments.
    model:
        Model name forwarded to :class:`~eda_agent.llm_client.LLMClient` when
        *llm_client* is not supplied (default: ``"gpt-4o"``).
    **kwargs:
        Additional keyword arguments forwarded to
        :class:`~eda_agent.llm_client.LLMClient`.

    Examples
    --------
    >>> from eda_agent import EDAAgent
    >>> agent = EDAAgent()
    >>> result = agent.run("4-bit synchronous up-counter with synchronous reset")
    >>> print(result.rtl)
    """

    def __init__(
        self,
        llm_client: LLMClient | None = None,
        model: str = "gpt-4o",
        **kwargs,
    ) -> None:
        if llm_client is None:
            llm_client = LLMClient(model=model, **kwargs)
        self.llm_client = llm_client
        self._rtl_gen = RTLGenerator(llm_client)
        self._tb_gen = TestbenchGenerator(llm_client)
        self._sva_gen = SVAGenerator(llm_client)

    def run(self, specification: str, verbose: bool = True) -> EDAResult:
        """Run the full EDA pipeline for *specification*.

        The method calls the LLM three times in sequence:

        1. **RTL generation** – produce synthesizable SystemVerilog RTL.
        2. **Testbench generation** – produce a self-checking testbench that
           exercises the RTL.
        3. **SVA generation** – produce SystemVerilog assertions for formal
           verification.

        Parameters
        ----------
        specification:
            Plain-text description of the IC's functionality and interface.
        verbose:
            When *True* (default) progress messages are printed to stdout.

        Returns
        -------
        EDAResult
            Dataclass containing the specification and all generated artefacts.
        """
        if verbose:
            print("[EDA Agent] Generating RTL …")
        rtl = self._rtl_gen.generate(specification)

        if verbose:
            print("[EDA Agent] Generating Testbench …")
        testbench = self._tb_gen.generate(specification, rtl)

        if verbose:
            print("[EDA Agent] Generating SVA …")
        sva = self._sva_gen.generate(specification, rtl)

        if verbose:
            print("[EDA Agent] Done.")

        return EDAResult(
            specification=specification,
            rtl=rtl,
            testbench=testbench,
            sva=sva,
        )
