"""Deterministic pacing helpers for transparent, user-directed typing.

This intentionally does not imitate human behavior, add typos, or vary timing to
conceal automation. The caller chooses a fixed speed and can stop typing at any
time.
"""

import math


class Humanizer:
    """Backward-compatible name for the app's predictable pacing helper."""

    @staticmethod
    def get_delay(base_delay: float, char: str | None = None) -> float:
        """Return a validated, fixed inter-character delay in seconds.

        ``char`` is accepted for compatibility with the earlier UI but does not
        affect timing. Character-dependent timing would make the automation less
        predictable and could suggest an attempt to mimic a person.
        """
        del char
        if not math.isfinite(base_delay) or base_delay < 0:
            raise ValueError("base_delay must be a finite, non-negative number")
        return base_delay
