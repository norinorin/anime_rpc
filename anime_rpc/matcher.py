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
SEQUENCE_WEIGHT = 100

NumberPosition: TypeAlias = list[tuple[tuple[int, int], str]]


class Candidate(TypedDict):
    index: int
    score: float
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

        befores: list[str] = []
        afters: list[str] = []

        for file_idx, (span, _) in valid_entries:
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

        candidate_anchors: set[tuple[str, str]] = set()
        candidate_anchors.add((commonsuffix(befores), commonprefix(afters)))
        for i in range(len(befores)):
            for j in range(i + 1, len(befores)):
                bc = commonsuffix([befores[i], befores[j]])
                ac = commonprefix([afters[i], afters[j]])
                candidate_anchors.add((bc, ac))

        best_before, best_after = "", ""
        best_inc_score = 0
        best_baked_score = -float("inf")

        for bc, ac in candidate_anchors:
            ss = len(bc) + len(ac) if (bc + ac).strip() else STRUCTURAL_PENALTY
            pat = f"{_escape_normalise_regex(bc)}\\d+{_escape_normalise_regex(ac)}"
            try:
                compiled = re.compile(pat)
            except re.error:
                continue

            matched_nums: list[int] = []
            for file_idx, (_, num) in valid_entries:
                if compiled.search(filenames[file_idx]):
                    matched_nums.append(int(num))

            if len(matched_nums) < MIN_N_SEQUENCE:
                continue

            sorted_nums = sorted(matched_nums)
            inc_score = sum(b > a for a, b in zip(sorted_nums, sorted_nums[1:]))
            baked_score = inc_score * SEQUENCE_WEIGHT + ss

            if baked_score > best_baked_score:
                best_baked_score = baked_score
                best_before, best_after = bc, ac
                best_inc_score = inc_score

        if best_inc_score == 0:
            _LOGGER.debug("No increasing sequence found for index %d, ignoring...", idx)
            continue

        candidates.append(
            Candidate(
                index=idx,
                score=best_baked_score,
                before=best_before,
                after=best_after,
            ),
        )

    if not candidates:
        return None

    _LOGGER.debug("Candidates: %s", candidates)
    best = sorted(candidates, key=lambda x: x["score"], reverse=True)[0]
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
