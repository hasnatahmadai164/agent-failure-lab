import re
from pathlib import Path

import pytest

from agent_failure_lab import __version__
from agent_failure_lab.catalog import END_MARKER, START_MARKER, catalog_page, catalog_table, splice
from agent_failure_lab.registry import build_registry
from agent_failure_lab.scenario import CATEGORIES
from loader import ROOT, load_module

SCRIPT = load_module("scripts/generate_catalog.py", "generate_catalog_for_docs")
BLOB = SCRIPT.README_LINK_BASE
DASHES = (chr(0x2014), chr(0x2013))
BANNED_WORDS = [
    "demo",
    "toy",
    "tutorial",
    "prototype",
    "sample",
    "starter",
    "robust",
    "seamless",
    "powerful",
    "leverage",
    "cutting-edge",
    "game-changing",
    "blazing",
    "ai-generated",
]
SCENARIOS = build_registry().scenarios()


def _text_files() -> list[Path]:
    markdown = [
        path
        for path in [*ROOT.glob("*.md"), *ROOT.glob("docs/*.md"), *ROOT.glob(".github/**/*.md")]
        if path.is_file()
    ]
    failure_readmes = list((ROOT / "src" / "agent_failure_lab" / "failures").glob("*/README.md"))
    templates = list((ROOT / ".github").glob("**/*.yml"))
    return sorted({*markdown, *failure_readmes, *templates})


FILES = _text_files()


def _name(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def test_the_documentation_files_were_found() -> None:
    names = {_name(path) for path in FILES}

    assert {"README.md", "CONTRIBUTING.md", "CHANGELOG.md", "docs/guards.md"} <= names
    assert len(FILES) > 20


@pytest.mark.parametrize("path", FILES, ids=_name)
def test_no_dash_is_used_as_punctuation(path: Path) -> None:
    text = path.read_text(encoding="utf-8")

    assert not any(dash in text for dash in DASHES)


@pytest.mark.parametrize("path", FILES, ids=_name)
def test_no_file_mentions_a_numbered_stage(path: Path) -> None:
    assert not re.search(r"\bstages?\s*\d", path.read_text(encoding="utf-8"), re.IGNORECASE)


@pytest.mark.parametrize("path", FILES, ids=_name)
def test_none_of_the_words_the_project_avoids_appear(path: Path) -> None:
    text = path.read_text(encoding="utf-8").lower()

    found = [
        word for word in BANNED_WORDS if re.search(rf"(?<![\w-]){re.escape(word)}(?![\w-])", text)
    ]
    assert found == []


@pytest.mark.parametrize("path", FILES, ids=_name)
def test_files_are_plain_utf8_with_unix_line_endings(path: Path) -> None:
    raw = path.read_bytes()

    assert not raw.startswith(b"\xef\xbb\xbf")
    assert b"\r\n" not in raw
    assert raw.endswith(b"\n")


def test_the_readme_table_is_the_one_the_registry_produces() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    expected = splice(readme, catalog_table(SCENARIOS, prefix=BLOB))

    assert readme == expected


def test_the_catalog_page_is_the_one_the_registry_produces() -> None:
    page = (ROOT / "docs" / "catalog.md").read_text(encoding="utf-8")

    assert page == catalog_page(SCENARIOS)


def test_the_readme_has_a_place_for_the_terminal_output() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert START_MARKER in readme
    assert END_MARKER in readme
    assert "<!-- terminal-output:start -->" in readme
    assert "<!-- terminal-output:end -->" in readme


def test_the_readme_leads_with_the_install_and_the_first_command() -> None:
    lines = (ROOT / "README.md").read_text(encoding="utf-8").splitlines()

    assert lines[0] == "# agent-failure-lab"
    assert "pip install agent-failure-lab" in lines
    assert "aflab run duplicate-side-effect" in lines


def test_the_taxonomy_names_every_category_and_every_failure() -> None:
    taxonomy = (ROOT / "docs" / "taxonomy.md").read_text(encoding="utf-8")

    for category in CATEGORIES:
        assert f"## {category}\n" in taxonomy
    for scenario in SCENARIOS:
        assert f"`{scenario.slug}`" in taxonomy


def test_each_failure_sits_under_its_own_category_in_the_taxonomy() -> None:
    taxonomy = (ROOT / "docs" / "taxonomy.md").read_text(encoding="utf-8")
    sections = dict(re.findall(r"^## (\S+)\n(.*?)(?=^## |\Z)", taxonomy, re.MULTILINE | re.DOTALL))

    for scenario in SCENARIOS:
        assert f"`{scenario.slug}`" in sections[scenario.category]


def test_every_guard_a_failure_uses_has_a_section_in_the_guards_reference() -> None:
    guards = (ROOT / "docs" / "guards.md").read_text(encoding="utf-8")
    headings = "\n".join(line for line in guards.splitlines() if line.startswith("## "))

    for scenario in SCENARIOS:
        for guard in scenario.guards:
            assert guard in headings


def test_the_changelog_has_an_entry_for_the_current_version() -> None:
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")

    assert f"## [{__version__}] - " in changelog
    assert "## [Unreleased]" in changelog


def test_the_version_is_a_plain_release_number() -> None:
    assert re.fullmatch(r"\d+\.\d+\.\d+", __version__)


LINK = re.compile(r"(?<!!)\[[^\]]*\]\(([^)\s]+)\)")


def _links(path: Path) -> list[tuple[str, Path | None]]:
    resolved: list[tuple[str, Path | None]] = []
    for target in LINK.findall(path.read_text(encoding="utf-8")):
        if target.startswith(BLOB):
            resolved.append((target, ROOT / target.removeprefix(BLOB).split("#")[0]))
        elif target.startswith(("http://", "https://", "mailto:", "#")):
            resolved.append((target, None))
        else:
            resolved.append((target, (path.parent / target.split("#")[0]).resolve()))
    return resolved


@pytest.mark.parametrize("path", [p for p in FILES if p.suffix == ".md"], ids=_name)
def test_links_to_files_in_the_repository_point_at_files_that_exist(path: Path) -> None:
    missing = [target for target, local in _links(path) if local is not None and not local.exists()]

    assert missing == []
