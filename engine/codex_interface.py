"""OpenAI Codex interface for motif-driven strategy refinement."""
from __future__ import annotations

import os
from typing import Optional

try:  # pragma: no cover - import guard for environments without openai
    import openai  # type: ignore
except Exception:  # pragma: no cover - if openai isn't installed
    openai = None


class CodexInterface:
    """Wrapper around OpenAI's chat completion API.

    The class is intentionally lightweight so it can be mocked easily in
    tests.  If the OpenAI package or API key is missing, calls will safely
    return ``None`` instead of raising an exception.
    """

    def __init__(self, model: str = "gpt-4", temperature: float = 0.7) -> None:
        self.model = model
        self.temperature = temperature
        self.api_key = os.getenv("OPENAI_API_KEY")
        if openai and self.api_key:  # pragma: no branch
            openai.api_key = self.api_key

    def send_prompt(self, prompt: str, system_msg: Optional[str] = None) -> Optional[str]:
        """Send a prompt to the model and return the response text.

        Parameters
        ----------
        prompt:
            The user content to send to the model.
        system_msg:
            Optional system message to prepend to the conversation.

        Returns
        -------
        Optional[str]
            The model's reply if successful, otherwise ``None``.
        """

        if not (openai and self.api_key):  # pragma: no cover - no API scenario
            return None

        messages = []
        if system_msg:
            messages.append({"role": "system", "content": system_msg})
        messages.append({"role": "user", "content": prompt})

        try:
            response = openai.ChatCompletion.create(
                model=self.model, messages=messages, temperature=self.temperature
            )
            return response.choices[0].message["content"].strip()
        except Exception as exc:  # pragma: no cover - API errors aren't predictable
            print(f"[Codex ERROR]: {exc}")
            return None
