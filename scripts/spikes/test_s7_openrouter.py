"""Regression checks for S7 measurement, with hand-calculated expectations."""
import unittest

import s7_jev_parity as original


class MetricsTests(unittest.TestCase):
    def test_systemone_uses_probabilities_and_score_rounding(self):
        from s7_openrouter import systemone_prediction
        answers = original.jev_questions_for(original.TOPICS)
        answers = {key: {"type": "noul", "noul": .1} for key in answers}
        answers.update(sentiment={"choice": "negative", "probabilities": {"negative": .8}},
                       intent={"choice": "complaint", "probabilities": {"complaint": .7}},
                       severity={"score": 1.6, "probabilities": {"2": .6}})
        raw = systemone_prediction(answers)
        self.assertEqual(raw["severity"], "high")
        self.assertEqual(raw["choice_probabilities"], {"sentiment": .8, "intent": .7, "severity": .6})

    def test_calibration_checks_each_choice_split(self):
        from s7_openrouter import calibration
        truth = [original.RECORDS[0]]
        prediction = {**truth[0], "choice_probabilities": {"sentiment": .9, "intent": .8, "severity": .7}}
        gaps = calibration([prediction], truth)
        self.assertAlmostEqual(gaps["sentiment"], .1)
        self.assertAlmostEqual(gaps["intent"], .2)
        self.assertAlmostEqual(gaps["severity"], .3)

    def test_p95_keeps_slow_tail_for_sixteen_records(self):
        from s7_openrouter import percentile95
        self.assertEqual(percentile95(list(range(1, 17))), 16)

    def test_unknown_budget_cannot_pass(self):
        from s7_openrouter import verdict
        self.assertEqual(verdict([True, True, True, True, None]), "INCONCLUSIVE")
        self.assertEqual(verdict([True, False, True, True, None]), "FAIL")

    def test_multi_label_accuracy_and_precision_are_both_reported(self):
        from s7_openrouter import evaluate
        truth = [original.RECORDS[0]]
        prediction = {**truth[0], "emotions": ["satisfaction", "anger"]}
        metrics = evaluate([prediction], truth)
        self.assertEqual(metrics["emotion_exact_accuracy"], 0)
        self.assertAlmostEqual(metrics["emotion_precision"], .5)
        self.assertAlmostEqual(metrics["emotion_micro_f1"], 2 / 3)

    def test_threshold_filters_both_topics_and_emotions(self):
        from s7_openrouter import labels
        raw = {"topics": [{"id": "search.result", "probability": .55}],
               "emotions": [{"label": "anger", "probability": .55}],
               "sentiment": "negative", "intent": "complaint", "severity": "low"}
        self.assertEqual(labels(raw, .6)["topics"], [])
        self.assertEqual(labels(raw, .6)["emotions"], ["neutral"])
        self.assertEqual(labels(raw, .5)["emotions"], ["anger"])


if __name__ == "__main__":
    unittest.main()
