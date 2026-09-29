"""Community publication-record checks. Fixtures are synthetic, not submissions."""

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import check_community_examples as checker


NAME = "early-career-backend-synthetic-test.md"
ENTRY = """# Synthetic test fixture

- **Discipline:** backend
- **Career stage:** early-career
- **Role:** Software Engineer
- **Attribution:** Anonymous

## Original wording

> Tested [COMPONENT].

## Proposed rewrite

> Added a regression test for [FAILURE] in [COMPONENT].

## Contribution and context

Test fixture only; not a real contribution.

## Context and checks

- **Result:** Regression test passed.
- **Validation:** Synthetic local-test description.
- **Numbers:** None
- **Privacy check:** Synthetic text contains no private details.

## Why the edit helps

Names the test and the failure without adding an outcome.

## Permission

""" + "\n".join("- [x] " + permission for permission in checker.PERMISSIONS) + """

## Review record

- **Submission:** https://github.com/deepdave98/latex-resume-and-cv-templates/issues/123
- **Author approval:** https://github.com/deepdave98/latex-resume-and-cv-templates/pull/124#issuecomment-123
- **Review:** https://github.com/deepdave98/latex-resume-and-cv-templates/pull/124#pullrequestreview-456
"""


def index(links=()):
    return "\n".join([
        "# Community Resume Examples", "<!-- reviewed-examples:start -->",
        "| Example | Discipline | Career stage | What the edit teaches |",
        "| --- | --- | --- | --- |",
        *(f"| [Test]({link}) | backend | early-career | Synthetic test |" for link in links),
        "<!-- reviewed-examples:end -->", "",
    ])


class EntryTests(unittest.TestCase):
    def test_complete_record_and_redactions_pass(self):
        self.assertEqual(checker.check_entry(ENTRY, NAME), [])

    def test_approval_links_survive_the_repository_rename(self):
        previous = ENTRY.replace("latex-resume-and-cv-templates", "swe-resume-templates")
        self.assertEqual(checker.check_entry(previous, NAME), [])
        for suffix in ("-copy", ".evil.test", "/extra"):
            changed = ENTRY.replace("latex-resume-and-cv-templates", "latex-resume-and-cv-templates" + suffix)
            self.assertTrue(checker.check_entry(changed, NAME))

    def test_ai_and_ml_records_use_the_same_review_requirements(self):
        for discipline in ("ai", "ml"):
            with self.subTest(discipline=discipline):
                text = ENTRY.replace("**Discipline:** backend", f"**Discipline:** {discipline}")
                name = f"early-career-{discipline}-synthetic-test.md"
                self.assertEqual(checker.check_entry(text, name), [])
                self.assertTrue(checker.check_entry(text.replace("- [x]", "- [ ]", 1), name))

    def test_each_permission_is_required(self):
        for permission in checker.PERMISSIONS:
            with self.subTest(permission=permission):
                text = ENTRY.replace("- [x] " + permission, "- [ ] " + permission)
                self.assertTrue(checker.check_entry(text, NAME))

    def test_each_section_is_required_once(self):
        for section in checker.SECTIONS:
            with self.subTest(section=section):
                self.assertTrue(checker.check_entry(ENTRY.replace("## " + section, "### " + section), NAME))
                self.assertTrue(checker.check_entry(ENTRY + "\n## " + section + "\nDuplicate\n", NAME))

    def test_missing_metadata_and_context_fail(self):
        for label in ("Discipline", "Career stage", "Role", "Attribution", "Result", "Validation", "Numbers", "Privacy check"):
            with self.subTest(label=label):
                self.assertTrue(checker.check_entry(ENTRY.replace("**" + label + ":**", "**Missing:**"), NAME))

    def test_template_and_placeholder_only_prose_fail(self):
        template = (checker.ROOT / "examples/community/TEMPLATE.md").read_text(encoding="utf-8")
        self.assertTrue(checker.check_entry(template, NAME))
        self.assertTrue(checker.check_entry(ENTRY.replace(
            "Added a regression test for [FAILURE] in [COMPONENT].", "[Rewrite here]"), NAME))

    def test_duplicate_metadata_is_rejected(self):
        self.assertTrue(checker.check_entry(ENTRY.replace("## Original wording", "- **Attribution:** Other\n\n## Original wording"), NAME))

    def test_attribution_supports_non_latin_names(self):
        self.assertEqual(checker.check_entry(ENTRY.replace("**Attribution:** Anonymous", "**Attribution:** 李明"), NAME), [])

    def test_review_requires_comment_links_in_this_repo(self):
        for replacement in (
            "https://github.com/deepdave98/latex-resume-and-cv-templates/pull/124",
            "https://github.com/another/repo/pull/124#issuecomment-123",
            "https://github.com/deepdave98/latex-resume-and-cv-templates/pull/124#top",
            "https://github.com/deepdave98/latex-resume-and-cv-templates/pull/124?token=secret#issuecomment-123",
            "https://github.com.evil.test/deepdave98/latex-resume-and-cv-templates/pull/124#issuecomment-123",
        ):
            with self.subTest(replacement=replacement):
                text = ENTRY.replace("https://github.com/deepdave98/latex-resume-and-cv-templates/pull/124#issuecomment-123", replacement)
                self.assertTrue(checker.check_entry(text, NAME))

    def test_stable_filename_matches_stage_and_discipline(self):
        for name in ("Example.md", "experienced-backend-test.md", "early-career-frontend-test.md", "early-career-backend-test_file.md"):
            with self.subTest(name=name):
                self.assertTrue(checker.check_entry(ENTRY, name))

    def test_html_comments_cannot_supply_approval(self):
        text = ENTRY.replace("- **Author approval:**", "<!-- - **Author approval:**").replace("#issuecomment-123\n", "#issuecomment-123 -->\n")
        self.assertTrue(checker.check_entry(text, NAME))


