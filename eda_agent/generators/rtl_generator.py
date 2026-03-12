"""RTL code generator."""

from __future__ import annotations

from ..llm_client import LLMClient
from ..prompts.rtl_prompts import RTL_SYSTEM_PROMPT, RTL_USER_PROMPT


class RTLGenerator:
    """Generates synthesizable SystemVerilog RTL from an IC specification.

    Parameters
    ----------
    llm_client:
        An :class:`~eda_agent.llm_client.LLMClient` instance used to call the
        language model.
    """

    def __init__(self, llm_client: LLMClient) -> None:
        self.llm_client = llm_client

    def generate(self, specification: str) -> str:
        """Generate RTL code for the given IC specification.

        Parameters
        ----------
        specification:
            Plain-text description of the IC's functionality and interface.

        Returns
        -------
        str
            SystemVerilog RTL source code.
        """
        user_prompt = RTL_USER_PROMPT.format(specification=specification)
        return self.llm_client.chat(system=RTL_SYSTEM_PROMPT, user=user_prompt)
