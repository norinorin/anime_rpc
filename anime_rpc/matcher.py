import difflib
import logging
import re
from os.path import commonprefix as os_commonprefix
from pathlib import Path

EP = "%ep%"
MIN_N_SEQUENCE = 2
_LOGGER = logging.getLogger("automatic_matcher")
SPACE_NORMALIZER = re.compile(r"\\\s+")


def exclude_anomalies(filenames: list[str], threshold: float = 0.6) -> list[str]:
    if len(filenames) < MIN_N_SEQUENCE:
        return filenames

    scores: list[tuple[str, float]] = []
    seq_matcher = difflib.SequenceMatcher(None)
    n_comparisons = len(filenames) - 1

    for i, f in enumerate(filenames):
        total = 0
        for j, g in enumerate(filenames):
            if i != j:
                seq_matcher.set_seqs(f, g)
                s = seq_matcher.ratio()
                total += s
        avg = total / n_comparisons
        scores.append((f, avg))

    return [f for f, score in scores if score >= threshold]


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


def generate_regex_pattern(filedir: str) -> str | None:
    dir_path = Path(filedir)
    filenames = [f.name for f in dir_path.iterdir() if f.is_file()]
    filenames = exclude_anomalies(filenames)
    if len(filenames) < MIN_N_SEQUENCE:
        return None

    patterns: list[str] = []
    prefix = common_prefix(filenames)
    suffix = common_prefix(filenames, reverse=True)

    _LOGGER.debug("Detected common prefix: %s", prefix)
    _LOGGER.debug("Detected common suffix: %s", suffix)

    patterns = []
    for name in filenames:
        middle = name[len(prefix) : len(name) - len(suffix) if suffix else None]
        match = re.search(r"\d+", middle)
        _LOGGER.debug("Middle: %s", middle)
        if not match:
            # can't find ep number, might be rpc.config, ignore
            continue
        before = prefix + middle[: match.start()]
        after = middle[match.end() :] + suffix
        patterns.append(rf"{before}{EP}{after}")

    if len(patterns) < MIN_N_SEQUENCE:
        return None

    _LOGGER.debug("Possible patterns: %s", patterns)
    pattern_prefix = common_prefix(patterns)
    pattern_suffix = common_prefix(patterns, reverse=True)
    generated_pattern = pattern_prefix if EP in pattern_prefix else pattern_suffix
    generated_pattern = re.escape(generated_pattern)
    generated_pattern = SPACE_NORMALIZER.sub(r"\\s+", generated_pattern)
    _LOGGER.info("Generated pattern: %s", generated_pattern)
    _LOGGER.info("Appending generated pattern to rpc.config...")

    with (dir_path / "rpc.config").open("a") as f:
        f.write(f"\n# Automatically generated pattern\nmatch={generated_pattern}\n")

    return generated_pattern
