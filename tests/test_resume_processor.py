import unittest
from unittest.mock import ANY, MagicMock, call, patch

import resume_processor
from resume_processor import ResumeProcessor


class TestResumeProcessor(unittest.TestCase):
    def _make_processor_with_mocks(self, *, num_versions_per_job=1):
        """
        Creates a ResumeProcessor with all integration points mocked at construction time,
        returning (processor, mocks_dict).
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
            num_versions_per_job=num_versions_per_job,
            job_description_folder="job_descriptions",
            tesseract_cmd=None,
        )

        return processor, {
            "state_manager": state_manager_instance,
            "input_handler": input_handler_instance,
            "gemini": gemini_instance,
            "output_generator": output_gen_instance,
        }

    def test_process_resumes_no_new_resumes_returns_early(self):
        processor, m = self._make_processor_with_mocks(num_versions_per_job=2)
        m["input_handler"].get_resumes_to_process.return_value = []

        processor.process_resumes()

        m["input_handler"].get_resumes_to_process.assert_called_once_with("input")
        m["gemini"].enhance_resume.assert_not_called()
        m["output_generator"].generate_structured_output.assert_not_called()
        m["output_generator"].generate_text_output.assert_not_called()
        m["state_manager"].update_resume_state.assert_not_called()

    def test_process_resumes_generic_generates_multiple_versions_and_updates_state_once(
        self,
    ):
        processor, m = self._make_processor_with_mocks(num_versions_per_job=2)

        resume = {
            "filepath": r"C:\resumes\alice.txt",
            "content": "Alice Resume Content",
            "hash": "hash-123",
        }
        m["input_handler"].get_resumes_to_process.return_value = [resume]

        m["gemini"].enhance_resume.side_effect = [
            '{"version": 1}',
            '{"version": 2}',
        ]
        m["output_generator"].generate_structured_output.side_effect = [
            r"C:\out\alice_generic_enhanced_v1.toml",
            r"C:\out\alice_generic_enhanced_v2.toml",
        ]
        m["output_generator"].generate_text_output.side_effect = [
            r"C:\out\alice_generic_enhanced_v1.txt",
            r"C:\out\alice_generic_enhanced_v2.txt",
        ]

        processor.process_resumes()

        # 2 versions => enhance called twice with no job description content
        self.assertEqual(m["gemini"].enhance_resume.call_count, 2)
        m["gemini"].enhance_resume.assert_has_calls(
            [
                call("Alice Resume Content", job_description=None),
                call("Alice Resume Content", job_description=None),
            ],
            any_order=False,
        )

        # Generators called twice each with correct job title token
        self.assertEqual(m["output_generator"].generate_structured_output.call_count, 2)
        self.assertEqual(m["output_generator"].generate_text_output.call_count, 2)

        # The processor enriches the JSON payload with scoring metadata before writing,
        # so we only assert the non-payload arguments here.
        m["output_generator"].generate_structured_output.assert_has_calls(
            [
                call(ANY, r"C:\resumes\alice.txt", "generic"),
                call(ANY, r"C:\resumes\alice.txt", "generic"),
            ],
            any_order=False,
        )
        # Payload is enriched with scoring metadata; only validate non-payload args.
        m["output_generator"].generate_text_output.assert_has_calls(
            [
                call(ANY, r"C:\resumes\alice.txt", "generic"),
                call(ANY, r"C:\resumes\alice.txt", "generic"),
            ],
            any_order=False,
        )

        # State updated once with the last structured output path from the loop
        m["state_manager"].update_resume_state.assert_called_once_with(
            "hash-123",
            r"C:\out\alice_generic_enhanced_v2.toml",
        )

    def test_process_resumes_with_job_description_found_passes_content_and_sanitizes_title(
        self,
    ):
        processor, m = self._make_processor_with_mocks(num_versions_per_job=1)

        resume = {
            "filepath": r"C:\resumes\bob.md",
            "content": "Bob Resume Content",
            "hash": "hash-456",
        }
        m["input_handler"].get_resumes_to_process.return_value = [resume]
        m["input_handler"].get_job_descriptions.return_value = {
            "software_engineer.txt": "JD CONTENT HERE"
        }

        m["gemini"].enhance_resume.return_value = '{"ok": true}'
        m[
            "output_generator"
        ].generate_structured_output.return_value = (
            r"C:\out\bob_software_engineer_enhanced.toml"
        )
        m[
            "output_generator"
        ].generate_text_output.return_value = (
            r"C:\out\bob_software_engineer_enhanced.txt"
        )

        processor.process_resumes(job_description_name="software_engineer.txt")

        m["input_handler"].get_job_descriptions.assert_called_once_with()
        m["gemini"].enhance_resume.assert_called_once_with(
            "Bob Resume Content",
            job_description="JD CONTENT HERE",
        )

        # Payload is enriched with scoring metadata; only validate non-payload args.
        m["output_generator"].generate_structured_output.assert_called_once_with(
            ANY,
            r"C:\resumes\bob.md",
            "software_engineer",
        )
        # Payload is enriched with scoring metadata; only validate non-payload args.
        m["output_generator"].generate_text_output.assert_called_once_with(
            ANY,
            r"C:\resumes\bob.md",
            "software_engineer",
        )
        m["state_manager"].update_resume_state.assert_called_once_with(
            "hash-456",
            r"C:\out\bob_software_engineer_enhanced.toml",
        )

    def test_process_resumes_with_job_description_missing_still_uses_filename_token_but_passes_none_content(
        self,
    ):
        processor, m = self._make_processor_with_mocks(num_versions_per_job=1)

        resume = {
            "filepath": r"C:\resumes\carol.txt",
            "content": "Carol Resume Content",
            "hash": "hash-789",
        }
        m["input_handler"].get_resumes_to_process.return_value = [resume]
        m["input_handler"].get_job_descriptions.return_value = {}  # not found

        m["gemini"].enhance_resume.return_value = '{"ok": true}'
        m[
            "output_generator"
        ].generate_structured_output.return_value = (
            r"C:\out\carol_software_engineer_enhanced.toml"
        )
        m[
            "output_generator"
        ].generate_text_output.return_value = (
            r"C:\out\carol_software_engineer_enhanced.txt"
        )

        processor.process_resumes(job_description_name="software_engineer.txt")

        m["gemini"].enhance_resume.assert_called_once_with(
            "Carol Resume Content",
            job_description=None,
        )
        # Payload is enriched with scoring metadata; only validate non-payload args.
        m["output_generator"].generate_structured_output.assert_called_once_with(
            ANY,
            r"C:\resumes\carol.txt",
            "software_engineer",
        )
        m["state_manager"].update_resume_state.assert_called_once_with(
            "hash-789",
            r"C:\out\carol_software_engineer_enhanced.toml",
        )

    def test_process_resumes_exception_during_enhancement_does_not_update_state(self):
        processor, m = self._make_processor_with_mocks(num_versions_per_job=2)

        resume = {
            "filepath": r"C:\resumes\dave.txt",
            "content": "Dave Resume Content",
            "hash": "hash-999",
        }
        m["input_handler"].get_resumes_to_process.return_value = [resume]

        m["gemini"].enhance_resume.side_effect = Exception("API down")

        processor.process_resumes()

        m["gemini"].enhance_resume.assert_called_once()
        m["output_generator"].generate_structured_output.assert_not_called()
        m["output_generator"].generate_text_output.assert_not_called()
        m["state_manager"].update_resume_state.assert_not_called()


if __name__ == "__main__":
    unittest.main()
