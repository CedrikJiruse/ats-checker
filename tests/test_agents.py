import unittest

from agents import AgentResponseError, ensure_json_object, strip_markdown_fences


class TestStripMarkdownFences(unittest.TestCase):
    def test_strip_plain_text_returns_trimmed(self):
        self.assertEqual(strip_markdown_fences("  hello  "), "hello")

    def test_strip_triple_backticks_without_language(self):
        text = '```\n{\n  "a": 1\n}\n```'
        self.assertEqual(strip_markdown_fences(text), '{\n  "a": 1\n}')

    def test_strip_triple_backticks_with_json_language(self):
        text = '```json\n{\n  "a": 1\n}\n```'
        self.assertEqual(strip_markdown_fences(text), '{\n  "a": 1\n}')

    def test_strip_triple_backticks_with_other_language(self):
        text = "```python\nprint('x')\n```"
        self.assertEqual(strip_markdown_fences(text), "print('x')")

    def test_strip_backticks_when_no_newline_falls_back(self):
        # No newline after fence -> fallback branch should still remove outer fences.
        text = '```{"a":1}```'
        self.assertEqual(strip_markdown_fences(text), '{"a":1}')

    def test_strip_preserves_internal_backticks(self):
        text = '```json\n{"a": "```inner```"}\n```'
        self.assertEqual(strip_markdown_fences(text), '{"a": "```inner```"}')

    def test_strip_non_string_returns_empty_string(self):
        self.assertEqual(strip_markdown_fences(None), "")
        self.assertEqual(strip_markdown_fences(123), "")


class TestEnsureJsonObject(unittest.TestCase):
    def test_ensure_json_object_parses_plain_json(self):
        obj = ensure_json_object('{"a": 1, "b": "x"}')
        self.assertEqual(obj, {"a": 1, "b": "x"})

    def test_ensure_json_object_parses_fenced_json(self):
        obj = ensure_json_object('```json\n{"a": 1}\n```')
        self.assertEqual(obj, {"a": 1})

    def test_ensure_json_object_parses_fenced_without_language(self):
        obj = ensure_json_object('```\n{"a": 1}\n```')
        self.assertEqual(obj, {"a": 1})

    def test_ensure_json_object_rejects_invalid_json(self):
        with self.assertRaises(AgentResponseError):
            ensure_json_object("{not valid json}")

    def test_ensure_json_object_rejects_non_object_root_array(self):
        with self.assertRaises(AgentResponseError):
            ensure_json_object("[1, 2, 3]")

    def test_ensure_json_object_rejects_non_object_root_scalar(self):
        with self.assertRaises(AgentResponseError):
            ensure_json_object('"just a string"')

    def test_ensure_json_object_rejects_empty(self):
        with self.assertRaises(AgentResponseError):
            ensure_json_object("")


if __name__ == "__main__":
    unittest.main()
