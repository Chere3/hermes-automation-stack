import io
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest.mock import patch

from validate_docs import main, markdown_files, validate_repository


class DocumentationValidationTests(unittest.TestCase):
    def write(self, root: Path, relative_path: str, content: str) -> None:
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def test_reports_a_missing_relative_markdown_link_but_ignores_code_samples(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write(
                root,
                "README.md",
                "[Missing](docs/missing.md)\n\n"
                "`[inline](not-a-link.md)`\n\n"
                "```md\n[example](also-not-a-link.md)\n```\n",
            )
            errors = validate_repository(root)
        self.assertIn("README.md: missing relative link: docs/missing.md", errors)
        self.assertEqual(len(errors), 1)

    def test_parses_spaces_parentheses_and_external_schemes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write(root, "docs/guide (v1).md", "# Guide\n")
            self.write(
                root,
                "README.md",
                "[Guide](<docs/guide (v1).md>)\n"
                "[Reference guide][guide]\n\n"
                "[guide]: <docs/guide (v1).md>\n\n"
                "[Website](https://example.test/docs)\n"
                "[FTP](ftp://example.test/archive)\n"
                "[Anchor](#section)\n"
                "[CDN](//example.test/image.png)\n",
            )
            errors = validate_repository(root)
        self.assertEqual(errors, [])

    def test_covers_root_readmes_docs_and_skills(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write(root, "README.md", "# Readme\n")
            self.write(root, "docs/guide.md", "# Guide\n")
            self.write(root, "skills/example/README.md", "# Example\n")
            files = {path.relative_to(root).as_posix() for path in markdown_files(root)}
        self.assertEqual(files, {"README.md", "docs/guide.md", "skills/example/README.md"})

    def test_reports_malformed_skill_frontmatter(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write(root, "README.md", "# Readme\n")
            self.write(root, "skills/example/SKILL.md", "---\nname: [broken\n---\n")
            errors = validate_repository(root)
        self.assertTrue(any("skills/example/SKILL.md: malformed YAML frontmatter" in error for error in errors))

    def test_reports_missing_skill_frontmatter(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write(root, "README.md", "# Readme\n")
            self.write(root, "skills/example/SKILL.md", "# No metadata\n")
            errors = validate_repository(root)
        self.assertIn(
            "skills/example/SKILL.md: missing opening YAML frontmatter delimiter",
            errors,
        )

    def test_reports_duplicate_frontmatter_keys(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write(root, "README.md", "# Readme\n")
            self.write(
                root,
                "skills/example/SKILL.md",
                "---\nname: first\nname: second\n---\n",
            )
            errors = validate_repository(root)
        self.assertTrue(any("found duplicate key 'name'" in error for error in errors))

    def test_reports_unhashable_frontmatter_keys(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write(root, "README.md", "# Readme\n")
            self.write(root, "skills/example/SKILL.md", "---\n[one, two]: value\n---\n")
            errors = validate_repository(root)
        self.assertTrue(any("skills/example/SKILL.md: malformed YAML frontmatter" in error for error in errors))

    def test_current_repository_content_passes(self):
        self.assertEqual(validate_repository(), [])

    def test_cli_prints_failures_to_stderr_and_returns_nonzero(self):
        stderr = io.StringIO()
        with patch("validate_docs.validate_repository", return_value=["README.md: missing relative link: docs/nope.md"]):
            with redirect_stderr(stderr):
                result = main()
        self.assertEqual(result, 1)
        self.assertIn("Documentation validation failed:", stderr.getvalue())
        self.assertIn("README.md: missing relative link: docs/nope.md", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
