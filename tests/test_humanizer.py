import unittest

from cheat.core.humanizer import Humanizer


class HumanizerTests(unittest.TestCase):
    def test_delay_is_fixed_and_independent_of_character(self):
        self.assertEqual(Humanizer.get_delay(0.2, "a"), 0.2)
        self.assertEqual(Humanizer.get_delay(0.2, "!"), 0.2)

    def test_zero_delay_is_valid(self):
        self.assertEqual(Humanizer.get_delay(0), 0)

    def test_negative_or_non_finite_delay_is_rejected(self):
        for delay in (-0.1, float("inf"), float("nan")):
            with self.subTest(delay=delay):
                with self.assertRaises(ValueError):
                    Humanizer.get_delay(delay)

    def test_sentence_pause_after_terminal_punctuation(self):
        text = 'Done! "Next sentence.'
        self.assertEqual(Humanizer.get_pause_after(text, 3, 0.8, 1.5), 0.8)
        self.assertEqual(Humanizer.get_pause_after(text, len(text) - 1, 0.8, 1.5), 0.8)

    def test_no_sentence_pause_inside_decimal_or_word(self):
        text = "Value 3.14 is pi-ish"
        self.assertEqual(Humanizer.get_pause_after(text, 7, 0.8, 1.5), 0.0)

    def test_paragraph_pause_after_blank_line(self):
        text = "First line.\n\nSecond paragraph."
        index = text.index("\n\n") + 1
        self.assertEqual(Humanizer.get_pause_after(text, index, 0.8, 1.5), 1.5)

    def test_invalid_pause_values_are_rejected(self):
        with self.assertRaises(ValueError):
            Humanizer.get_pause_after("Hi.", 2, -1, 1)
        with self.assertRaises(ValueError):
            Humanizer.get_pause_after("Hi.", 2, 1, float("inf"))


if __name__ == "__main__":
    unittest.main()
