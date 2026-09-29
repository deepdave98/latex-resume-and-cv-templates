#!/usr/bin/env python3
"""Check community-entry structure and index coverage, not claims or consent."""

from collections import Counter
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
DISCIPLINES = {"backend", "frontend", "data", "ai", "ml", "general"}
STAGES = {"early-career", "experienced"}
SECTIONS = (
    "Original wording", "Proposed rewrite", "Contribution and context",
    "Context and checks", "Why the edit helps", "Permission", "Review record",
)
PERMISSIONS = (
    "I wrote the original wording and have the right to submit it; it is not copied from someone else's private resume.",
    "I removed employer, client, customer, product, team, and confidential system details.",
    "Every claim and number is truthful. I did not invent a metric or expose private evidence.",
    "I permit this submission to be published under the repository's MIT License.",
)
# Existing approval permalinks remain valid after the repository rename.
REPO_URL = r"https://github\.com/deepdave98/(?:latex-resume-and-cv-templates|swe-resume-templates)"
COMMENT = r"(?:issuecomment-\d+|discussion_r\d+|pullrequestreview-\d+)"


def field(text, name):
    values = re.findall(r"^- \*\*" + re.escape(name) + r":\*\* (.+)$", text, re.M)
    return values[0].strip() if len(values) == 1 else ""


def substantive(text):
    # Redaction placeholders are allowed, but cannot be the entire explanation.
    text = re.sub(r"<!--.*?-->|\[[^\]]*\]", "", text, flags=re.S)
    return any(character.isalpha() for character in text)


def check_entry(text, name):
    errors = []
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    parts = re.split(r"^## (.+)\s*$", text, flags=re.M)
    if tuple(parts[1::2]) != SECTIONS:
        return [f"{name}: use each section from TEMPLATE.md once, in order"]
    sections = dict(zip(parts[1::2], parts[2::2]))
    header = parts[0]
    discipline, stage = field(header, "Discipline"), field(header, "Career stage")
    if discipline not in DISCIPLINES or stage not in STAGES:
        errors.append(f"{name}: choose a listed discipline and career stage")
    elif not re.fullmatch(re.escape(f"{stage}-{discipline}-") + r"[a-z0-9]+(?:-[a-z0-9]+)*\.md", name):
        errors.append(f"{name}: filename must start with {stage}-{discipline}- and use lowercase words")
    title = re.findall(r"^# (.+)$", header, re.M)
    if len(title) != 1 or not substantive(title[0]):
        errors.append(f"{name}: add a descriptive title")
    for label in ("Role", "Attribution"):
        if not substantive(field(header, label)):
            errors.append(f"{name}: fill in {label}")
    for section in SECTIONS[:3] + ("Why the edit helps",):
        if not substantive(sections[section]):
            errors.append(f"{name}: fill in {section}")
    for label in ("Result", "Validation", "Numbers", "Privacy check"):
        if not substantive(field(sections["Context and checks"], label)):
            errors.append(f"{name}: fill in {label}; use None when there is no number")
    permissions = re.findall(r"^- \[[xX]\] (.+)$", sections["Permission"], re.M)
    if tuple(permissions) != PERMISSIONS or re.search(r"^- \[ \]", sections["Permission"], re.M):
        errors.append(f"{name}: all four permissions must be checked without changing their wording")
    patterns = {
        "Submission": REPO_URL + r"/(?:issues|pull)/[1-9]\d*",
        "Author approval": REPO_URL + r"/(?:issues|pull)/[1-9]\d*#" + COMMENT,
        "Review": REPO_URL + r"/pull/[1-9]\d*#" + COMMENT,
    }
    for label, pattern in patterns.items():
        if not re.fullmatch(pattern, field(sections["Review record"], label)):
            errors.append(f"{name}: add a repository {'comment permalink' if label != 'Submission' else 'issue or PR URL'} for {label}")
    return errors


def check_directory(directory):
    errors = []
    index = (directory / "README.md").read_text(encoding="utf-8")
    start, end = "<!-- reviewed-examples:start -->", "<!-- reviewed-examples:end -->"
    if index.count(start) != 1 or index.count(end) != 1 or index.index(start) > index.index(end):
        return ["README.md: keep one ordered pair of reviewed-index markers"]
    table = re.sub(r"<!--.*?-->", "", index.split(start, 1)[1].split(end, 1)[0], flags=re.S)
    links = re.findall(r"\[[^\]\n]+\]\(([^)\n]+)\)", table)
    counts = Counter(links)
    accepted = directory / "accepted"
    if accepted.is_symlink() or (accepted.exists() and not accepted.is_dir()):
        return ["accepted/: use a regular directory, not a symlink"]
    entries = sorted(accepted.glob("*.md"))
    paths = {"accepted/" + entry.name for entry in entries}
    for link, count in counts.items():
        if link not in paths or not re.fullmatch(r"accepted/[a-z0-9]+(?:-[a-z0-9]+)*\.md", link):
            errors.append(f"README.md: invalid or missing indexed file {link}")
        if count != 1:
            errors.append(f"README.md: index {link} exactly once")
    for entry in entries:
        if entry.is_symlink() or not entry.is_file():
            errors.append(f"{entry.name}: expected a regular Markdown file")
            continue
        if counts["accepted/" + entry.name] != 1:
            errors.append(f"{entry.name}: add exactly one reviewed-index link")
        errors.extend(check_entry(entry.read_text(encoding="utf-8"), entry.name))
    if entries and "No accepted examples yet." in index:
        errors.append("README.md: remove the empty-index notice after accepting the first entry")
    return errors


def main():
    try:
        errors = check_directory(ROOT / "examples" / "community")
    except (OSError, UnicodeError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    for error in errors:
        print(f"FAIL: {error}", file=sys.stderr)
    if not errors:
        print("PASS: community records and index are consistent; human review is still required")
    return int(bool(errors))


if __name__ == "__main__":
    sys.exit(main())
