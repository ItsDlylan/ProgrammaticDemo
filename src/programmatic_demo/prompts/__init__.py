"""Prompt templates for director agent interactions.

This package contains prompt templates used by the Director agent
for planning scenes, analyzing observations, and deciding on actions.
"""

from pathlib import Path

PROMPTS_DIR = Path(__file__).parent


def load_prompt(name: str) -> str:
    """Load a prompt template by name.

    Args:
        name: Name of the prompt template (without .txt extension).

    Returns:
        The prompt template text.

    Raises:
        FileNotFoundError: If the prompt template doesn't exist.
    """
    prompt_path = PROMPTS_DIR / f"{name}.txt"
    return prompt_path.read_text()


def get_available_prompts() -> list[str]:
    """Get a list of available prompt template names.

    Returns:
        List of prompt names (without .txt extension).
    """
    return [p.stem for p in PROMPTS_DIR.glob("*.txt")]


__all__ = ["load_prompt", "get_available_prompts", "PROMPTS_DIR"]
