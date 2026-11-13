import random
import unittest

from cheat.core.typo_simulator import simulate_typos


class TypoSimulatorTests(unittest.TestCase):
    def test_zero_probability_preserves_text_without_corrections(self):
        result = simulate_typos("Hello, world!", 0, rng=random.Random(1))
        self.assertEqual(result.initial_text, "Hello, world!")
        self.assertEqual(result.corrected_text, "Hello, world!")
        self.assertEqual(result.corrections, ())

    def test_full_probability_corrects_only_mistaken_positions(self):
        original = "cat sat"
        result = simulate_typos(original, 1, correction_delay_words=1, rng=random.Random(5))
        self.assertNotEqual(result.initial_text, original)
        self.assertEqual(result.corrected_text, original)
        self.assertTrue(all(c.corrected_after_word > c.word_number for c in result.corrections))
        self.assertTrue(all(c.mistaken.lower() in "qwertyuiopasdfghjklzxcvbnm" for c in result.corrections))
        for correction in result.corrections:
            self.assertEqual(result.corrected_text[correction.character_index], correction.intended)

    def test_i_uses_adjacent_qwerty_keys(self):
        result = simulate_typos("i", 1, rng=random.Random(2))
        correction = result.corrections[0]
        self.assertIn(correction.mistaken.lower(), {"u", "o", "j", "k"})

    def test_invalid_probability_and_delay_are_rejected(self):
        with self.assertRaises(ValueError):
            simulate_typos("text", 1.1)
        with self.assertRaises(ValueError):
            simulate_typos("text", 0.2, 0)


if __name__ == "__main__":
    unittest.main()
