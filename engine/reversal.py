"""Strategy reversal utilities."""
from __future__ import annotations

from typing import Any, Dict, Type

from .codex_interface import CodexInterface
from .memory import Memory


def reverse(
    strategy: Dict[str, Any],
    codex_cls: Type[CodexInterface] = CodexInterface,
    memory_cls: Type[Memory] = Memory,
) -> Any:
    """Request a strategy reversal suggestion from the Codex.

    The latest memory shard is loaded and supplied along with the current
    strategy.  The Codex response is returned directly; callers can parse it as
    needed.
    """

    codex = codex_cls()
    memory = memory_cls()
    last_memory = memory.load_latest()
    prompt = (
        "Given the strategy:"\
        f" {strategy}\n"
        f"and the last memory: {last_memory}.\n"
        "Suggest a reversal or adjustment."
    )
    return codex.send_prompt(prompt, system_msg="You evaluate trading rituals")
