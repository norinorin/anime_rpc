from __future__ import annotations

import logging
import mimetypes
import re
from os.path import commonprefix
from pathlib import Path
from typing import TypeAlias, TypedDict

_LOGGER = logging.getLogger("automatic_matcher")

EP = "%ep%"
MIN_N_SEQUENCE = 2
SPACE_NORMALIZER = re.compile(r"\\\s+")
NUM_NORMALIZER = re.compile(r"\d+")
HANGING_BACKSLASH = re.compile(r"(?<!\\)\\$")
STRUCTURAL_PENALTY = -5

NumberPosition: TypeAlias = list[tuple[tuple[int, int], str]]
Span: TypeAlias = tuple[int, int]


class Candidate(TypedDict):
    index: int
    increasing_score: float
    structural_score: float
    before: str
    after: str


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


def build_filename_pattern(filenames: list[str]) -> str | None:
    filenames = exclude_non_media_files(filenames)
    if len(filenames) < MIN_N_SEQUENCE:
        return None

    _LOGGER.debug("Input filenames: %s", filenames)
    number_positions: list[NumberPosition] = []

    for name in filenames:
        positions: NumberPosition = []
        number_positions.append(positions)
        for match in re.finditer(r"\d+", name):
            positions.append((match.span(), match.group()))

    _LOGGER.debug("Number positions: %s", number_positions)
    return infer_episode_pattern(filenames, number_positions)


def commonsuffix(filenames: list[str]) -> str:
    rev = [f[::-1] for f in filenames]
    return commonprefix(rev)[::-1]


def infer_episode_pattern(
    filenames: list[str],
    number_positions: list[NumberPosition],
) -> str | None:
    if not (filenames and number_positions):
        _LOGGER.debug("No filenames or number positions found")
        return None

    candidates: list[Candidate] = []
    max_len = max(len(p) for p in number_positions)

    if max_len == 0:
        _LOGGER.debug("No numbers found in filenames")
        return None

    for idx in range(max_len):
        valid_entries = [
            (i, position[idx])
            for i, position in enumerate(number_positions)
            if idx < len(position)
        ]

        if len(valid_entries) < MIN_N_SEQUENCE:
            continue

        nums: list[int] = []
        spans: list[tuple[int, Span]] = []
        befores: list[str] = []
        afters: list[str] = []

        for file_idx, (span, num) in valid_entries:
            nums.append(int(num))
            spans.append((file_idx, span))

            start, end = span
            filename = filenames[file_idx]
            before = filename[:start]
            after = filename[end:]
            befores.append(before)
            afters.append(after)
            _LOGGER.debug(
                "Filename: %r, Before: %r, After: %r",
                filename,
                before,
                after,
            )

        increasing_score = sum(b > a for a, b in zip(nums, nums[1:]))
        before_common = commonsuffix(befores)
        after_common = commonprefix(afters)
        structural_score = (
            len(before_common) + len(after_common)
            if (before_common + after_common).strip()
            else STRUCTURAL_PENALTY
        )

        if increasing_score == 0:
            _LOGGER.debug("No increasing sequence found for index %d, ignoring...", idx)
            continue

        candidates.append(
            Candidate(
                index=idx,
                increasing_score=increasing_score,
                structural_score=structural_score,
                before=before_common,
                after=after_common,
            ),
        )

    if not candidates:
        return None

    _LOGGER.debug("Candidates: %s", candidates)
    best = sorted(
        candidates,
        key=lambda x: (-x["increasing_score"] - x["structural_score"]),
    )[0]

    pattern = (
        f"{_escape_normalise_regex(best['before'])}{EP}"
        f"{_escape_normalise_regex(best['after'])}"
    )
    _LOGGER.debug("Generated pattern: %s", pattern)
    return pattern


def generate_regex_pattern(filedir: Path) -> str | None:
    filenames: list[str] = [f.name for f in filedir.iterdir() if f.is_file()]
    if not (pattern := build_filename_pattern(filenames)):
        return None

    _LOGGER.debug("Generated pattern: %s", pattern)
    _LOGGER.info("Appending generated pattern to .rpc...")

    # FIXME: write in a dedicated thread
    with (filedir / ".rpc").open("a") as f:
        f.write(f"\n# Automatically generated pattern\nmatch={pattern}\n")

    return pattern
