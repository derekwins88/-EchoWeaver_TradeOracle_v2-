"""Core execution loop for the EchoWeaver capsule."""
from __future__ import annotations

import yaml
from typing import Any, Dict, Type

from .codex_interface import CodexInterface
from .memory import Memory


def run(
    motif: str,
    config_path: str = "config/strategy.yaml",
    codex_cls: Type[CodexInterface] = CodexInterface,
    memory_cls: Type[Memory] = Memory,
) -> Any:
    """Execute a single motif cycle through the Codex interface.

    The function loads the strategy configuration, sends the motif and
    configuration to the Codex model and stores the resulting response in an
    ``.immshard`` file.

    Parameters
    ----------
    motif:
        The motif or signal to be evaluated by the model.
    config_path:
        Path to the YAML strategy configuration.
    codex_cls:
        Class implementing the Codex interface.  This is primarily for
        dependency injection during testing.
    memory_cls:
        Class implementing the memory storage API.
    """

    with open(config_path, "r", encoding="utf-8") as handle:
        config: Dict[str, Any] = yaml.safe_load(handle)

    codex = codex_cls()
    prompt = f"Motif: {motif}\nConfig: {config}"
    response = codex.send_prompt(prompt, system_msg="You are the EchoWeaver Codex")

    memory = memory_cls()
    memory.save_trade({"motif": motif, "config": config, "response": response})
    return response
