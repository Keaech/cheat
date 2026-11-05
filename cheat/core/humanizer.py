import random
import time

class Humanizer:
    """Algorithms to make robotic typing feel human."""

    @staticmethod
    def get_delay(base_delay: float) -> float:
        # Add natural jitter (70% to 130% of base delay)
        jitter = random.uniform(0.7, 1.3)
        delay = base_delay * jitter

        # Simulate "thinking" pauses (small chance of a longer break)
        if random.random() < 0.03:
            delay += random.uniform(0.4, 1.2)

        return delay

    @staticmethod
    def should_make_mistake(char: str, probability: float) -> bool:
        # Only make mistakes on alphabetic characters
        return char.isalpha() and random.random() < probability

    @staticmethod
    def get_random_char() -> str:
        return random.choice("qwertyuiopasdfghjklzxcvbnm")
