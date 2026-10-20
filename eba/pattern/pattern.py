from dataclasses import dataclass
from typing import Literal

from eba.envelope.topic import is_name
from eba.errors import InvalidTopic

Wildcard = Literal["none", "star", "globstar"]


@dataclass(frozen=True, slots=True)
class Pattern:
    literal: tuple[str, ...]
    wildcard: Wildcard


def parse_pattern(text: str) -> Pattern:
    if not isinstance(text, str) or not text:
        raise InvalidTopic("empty pattern")
    parts = text.split(".")
    if "" in parts:
        raise InvalidTopic(f"illegal pattern: {text!r}")
    for index, part in enumerate(parts):
        if part in ("*", "**"):
            if index != len(parts) - 1:
                raise InvalidTopic(f"wildcard not terminal: {text!r}")
            continue
        if not is_name(part):
            raise InvalidTopic(f"illegal pattern segment: {part!r}")
    wildcard: Wildcard = "none"
    literal = parts
    last = parts[-1]
    if last == "*":
        wildcard = "star"
        literal = parts[:-1]
    elif last == "**":
        wildcard = "globstar"
        literal = parts[:-1]
    return Pattern(tuple(literal), wildcard)


def lookup_keys(parts: list[str]) -> tuple[tuple[Wildcard, str], ...]:
    keys: list[tuple[Wildcard, str]] = [("none", ".".join(parts))]
    if parts:
        keys.append(("star", ".".join(parts[:-1])))
    prefix = ""
    keys.append(("globstar", prefix))
    for part in parts:
        prefix = part if prefix == "" else f"{prefix}.{part}"
        keys.append(("globstar", prefix))
    return tuple(keys)
