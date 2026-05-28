from __future__ import annotations

from itertools import pairwise
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
BRACKETED_HASH = re.compile(r"(\s*[\[\(][A-Fa-f0-9]{6,9}[\]\)])")
STRUCTURAL_PENALTY = -5
SEQUENCE_WEIGHT = 100

NumberPosition: TypeAlias = list[tuple[tuple[int, int], str]]


class Candidate(TypedDict):
    index: int
    score: float
    matched_befores: list[str]
    matched_afters: list[str]


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
        hash_spans = [m.span() for m in BRACKETED_HASH.finditer(name)]
        for match in re.finditer(r"\d+", name):
            if any(
                start <= match.start() and match.end() <= end
                for start, end in hash_spans
            ):
                continue
            positions.append((match.span(), match.group()))

    _LOGGER.debug("Number positions: %s", number_positions)
    return infer_episode_pattern(filenames, number_positions)


def commonsuffix(filenames: list[str]) -> str:
    rev = [f[::-1] for f in filenames]
    return commonprefix(rev)[::-1]


def analyse_side(strings: list[str]) -> tuple[str, int]:
    if not strings:
        return "", 0

    clean = [BRACKETED_HASH.sub("", s) for s in strings]
    has_hash = clean != strings

    if len(set(clean)) <= 1:
        if not has_hash:
            return _escape_normalise_regex(strings[0]), 0
        parts = BRACKETED_HASH.split(strings[0])
        pat = "".join(
            ".*" if i % 2 else _escape_normalise_regex(p) for i, p in enumerate(parts)
        )
        return pat, 0

    cp = commonprefix(clean)
    cs = commonsuffix(clean)

    # prevent static affixes from stealing partial alphabetical words from the title
    if cp and re.search(r"[A-Za-z]$", cp):
        if any(len(s) > len(cp) and re.match(r"[A-Za-z]", s[len(cp)]) for s in clean):
            cp = re.sub(r"[A-Za-z]+$", "", cp)

    if cs and re.search(r"^[A-Za-z]", cs):
        if any(
            len(s) > len(cs) and re.match(r"[A-Za-z]", s[-len(cs) - 1]) for s in clean
        ):
            cs = re.sub(r"^[A-Za-z]+", "", cs)

    ph = r"\s*(?:\[[A-Fa-f0-9]{{6,9}}\]|\([A-Fa-f0-9]{{6,9}}\))" if has_hash else ""
    variance = max(0, len(clean[0]) - len(cp) - len(cs))
    return (
        f"{_escape_normalise_regex(cp)}{{TAG}}{ph}{_escape_normalise_regex(cs)}",
        variance,
    )


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

        best_matches: list[tuple[int, tuple[int, int]]] = []
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
            matches: list[tuple[int, tuple[int, int]]] = []
            for file_idx, (span, num) in valid_entries:
                if compiled.search(filename := filenames[file_idx]):
                    matched_nums.append(int(num))
                    matches.append((file_idx, span))

            if len(matched_nums) < MIN_N_SEQUENCE:
                continue

            sorted_nums = sorted(matched_nums)
            inc_score = sum(b > a for a, b in pairwise(sorted_nums))
            baked_score = inc_score * SEQUENCE_WEIGHT + ss

            if baked_score > best_baked_score:
                best_baked_score = baked_score
                best_inc_score = inc_score
                best_matches = matches

        if best_inc_score == 0:
            _LOGGER.debug("No increasing sequence found for index %d, ignoring...", idx)
            continue

        candidates.append(
            Candidate(
                index=idx,
                score=best_baked_score,
                matched_befores=[filenames[i][: s[0]] for i, s in best_matches],
                matched_afters=[filenames[i][s[1] :] for i, s in best_matches],
            ),
        )

    if not candidates:
        return None

    _LOGGER.debug("Candidates: %s", candidates)
    best = max(candidates, key=lambda x: x["score"])
    head_pat, head_var = analyse_side(best["matched_befores"])
    tail_pat, tail_var = analyse_side(best["matched_afters"])
    head_tag = "%title%" if head_var > tail_var else ".*"
    tail_tag = "%title%" if tail_var >= head_var and tail_var > 0 else ".*"
    head_pattern = head_pat.format(TAG=head_tag)
    tail_pattern = tail_pat.format(TAG=tail_tag)
    pattern = f"{head_pattern}{EP}{tail_pattern}"
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
