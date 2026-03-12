"""Testbench generator."""

from __future__ import annotations

from ..llm_client import LLMClient
from ..prompts.testbench_prompts import TB_SYSTEM_PROMPT, TB_USER_PROMPT


class TestbenchGenerator:
    """Generates a self-checking SystemVerilog testbench.

    Parameters
    ----------
    llm_client:
        An :class:`~eda_agent.llm_client.LLMClient` instance used to call the
        language model.
    """

    def __init__(self, llm_client: LLMClient) -> None:
        self.llm_client = llm_client

    def generate(self, specification: str, rtl_code: str) -> str:
        """Generate a testbench for the given design.

        Parameters
        ----------
        specification:
            Plain-text description of the IC's functionality and interface.
        rtl_code:
            The RTL source produced by :class:`~eda_agent.generators.RTLGenerator`.

        Returns
        -------
        str
            SystemVerilog testbench source code.
        """
        user_prompt = TB_USER_PROMPT.format(
            specification=specification, rtl_code=rtl_code
        )
        return self.llm_client.chat(system=TB_SYSTEM_PROMPT, user=user_prompt)
