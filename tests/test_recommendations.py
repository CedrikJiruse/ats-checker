import unittest

from recommendations import (
    generate_recommendations,
    generate_recommendations_detailed,
)


class TestRecommendations(unittest.TestCase):
    def test_returns_warning_when_no_scoring_payload(self):
        recs = generate_recommendations(scoring_payload=None, max_items=5)
        self.assertTrue(len(recs) >= 1)
        self.assertIn("No scoring data found", recs[0])

    def test_accepts_resume_object_with_scoring(self):
        resume_obj = {
            "personal_info": {"name": "User", "email": "u@example.com"},
            "_scoring": {
                "iteration_score": 50.0,
                "mode": "resume_only",
                "resume_report": {
                    "total": 50.0,
                    "categories": [
                        {"name": "completeness", "score": 40.0, "weight": 0.3},
                        {"name": "impact", "score": 30.0, "weight": 0.2},
                    ],
                },
            },
        }
        recs = generate_recommendations(scoring_payload=resume_obj, max_items=10)
        self.assertTrue(any("resume quality score is low" in r.lower() for r in recs))
        self.assertTrue(any("completeness" in r.lower() for r in recs))
        self.assertTrue(any("impact" in r.lower() for r in recs))

    def test_accepts_score_details_shape(self):
        score_details = {
            "mode": "resume_plus_match",
            "resume_report": {
                "total": 55.0,
                "categories": [
                    {"name": "skills_quality", "score": 40.0, "weight": 0.2},
                ],
            },
            "match_report": {
                "total": 45.0,
                "categories": [
                    {
                        "name": "keyword_overlap",
                        "score": 25.0,
                        "weight": 0.45,
                        "details": {
                            "sample_missing": ["python", "kubernetes", "aws"],
                            "sample_overlap": ["docker"],
                        },
                    },
                    {"name": "skills_overlap", "score": 20.0, "weight": 0.35},
                    {"name": "role_alignment", "score": 25.0, "weight": 0.2},
                ],
            },
            "combined": {"resume_total": 55.0, "match_total": 45.0},
        }
        recs = generate_recommendations(scoring_payload=score_details, max_items=10)
        # Should prefer match-related guidance and mention keywords
        self.assertTrue(any("match to the job description" in r.lower() for r in recs))
        self.assertTrue(any("keyword" in r.lower() for r in recs))
        self.assertTrue(any("python" in r.lower() for r in recs))

    def test_missing_keywords_recommendation_is_deduped(self):
        # Provide duplicate missing keywords chunks via repeated category details
        score_details = {
            "mode": "resume_plus_match",
            "match_report": {
                "total": 10.0,
                "categories": [
                    {
                        "name": "keyword_overlap",
                        "score": 10.0,
                        "weight": 0.45,
                        "details": {"sample_missing": ["python", "python", "aws"]},
                    }
                ],
            },
        }
        recs = generate_recommendations(scoring_payload=score_details, max_items=10)
        # Only one missing-keywords recommendation should appear
        missing_recs = [r for r in recs if "job-relevant keywords" in r.lower()]
        self.assertLessEqual(len(missing_recs), 1)
        if missing_recs:
            self.assertIn("python", missing_recs[0].lower())
            self.assertIn("aws", missing_recs[0].lower())

    def test_max_items_limits_output(self):
        score_details = {
            "mode": "resume_plus_match",
            "resume_report": {
                "total": 10.0,
                "categories": [
                    {"name": "completeness", "score": 10.0, "weight": 0.3},
                    {"name": "skills_quality", "score": 10.0, "weight": 0.2},
                    {"name": "experience_quality", "score": 10.0, "weight": 0.3},
                    {"name": "impact", "score": 10.0, "weight": 0.2},
                ],
            },
            "match_report": {
                "total": 10.0,
                "categories": [
                    {"name": "keyword_overlap", "score": 10.0, "weight": 0.45},
                    {"name": "skills_overlap", "score": 10.0, "weight": 0.35},
                    {"name": "role_alignment", "score": 10.0, "weight": 0.2},
                ],
            },
        }
        recs = generate_recommendations(scoring_payload=score_details, max_items=3)
        self.assertEqual(len(recs), 3)

    def test_detailed_recommendations_include_severity(self):
        score_details = {
            "mode": "resume_only",
            "resume_report": {
                "total": 20.0,
                "categories": [{"name": "impact", "score": 10.0, "weight": 0.2}],
            },
        }
        detailed = generate_recommendations_detailed(
            scoring_payload=score_details, max_items=5
        )
        self.assertTrue(len(detailed) >= 1)
        # Ensure structured output with severity exists
        self.assertTrue(hasattr(detailed[0], "severity"))
        self.assertIn(detailed[0].severity, ("info", "warn", "high"))

    def test_unknown_category_generates_generic_message(self):
        score_details = {
            "mode": "resume_only",
            "resume_report": {
                "total": 50.0,
                "categories": [{"name": "some_new_category", "score": 10.0}],
            },
        }
        recs = generate_recommendations(scoring_payload=score_details, max_items=10)
        self.assertTrue(any("some_new_category" in r for r in recs))

    def test_low_score_threshold_filters_categories(self):
        score_details = {
            "mode": "resume_only",
            "resume_report": {
                "total": 70.0,
                "categories": [{"name": "impact", "score": 65.0}],
            },
        }
        # Set threshold lower than score so category-specific rec shouldn't appear
        detailed = generate_recommendations_detailed(
            scoring_payload=score_details, max_items=10, low_score_threshold=60.0
        )
        msgs = [r.message.lower() for r in detailed]
        # Impact-specific recommendation triggers only if below threshold; should not be present
        self.assertFalse(any("increase impact" in m for m in msgs))

    def test_handles_non_dict_categories_gracefully(self):
        score_details = {
            "mode": "resume_plus_match",
            "resume_report": {"total": 50.0, "categories": ["bad", 123, None]},
            "match_report": {"total": 50.0, "categories": ["bad", 123, None]},
        }
        recs = generate_recommendations(scoring_payload=score_details, max_items=10)
        # Should still return at least a general guidance line without crashing
        self.assertTrue(len(recs) >= 1)

    def test_handles_payload_without_mode(self):
        score_details = {
            "resume_report": {
                "total": 10.0,
                "categories": [{"name": "impact", "score": 0}],
            }
        }
        recs = generate_recommendations(scoring_payload=score_details, max_items=10)
        # Should default to resume-oriented guidance
        self.assertTrue(any("resume clarity" in r.lower() for r in recs))


if __name__ == "__main__":
    unittest.main()
