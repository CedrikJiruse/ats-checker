import unittest
from unittest.mock import MagicMock, patch

import resume_processor
from resume_processor import ResumeProcessor


class FakeScoreReport:
    def __init__(self, total: float, kind: str, categories=None):
        self.total = float(total)
        self._kind = kind
        self._categories = categories if categories is not None else []

    def as_dict(self):
        # Match the shape expected by scoring helpers in resume_processor
        return {
            "kind": self._kind,
            "total": float(self.total),
            "categories": list(self._categories),
            "meta": {},
        }


class TestResumeProcessorScoreCache(unittest.TestCase):
    def _make_processor(self, *, score_cache_enabled: bool):
        """
        Create a ResumeProcessor with all external dependencies mocked out so we can test
        _score_for_iteration in isolation.
        """
        state_manager_instance = MagicMock(name="StateManagerInstance")
        input_handler_instance = MagicMock(name="InputHandlerInstance")
        gemini_instance = MagicMock(name="GeminiAPIIntegratorInstance")
        output_gen_instance = MagicMock(name="OutputGeneratorInstance")

        patches = [
            patch.object(
                resume_processor, "StateManager", return_value=state_manager_instance
            ),
            patch.object(
                resume_processor, "InputHandler", return_value=input_handler_instance
            ),
            patch.object(
                resume_processor, "GeminiAPIIntegrator", return_value=gemini_instance
            ),
            patch.object(
                resume_processor, "OutputGenerator", return_value=output_gen_instance
            ),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

        processor = ResumeProcessor(
            input_folder="input",
            output_folder="output",
            model_name="gemini-pro",
            temperature=0.7,
            top_p=0.95,
            top_k=40,
            max_output_tokens=8192,
            num_versions_per_job=1,
            job_description_folder="job_descriptions",
            tesseract_cmd=None,
            score_cache_enabled=score_cache_enabled,
            max_concurrent_requests=1,
        )
        return processor

    @patch.object(resume_processor, "compute_iteration_score")
    @patch.object(resume_processor, "score_job")
    @patch.object(resume_processor, "score_match")
    @patch.object(resume_processor, "score_resume")
    def test_score_cache_hit_same_inputs(
        self,
        mock_score_resume,
        mock_score_match,
        mock_score_job,
        mock_compute_iteration_score,
    ):
        processor = self._make_processor(score_cache_enabled=True)

        resume_json = (
            '{"personal_info": {}, "summary": null, "experience": [], '
            '"education": [], "skills": [], "projects": []}'
        )
        job_description_content = (
            "We want a Python engineer. Requirements: Python, AWS."
        )

        mock_score_resume.return_value = FakeScoreReport(70.0, "resume")
        mock_score_match.return_value = FakeScoreReport(
            90.0,
            "match",
            categories=[
                {
                    "name": "keyword_overlap",
                    "score": 80.0,
                    "weight": 0.45,
                    "details": {
                        "sample_overlap": ["python"],
                        "sample_missing": ["aws"],
                    },
                }
            ],
        )
        mock_score_job.return_value = FakeScoreReport(55.0, "job")
        mock_compute_iteration_score.return_value = (
            82.5,
            {
                "resume_total": 70.0,
                "match_total": 90.0,
                "weights": {"resume": 0.5, "match": 0.5},
            },
        )

        out1 = processor._score_for_iteration(
            resume_json=resume_json,
            job_description_name="job.txt",
            job_description_content=job_description_content,
        )
        out2 = processor._score_for_iteration(
            resume_json=resume_json,
            job_description_name="job.txt",
            job_description_content=job_description_content,
        )

        # Verify cache hit prevents duplicate scoring calls
        self.assertEqual(mock_score_resume.call_count, 1)
        self.assertEqual(mock_score_match.call_count, 1)
        self.assertEqual(mock_score_job.call_count, 1)
        self.assertEqual(mock_compute_iteration_score.call_count, 1)

        self.assertEqual(out1, out2)
        self.assertEqual(len(processor._score_cache), 1)

    @patch.object(resume_processor, "compute_iteration_score")
    @patch.object(resume_processor, "score_job")
    @patch.object(resume_processor, "score_match")
    @patch.object(resume_processor, "score_resume")
    def test_score_cache_miss_when_job_description_changes(
        self,
        mock_score_resume,
        mock_score_match,
        mock_score_job,
        mock_compute_iteration_score,
    ):
        processor = self._make_processor(score_cache_enabled=True)

        resume_json = (
            '{"personal_info": {}, "summary": null, "experience": [], '
            '"education": [], "skills": [], "projects": []}'
        )
        jd1 = "JD one: Python required."
        jd2 = "JD two: Java required."

        mock_score_resume.return_value = FakeScoreReport(70.0, "resume")
        mock_score_match.return_value = FakeScoreReport(50.0, "match")
        mock_score_job.return_value = FakeScoreReport(10.0, "job")
        mock_compute_iteration_score.return_value = (
            60.0,
            {"resume_total": 70.0, "match_total": 50.0},
        )

        processor._score_for_iteration(
            resume_json=resume_json,
            job_description_name="job1.txt",
            job_description_content=jd1,
        )
        processor._score_for_iteration(
            resume_json=resume_json,
            job_description_name="job2.txt",
            job_description_content=jd2,
        )

        # Different JD content => different cache key => recompute
        self.assertEqual(mock_score_resume.call_count, 2)
        self.assertEqual(mock_score_match.call_count, 2)
        self.assertEqual(mock_score_job.call_count, 2)
        self.assertEqual(mock_compute_iteration_score.call_count, 2)
        self.assertEqual(len(processor._score_cache), 2)

    @patch.object(resume_processor, "compute_iteration_score")
    @patch.object(resume_processor, "score_job")
    @patch.object(resume_processor, "score_match")
    @patch.object(resume_processor, "score_resume")
    def test_score_cache_disabled_recomputes_every_time(
        self,
        mock_score_resume,
        mock_score_match,
        mock_score_job,
        mock_compute_iteration_score,
    ):
        processor = self._make_processor(score_cache_enabled=False)

        resume_json = (
            '{"personal_info": {}, "summary": null, "experience": [], '
            '"education": [], "skills": [], "projects": []}'
        )
        job_description_content = "JD: Python required."

        mock_score_resume.return_value = FakeScoreReport(70.0, "resume")
        mock_score_match.return_value = FakeScoreReport(90.0, "match")
        mock_score_job.return_value = FakeScoreReport(55.0, "job")
        mock_compute_iteration_score.return_value = (
            82.5,
            {"resume_total": 70.0, "match_total": 90.0},
        )

        processor._score_for_iteration(
            resume_json=resume_json,
            job_description_name="job.txt",
            job_description_content=job_description_content,
        )
        processor._score_for_iteration(
            resume_json=resume_json,
            job_description_name="job.txt",
            job_description_content=job_description_content,
        )

        self.assertEqual(mock_score_resume.call_count, 2)
        self.assertEqual(mock_score_match.call_count, 2)
        self.assertEqual(mock_score_job.call_count, 2)
        self.assertEqual(mock_compute_iteration_score.call_count, 2)
        self.assertEqual(len(processor._score_cache), 0)


if __name__ == "__main__":
    unittest.main()
