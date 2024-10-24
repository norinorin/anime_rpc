# https://stackoverflow.com/questions/30069846/how-to-find-out-chinese-or-japanese-character-in-a-string-in-python
CJK_RANGES = [
    {"from": ord("\u3300"), "to": ord("\u33ff")},  # compatibility ideographs
    {"from": ord("\ufe30"), "to": ord("\ufe4f")},  # compatibility ideographs
    {"from": ord("\uf900"), "to": ord("\ufaff")},  # compatibility ideographs
    {"from": ord("\U0002F800"), "to": ord("\U0002fa1f")},  # compatibility ideographs
    {"from": ord("\u3040"), "to": ord("\u309f")},  # Japanese Hiragana
    {"from": ord("\u30a0"), "to": ord("\u30ff")},  # Japanese Katakana
    {"from": ord("\u2e80"), "to": ord("\u2eff")},  # cjk radicals supplement
    {"from": ord("\u4e00"), "to": ord("\u9fff")},
    {"from": ord("\u3400"), "to": ord("\u4dbf")},
    {"from": ord("\U00020000"), "to": ord("\U0002a6df")},
    {"from": ord("\U0002a700"), "to": ord("\U0002b73f")},
    {"from": ord("\U0002b740"), "to": ord("\U0002b81f")},
    {"from": ord("\U0002b820"), "to": ord("\U0002ceaf")},  # included as of Unicode 8.0
]


def _is_char_cjk(char: str) -> bool:
    return any([range["from"] <= ord(char) <= range["to"] for range in CJK_RANGES])


def _contains_cjk(text: str) -> bool:
    return any([_is_char_cjk(i) for i in text])


def _quote_cjk(text: str) -> str:
    if text.startswith(("「", "『")) or text.endswith(("」", "』")):
        return text

    return f"「{text}」"


def quote(text: str) -> str:
    if _contains_cjk(text):
        return _quote_cjk(text)

    if text.startswith('"') or text.endswith('"'):
        return text

    return f'"{text}"'
