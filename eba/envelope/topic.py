import re

from eba.envelope.errors import EnvelopeBuildError

_NAME = re.compile(r"[a-z][a-z0-9_]*\Z")


def is_name(segment: str) -> bool:
    return isinstance(segment, str) and _NAME.fullmatch(segment) is not None


def split_topic(topic: str) -> list[str]:
    if not isinstance(topic, str) or not topic:
        raise EnvelopeBuildError("topic must be a nonempty string")
    parts = topic.split(".")
    for part in parts:
        if not is_name(part):
            raise EnvelopeBuildError(f"illegal topic segment: {part!r}")
    return parts
