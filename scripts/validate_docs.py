#!/usr/bin/env python3
"""Validate local Markdown links and YAML metadata in reusable skills.

The check is deliberately offline: external URLs are outside this repository's
control, while broken local links and malformed skill metadata are regressions
we can catch deterministically in CI.
"""

from __future__ import annotations

import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

from markdown_it import MarkdownIt
import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MARKDOWN = MarkdownIt("commonmark")


class UniqueKeyLoader(yaml.SafeLoader):
    """Safe YAML loader that refuses ambiguous duplicate mapping keys."""


def construct_unique_mapping(loader: UniqueKeyLoader, node: yaml.nodes.MappingNode, deep: bool = False):
    mapping = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                f"found duplicate key {key!r}",
                key_node.start_mark,
            )
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, construct_unique_mapping
)


def markdown_files(root: Path) -> list[Path]:
    """Return Markdown files covered by the repository link check."""
    files = set(root.glob("README*.md"))
    files.update((root / "docs").rglob("*.md"))
    files.update((root / "skills").rglob("*.md"))
    return sorted(path for path in files if path.is_file())


def is_local_target(target: str | None) -> bool:
    if not target:
        return False
    parsed = urlsplit(target)
    return not (
        target.startswith("#")
        or target.startswith("//")
        or bool(parsed.scheme)
    )


def markdown_destinations(text: str) -> list[str]:
    """Return link and image destinations parsed from Markdown, not code samples."""
    destinations: list[str] = []
    for token in MARKDOWN.parse(text):
        inline_tokens = token.children or []
        for inline_token in inline_tokens:
            if inline_token.type == "link_open":
                destination = inline_token.attrGet("href")
            elif inline_token.type == "image":
                destination = inline_token.attrGet("src")
            else:
                continue
            if destination is not None:
                destinations.append(destination)
    return destinations


def validate_markdown_links(path: Path, root: Path) -> list[str]:
    """Return failures for relative Markdown destinations in *path*."""
    text = path.read_text(encoding="utf-8")
    failures: list[str] = []
    relative_path = path.relative_to(root).as_posix()

    for target in markdown_destinations(text):
        if not is_local_target(target):
            continue
        parsed = urlsplit(target)
        destination = unquote(parsed.path)
        if not destination:
            continue
        resolved = (path.parent / destination).resolve()
        try:
            resolved.relative_to(root.resolve())
        except ValueError:
            failures.append(f"{relative_path}: relative link escapes repository: {target}")
        else:
            if not resolved.exists():
                failures.append(f"{relative_path}: missing relative link: {target}")
    return failures


def validate_skill_frontmatter(path: Path, root: Path) -> list[str]:
    """Return failures for the YAML frontmatter at the start of a SKILL.md."""
    text = path.read_text(encoding="utf-8")
    relative_path = path.relative_to(root).as_posix()
    if not text.startswith("---\n"):
        return [f"{relative_path}: missing opening YAML frontmatter delimiter"]

    closing_delimiter = text.find("\n---\n", len("---\n"))
    if closing_delimiter == -1:
        return [f"{relative_path}: missing closing YAML frontmatter delimiter"]

    frontmatter = text[len("---\n") : closing_delimiter]
    try:
        metadata = yaml.load(frontmatter, Loader=UniqueKeyLoader)
    except (TypeError, yaml.YAMLError) as error:
        return [
            f"{relative_path}: malformed YAML frontmatter: {getattr(error, 'problem', None) or error}"
        ]
    if not isinstance(metadata, dict):
        return [f"{relative_path}: YAML frontmatter must be a mapping"]
    return []


def validate_repository(root: Path = PROJECT_ROOT) -> list[str]:
    """Validate all repository-owned Markdown and skill metadata."""
    errors: list[str] = []
    for path in markdown_files(root):
        errors.extend(validate_markdown_links(path, root))
    for path in sorted((root / "skills").rglob("SKILL.md")):
        errors.extend(validate_skill_frontmatter(path, root))
    return errors


def main() -> int:
    errors = validate_repository()
    if errors:
        print("Documentation validation failed:", file=sys.stderr)
        print(*errors, sep="\n", file=sys.stderr)
        return 1
    print("Documentation validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
