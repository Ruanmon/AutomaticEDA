"""LLM client wrapper for the EDA agent."""

import os
from openai import OpenAI


class LLMClient:
    """Thin wrapper around the OpenAI chat-completions API.

    Parameters
    ----------
    model:
        Model name to use (default: ``gpt-4o``).
    api_key:
        OpenAI API key.  Falls back to the ``OPENAI_API_KEY`` environment
        variable when not supplied.
    base_url:
        Custom API base URL (useful for Azure OpenAI or compatible endpoints).
        Falls back to the ``OPENAI_BASE_URL`` environment variable.
    temperature:
        Sampling temperature (default: 0.1 for more deterministic output).
    """

    def __init__(
        self,
        model: str = "gpt-4o",
        api_key: str | None = None,
        base_url: str | None = None,
        temperature: float = 0.1,
    ) -> None:
        self.model = model
        self.temperature = temperature
        self.client = OpenAI(
            api_key=api_key or os.environ.get("OPENAI_API_KEY"),
            base_url=base_url or os.environ.get("OPENAI_BASE_URL") or None,
        )

    def chat(self, system: str, user: str) -> str:
        """Send a chat request and return the assistant reply as a string.

        Parameters
        ----------
        system:
            System-role message.
        user:
            User-role message.

        Returns
        -------
        str
            The content of the model's response.
        """
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=self.temperature,
        )
        return response.choices[0].message.content
