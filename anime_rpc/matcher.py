from __future__ import annotations

import logging
import mimetypes
import re
from collections import defaultdict
from os.path import commonprefix as os_commonprefix
from pathlib import Path

EP = "%ep%"
MIN_N_SEQUENCE = 2
_LOGGER = logging.getLogger("automatic_matcher")
SPACE_NORMALIZER = re.compile(r"\\\s+")
NUM_NORMALIZER = re.compile(r"\d+")
HANGING_BACKSLASH = re.compile(r"(?<!\\)\\$")


def _escape_normalise_regex(pattern: str) -> str:
    pattern = re.escape(pattern)
    pattern = SPACE_NORMALIZER.sub(r"\\s+", pattern)
    return NUM_NORMALIZER.sub(r"\\d+", pattern)


def exclude_non_media_files(filenames: list[str]) -> list[str]:
    if len(filenames) < MIN_N_SEQUENCE:
        return filenames

    return [
        f
        for f in filenames
        if (m := mimetypes.guess_type(f)[0]) and m.split("/", maxsplit=1)[0] == "video"
    ]


def strip_digits(text: str) -> str:
    while text and text[-1].isdigit():
        text = text[:-1]
    while text and text[0].isdigit():
        text = text[1:]
    return text


def common_prefix(strings: list[str], *, reverse: bool = False) -> str:
    if reverse:
        strings = [s[::-1] for s in strings]
    ret = os_commonprefix(strings)
    ret = strip_digits(ret)
    if reverse:
        ret = ret[::-1]
    return ret


def find_most_variable_number_parts(
    filenames: list[str],
    prefix: str,
    suffix: str,
) -> tuple[int, int] | None:
    number_positions: defaultdict[tuple[int, int], list[str]] = defaultdict(list)

    for name in filenames:
        middle = name[len(prefix) : len(name) - len(suffix) if suffix else None]
        for match in re.finditer(r"\d+", middle):
            number_positions[match.span()].append(match.group())

    variability = {
        span: len(set(numbers)) for span, numbers in number_positions.items()
    }
    if not variability:
        return None

    sorted_spans = sorted(variability.items(), key=lambda x: -x[1])
    return sorted_spans[0][0]


def extract_ep_anchor(patterns: list[str]) -> str | None:
    if not patterns:
        return None

    befores: list[str] = []
    afters: list[str] = []

    for p in patterns:
        if EP not in p:
            continue

        before, _, after = p.partition(EP)
        befores.append(before)
        afters.append(after)

    prefix = common_prefix(befores)
    suffix = common_prefix(afters, reverse=False)
    pattern = f"{prefix}{EP}{suffix}"
    return HANGING_BACKSLASH.sub("", pattern)


def build_filename_pattern(filenames: list[str]) -> str | None:
    filenames = exclude_non_media_files(filenames)
    if len(filenames) < MIN_N_SEQUENCE:
        return None

    patterns: list[str] = []
    prefix = common_prefix(filenames)
    suffix = common_prefix(filenames, reverse=True)
    ep_span = find_most_variable_number_parts(filenames, prefix, suffix)

    _LOGGER.debug("Detected common prefix: %s", prefix)
    _LOGGER.debug("Detected common suffix: %s", suffix)
    _LOGGER.debug("Detected ep span: %s", ep_span)

    if ep_span is None:
        return None

    patterns = []
    for name in filenames:
        middle = name[len(prefix) : len(name) - len(suffix) if suffix else None]
        before = prefix + middle[: ep_span[0]]
        after = middle[ep_span[1] :] + suffix
        patterns.append(rf"{before}{EP}{after}")

    if len(patterns) < MIN_N_SEQUENCE:
        return None

    _LOGGER.debug("Possible patterns: %s", patterns)
    patterns = [_escape_normalise_regex(p) for p in patterns]
    return extract_ep_anchor(patterns)


def generate_regex_pattern(filedir: str) -> str | None:
    dir_path = Path(filedir)
    filenames: list[str] = [f.name for f in dir_path.iterdir() if f.is_file()]
    if not (pattern := build_filename_pattern(filenames)):
        return None

    _LOGGER.debug("Generated pattern: %s", pattern)
    _LOGGER.info("Appending generated pattern to rpc.config...")

    with (dir_path / "rpc.config").open("a") as f:
        f.write(f"\n# Automatically generated pattern\nmatch={pattern}\n")

    return pattern
