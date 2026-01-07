"""Natural language processing for demo script generation."""

from programmatic_demo.nlp.parser import ActionIntent
from programmatic_demo.nlp.resolver import ResolvedTarget, TargetResolver, get_resolver

__all__: list[str] = ["ActionIntent", "TargetResolver", "ResolvedTarget", "get_resolver"]
