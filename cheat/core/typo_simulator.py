"""Preview-only typo simulation; this module never sends keyboard input.

The simulator substitutes nearby QWERTY letters at a configurable probability,
then corrects those individual positions after a later word boundary. It always
edits only the typo's character index, leaving all subsequent text intact.
"""

from __future__ import annotations

import random
from dataclasses import dataclass


_ROWS = ("qwertyuiop", "asdfghjkl", "zxcvbnm")
_KEY_POSITIONS = {
    char: (row_index, column + (0.25 if row_index == 1 else 0.65 if row_index == 2 else 0))
    for row_index, row in enumerate(_ROWS)
    for column, char in enumerate(row)
}
_NEIGHBORS = {
    char: tuple(
        other
        for other, (other_row, other_column) in _KEY_POSITIONS.items()
        if other != char
        and abs(other_row - row) <= 1
        and abs(other_column - column) <= 1.15
    )
    for char, (row, column) in _KEY_POSITIONS.items()
}


@dataclass(frozen=True)
class Correction:
    """One simulated typo and its later, position-specific correction."""

    character_index: int
    word_number: int
    corrected_after_word: int
    intended: str
    mistaken: str


@dataclass(frozen=True)
class SimulationEvent:
    """A visible preview state at a simulated word boundary."""

    word_number: int
    description: str
    text: str


@dataclass(frozen=True)
class SimulationResult:
    initial_text: str
    corrected_text: str
    corrections: tuple[Correction, ...]
    timeline: tuple[SimulationEvent, ...]


def _word_numbers(text: str) -> list[int]:
    """Map each character offset to its 1-based word number (0 for whitespace)."""
    numbers = [0] * len(text)
    word_number = 0
    in_word = False
    for index, char in enumerate(text):
        if char.isspace():
            in_word = False
        else:
            if not in_word:
                word_number += 1
                in_word = True
            numbers[index] = word_number
    return numbers


def simulate_typos(
    text: str,
    probability: float = 0.20,
    correction_delay_words: int = 3,
    *,
    rng: random.Random | None = None,
) -> SimulationResult:
    """Simulate nearby-key mistakes and later local corrections in a preview.

    ``probability`` is a per-letter chance in [0, 1]. Corrections are made by
    replacing the exact mistaken character, not by deleting/retyping the suffix.
    Provide a seeded ``random.Random`` for repeatable tests and demonstrations.
    """
    if not 0 <= probability <= 1:
        raise ValueError("probability must be between 0 and 1")
    if correction_delay_words < 1:
        raise ValueError("correction_delay_words must be at least 1")

    rng = rng or random.Random()
    word_numbers = _word_numbers(text)
    initial = list(text)
    corrections: list[Correction] = []

    for index, char in enumerate(text):
        if not char.isalpha():
            continue
        lower = char.lower()
        neighbors = _NEIGHBORS.get(lower, ())
        if neighbors and rng.random() < probability:
            replacement = rng.choice(neighbors)
            if char.isupper():
                replacement = replacement.upper()
            initial[index] = replacement
            word_number = word_numbers[index]
            corrections.append(Correction(
                character_index=index,
                word_number=word_number,
                corrected_after_word=word_number + correction_delay_words,
                intended=char,
                mistaken=replacement,
            ))

    initial_text = "".join(initial)
    corrected = list(initial)
    pending_by_word: dict[int, list[Correction]] = {}
    for correction in corrections:
        pending_by_word.setdefault(correction.corrected_after_word, []).append(correction)

    timeline: list[SimulationEvent] = []
    total_words = max(word_numbers, default=0)
    for word_number in range(1, total_words + 1):
        timeline.append(SimulationEvent(
            word_number=word_number,
            description=f"Typed through word {word_number}; any uncorrected simulated mistakes remain visible.",
            text="".join(corrected),
        ))
        due = pending_by_word.get(word_number, ())
        for correction in due:
            corrected[correction.character_index] = correction.intended
            timeline.append(SimulationEvent(
                word_number=word_number,
                description=(
                    f"After word {word_number}, corrected character at position "
                    f"{correction.character_index + 1} ({correction.mistaken!r} → {correction.intended!r}); "
                    "the following text was preserved."
                ),
                text="".join(corrected),
            ))

    # Corrections due beyond the end of short input are still shown as later
    # preview events, rather than silently dropping the simulated repair.
    for due_word in sorted(key for key in pending_by_word if key > total_words):
        for correction in pending_by_word[due_word]:
            corrected[correction.character_index] = correction.intended
            timeline.append(SimulationEvent(
                word_number=due_word,
                description=(
                    f"After word {due_word}, corrected character at position "
                    f"{correction.character_index + 1} ({correction.mistaken!r} → {correction.intended!r}); "
                    "the following text was preserved."
                ),
                text="".join(corrected),
            ))

    return SimulationResult(
        initial_text=initial_text,
        corrected_text="".join(corrected),
        corrections=tuple(corrections),
        timeline=tuple(timeline),
    )
