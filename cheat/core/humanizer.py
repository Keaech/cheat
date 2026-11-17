"""Predictable, user-configurable pacing for transparent text entry.

Pauses are deterministic and visible in the settings; this module does not add
random timing or simulated typing errors to disguise automation.
"""

import math


class Humanizer:
    """Backward-compatible name for the app's pacing helper."""

    @staticmethod
    def get_delay(base_delay: float, char: str | None = None) -> float:
        """Return a validated, fixed inter-character delay in seconds."""
        del char  # Kept for compatibility; character type does not change speed.
        if not math.isfinite(base_delay) or base_delay < 0:
            raise ValueError("base_delay must be a finite, non-negative number")
        return base_delay

    @staticmethod
    def get_pause_after(
        text: str,
        index: int,
        sentence_pause: float,
        paragraph_pause: float,
    ) -> float:
        """Return an optional explicit pause after a sentence or blank line.

        Sentence punctuation is recognized when followed by whitespace or the
        end of the text, allowing closing quotes/brackets. Decimal points and
        punctuation inside a word do not trigger a pause. A paragraph pause is
        applied after the second newline in a consecutive newline sequence.
        """
        if not 0 <= index < len(text):
            raise IndexError("index is outside the text")
        if not math.isfinite(sentence_pause) or sentence_pause < 0:
            raise ValueError("sentence_pause must be finite and non-negative")
        if not math.isfinite(paragraph_pause) or paragraph_pause < 0:
            raise ValueError("paragraph_pause must be finite and non-negative")

        char = text[index]
        if char == "\n" and index > 0 and text[index - 1] == "\n":
            return paragraph_pause
        if char not in ".!?":
            return 0.0

        cursor = index + 1
        while cursor < len(text) and text[cursor] in '\"\'”’)]}':
            cursor += 1
        if cursor == len(text) or text[cursor].isspace():
            return sentence_pause
        return 0.0
