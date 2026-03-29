import unittest

from broadcast.pipeline import _fit_script_to_duration


class PipelineTests(unittest.TestCase):
    def test_fit_script_to_duration_leaves_short_copy_unchanged(self) -> None:
        script = "Bitcoin is firm. Traders are watching rates. Ethereum is holding support."
        self.assertEqual(_fit_script_to_duration(script, 60), script)

    def test_fit_script_to_duration_trims_to_target_budget(self) -> None:
        sentence = "Bitcoin is firm and traders are watching rates for the next catalyst."
        script = " ".join(sentence for _ in range(20))

        fitted = _fit_script_to_duration(script, 30)

        self.assertLessEqual(len(fitted.split()), 72)
        self.assertTrue(fitted.endswith((".", "!", "?", "...")))


if __name__ == "__main__":
    unittest.main()
