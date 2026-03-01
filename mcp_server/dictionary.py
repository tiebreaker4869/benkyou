"""Dictionary lookup utilities backed by jamdict."""

from jamdict import Jamdict

_jam: Jamdict | None = None


def _get_jam() -> Jamdict:
    """Lazily initialize and return the Jamdict singleton."""
    global _jam
    if _jam is None:
        _jam = Jamdict()
    return _jam


def lookup_word(word: str) -> dict | None:
    """Lookup one word and return normalized dictionary fields."""
    result = _get_jam().lookup(word)
    if not result.entries:
        return None

    entry = result.entries[0]
    if entry.kana_forms:
        reading = entry.kana_forms[0].text
    elif entry.kanji_forms:
        reading = entry.kanji_forms[0].text
    else:
        reading = ""

    senses = entry.senses
    return {
        "reading": reading,
        "pos": [str(p) for p in senses[0].pos] if senses else [],
        "meanings": [str(g) for g in senses[0].gloss] if senses else [],
        "examples": [],
    }