class IndexTests(unittest.TestCase):
    def test_repository_records_and_index(self):
        self.assertEqual(checker.check_directory(checker.ROOT / "examples/community"), [])

    def test_empty_index_is_valid_without_invented_entries(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "README.md").write_text(index(), encoding="utf-8")
            self.assertEqual(checker.check_directory(root), [])

    def test_missing_duplicate_or_unindexed_entry_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "accepted").mkdir()
            (root / "accepted" / NAME).write_text(ENTRY, encoding="utf-8")
            path = "accepted/" + NAME
            for links, valid in (([path], True), ([], False), ([path, path], False), ([path, "accepted/missing.md"], False), (["../private.md"], False)):
                with self.subTest(links=links):
                    (root / "README.md").write_text(index(links), encoding="utf-8")
                    self.assertEqual(checker.check_directory(root) == [], valid)

    def test_acceptance_removes_empty_notice(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "accepted").mkdir()
            (root / "accepted" / NAME).write_text(ENTRY, encoding="utf-8")
            (root / "README.md").write_text("No accepted examples yet.\n" + index(["accepted/" + NAME]), encoding="utf-8")
            self.assertTrue(checker.check_directory(root))

    def test_commented_index_link_does_not_count(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "accepted").mkdir()
            (root / "accepted" / NAME).write_text(ENTRY, encoding="utf-8")
            content = index().replace("<!-- reviewed-examples:end -->", f"<!-- [Test](accepted/{NAME}) -->\n<!-- reviewed-examples:end -->")
            (root / "README.md").write_text(content, encoding="utf-8")
            self.assertTrue(checker.check_directory(root))

    def test_index_requires_unique_ordered_markers(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for content in ("# Missing markers", index() + "<!-- reviewed-examples:start -->", "<!-- reviewed-examples:end -->\n<!-- reviewed-examples:start -->"):
                with self.subTest(content=content):
                    (root / "README.md").write_text(content, encoding="utf-8")
                    self.assertTrue(checker.check_directory(root))

    def test_symlink_entry_is_not_read(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "accepted").mkdir()
            (root / "README.md").write_text(index(["accepted/" + NAME]), encoding="utf-8")
            try:
                (root / "accepted" / NAME).symlink_to(root / "README.md")
            except (OSError, NotImplementedError) as error:
                self.skipTest(str(error))
            self.assertTrue(checker.check_directory(root))

    def test_cli_exit_status_and_errors(self):
        with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
            with patch.object(checker, "check_directory", return_value=[]):
                self.assertEqual(checker.main(), 0)
            with patch.object(checker, "check_directory", return_value=["missing approval"]):
                self.assertEqual(checker.main(), 1)
            with patch.object(checker, "check_directory", side_effect=OSError("missing index")):
                self.assertEqual(checker.main(), 1)


if __name__ == "__main__":
    unittest.main()
