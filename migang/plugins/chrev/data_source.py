charmap = {
    "a": "ɐ",
    "b": "q",
    "c": "ɔ",
    "d": "p",
    "e": "ǝ",
    "f": "ɟ",
    "g": "ƃ",
    "h": "ɥ",
    "i": "ᴉ",
    "j": "ɾ",
    "k": "ʞ",
    "l": "l",
    "m": "ɯ",
    "n": "u",
    "o": "o",
    "p": "d",
    "q": "b",
    "r": "ɹ",
    "s": "s",
    "t": "ʇ",
    "u": "n",
    "v": "ʌ",
    "w": "ʍ",
    "x": "x",
    "y": "ʎ",
    "z": "z",
    "A": "∀",
    "B": "ᗺ",
    "C": "Ɔ",
    "D": "ᗡ",
    "E": "Ǝ",
    "F": "Ⅎ",
    "G": "⅁",
    "H": "H",
    "I": "I",
    "J": "ſ",
    "K": "ʞ",
    "L": "˥",
    "M": "W",
    "N": "N",
    "O": "O",
    "P": "Ԁ",
    "Q": "Ò",
    "R": "ᴚ",
    "S": "S",
    "T": "⏊",
    "U": "∩",
    "V": "Λ",
    "W": "M",
    "X": "X",
    "Y": "⅄",
    "Z": "Z",
    "ɐ": "a",
    "ɔ": "c",
    "ǝ": "e",
    "ɟ": "f",
    "ƃ": "g",
    "ɥ": "h",
    "ᴉ": "i",
    "ɾ": "j",
    "ʞ": "k",
    "ɯ": "m",
    "ɹ": "r",
    "ʇ": "t",
    "ʌ": "v",
    "ʍ": "w",
    "ʎ": "y",
    "∀": "A",
    "ᗺ": "B",
    "Ɔ": "C",
    "ᗡ": "D",
    "Ǝ": "E",
    "Ⅎ": "F",
    "⅁": "G",
    "ſ": "J",
    "˥": "L",
    "Ԁ": "P",
    "Ò": "Q",
    "ᴚ": "R",
    "⏊": "T",
    "∩": "U",
    "Λ": "V",
    "⅄": "Y",
}


def _rev(ch: str) -> str:
    if (r := charmap.get(ch)) is not None:
        return r
    return ch


def rev_word(word: str) -> str:
    return "".join(map(_rev, word))
