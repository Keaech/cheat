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


if __name__ == "__main__":
    unittest.main()
