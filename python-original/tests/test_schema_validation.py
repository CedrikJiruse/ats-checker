import json
import os
import unittest
from tempfile import TemporaryDirectory

from schema_validation import (
    ValidationResult,
    format_validation_errors,
    load_schema,
    schema_validation_available,
    validate_json,
    validate_json_str,
)


class TestSchemaValidationHelpers(unittest.TestCase):
    def test_schema_validation_available_returns_bool(self):
        available = schema_validation_available()
        self.assertIsInstance(available, bool)

    def test_load_schema_raises_on_empty_path(self):
        with self.assertRaises(ValueError):
            load_schema("")

    def test_load_schema_raises_on_missing_file(self):
        with TemporaryDirectory() as tmp:
            missing = os.path.join(tmp, "missing_schema.json")
            with self.assertRaises(FileNotFoundError):
                load_schema(missing)

    def test_load_schema_raises_on_invalid_json(self):
        with TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "bad_schema.json")
            with open(path, "w", encoding="utf-8") as f:
                f.write("{ not valid json")
            with self.assertRaises(ValueError):
                load_schema(path)

    def test_load_schema_raises_when_schema_not_object(self):
        with TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "schema.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(["not", "an", "object"], f)
            with self.assertRaises(ValueError):
                load_schema(path)

    def test_validate_json_str_rejects_empty_string(self):
        res = validate_json_str("", schema={"type": "object"}, instance_name="resume")
        self.assertIsInstance(res, ValidationResult)
        self.assertFalse(res.ok)
        self.assertEqual(res.summary, "empty_json")
        self.assertTrue(any("empty" in e.lower() for e in res.errors))

    def test_validate_json_str_rejects_invalid_json(self):
        res = validate_json_str(
            "{oops", schema={"type": "object"}, instance_name="resume"
        )
        self.assertIsInstance(res, ValidationResult)
        self.assertFalse(res.ok)
        self.assertEqual(res.summary, "invalid_json")
        self.assertTrue(any("invalid json" in e.lower() for e in res.errors))

    def test_validate_json_returns_unavailable_result_when_jsonschema_missing(self):
        # We can't assume jsonschema is installed in every environment.
        # When unavailable, the helper should return a deterministic "unavailable" result.
        if schema_validation_available():
            self.skipTest("jsonschema is available; skipping unavailable-path test")
        res = validate_json(
            instance={}, schema={"type": "object"}, instance_name="resume"
        )
        self.assertFalse(res.ok)
        self.assertEqual(res.summary, "schema_validation_unavailable")
        self.assertTrue(
            any(
                "missing" in e.lower() or "unavailable" in e.lower() for e in res.errors
            )
        )

    def test_validate_json_rejects_non_dict_schema_type(self):
        # This should fail even if jsonschema is unavailable (local type check).
        res = validate_json(instance={}, schema=[], instance_name="resume")  # type: ignore[arg-type]
        self.assertFalse(res.ok)
        self.assertEqual(res.summary, "invalid_schema_type")

    def test_format_validation_errors_produces_string(self):
        # Even with non-jsonschema errors, formatting should return a string
        formatted = format_validation_errors(
            [ValueError("boom")], instance_name="resume", max_errors=5
        )
        self.assertIsInstance(formatted, str)
        self.assertIn("boom", formatted.lower())


class TestResumeSchemaFileLoading(unittest.TestCase):
    def test_can_load_repo_resume_schema_file(self):
        # This path is expected to exist in the repo
        schema_path = os.path.join("config", "resume_schema.json")
        schema = load_schema(schema_path)
        self.assertIsInstance(schema, dict)
        # basic shape checks
        self.assertEqual(schema.get("type"), "object")
        self.assertIn("properties", schema)
        props = schema.get("properties", {})
        self.assertIsInstance(props, dict)
        self.assertIn("personal_info", props)
        self.assertIn("_scoring", props)

    def test_schema_validation_on_minimal_valid_resume_object(self):
        if not schema_validation_available():
            self.skipTest("jsonschema not installed; validation runtime not available")

        schema_path = os.path.join("config", "resume_schema.json")
        schema = load_schema(schema_path)

        # Required fields in the schema: personal_info, experience, education, skills, projects
        resume = {
            "personal_info": {"name": "Test User", "email": "test@example.com"},
            "summary": "A short summary",
            "experience": [],
            "education": [],
            "skills": [],
            "projects": [],
            "_meta": {"timestamp": "20250101_120000"},
            "_scoring": {
                "iteration_score": 75.0,
                "mode": "resume_only",
                "resume_report": {"total": 75.0, "kind": "resume"},
            },
        }

        res = validate_json(resume, schema, instance_name="resume")
        self.assertTrue(res.ok, msg=res.detail or "\n".join(res.errors))

    def test_schema_validation_fails_when_required_field_missing(self):
        if not schema_validation_available():
            self.skipTest("jsonschema not installed; validation runtime not available")

        schema_path = os.path.join("config", "resume_schema.json")
        schema = load_schema(schema_path)

        resume_missing = {
            "personal_info": {"name": "Test User", "email": "test@example.com"},
            # missing required keys: experience, education, skills, projects
        }

        res = validate_json(resume_missing, schema, instance_name="resume")
        self.assertFalse(res.ok)
        self.assertEqual(res.summary, "schema_validation_failed")
        # error output should mention at least one of the missing fields
        combined = " ".join(res.errors).lower() + " " + (res.detail or "").lower()
        self.assertTrue(
            any(
                k in combined for k in ["experience", "education", "skills", "projects"]
            ),
            msg=res.detail or "\n".join(res.errors),
        )


if __name__ == "__main__":
    unittest.main()
