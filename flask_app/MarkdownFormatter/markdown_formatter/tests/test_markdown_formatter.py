import unittest
from main import format_markdown

class MarkdownFormatterTest(unittest.TestCase):

    def test_format_headings(self):
        content = "# Heading 1\n## Heading 2\n### Heading 3"
        expected = "  # Heading 1\n  ## Heading 2\n  ### Heading 3\n"
        self.assertEqual(format_markdown(content), expected)

    def test_format_lists(self):
        content = "- Item 1\n- Item 2\n  - Subitem 1"
        expected = "  - Item 1\n  - Item 2\n    - Subitem 1\n"
        self.assertEqual(format_markdown(content), expected)

    def test_format_links(self):
        content = "[Link Text](https://example.com)"
        expected = "  [Link Text](https://example.com)\n"
        self.assertEqual(format_markdown(content), expected)

    def test_format_images(self):
        content = "![Alt Text](image.jpg)"
        expected = "  ![Alt Text](image.jpg)\n"
        self.assertEqual(format_markdown(content), expected)

    def test_format_code_blocks(self):
        content = "```python\nprint('Hello world')\n```"
        expected = "  ```python\nprint('Hello world')\n```\n"
        self.assertEqual(format_markdown(content), expected)

    def test_format_empty_file(self):
        content = ""
        self.assertEqual(format_markdown(content), "")

    def test_handle_invalid_markdown(self):
        content = "This is invalid markdown"
        with self.assertRaises(mistletoe.core.MistletoeError):
            format_markdown(content)

if __name__ == '__main__':
    unittest.main()