# Review a community example

Accept edits that clarify the author's contribution, a decision, a constraint, or a check. Do not ask for an offer letter or proof of a hire.

## Review in the open

For an issue submission, copy the redacted content into [`TEMPLATE.md`](TEMPLATE.md) and open a draft PR. Link the issue. For a PR submission, review the existing draft. Do not copy unredacted text into comments, commits, or another file.

Compare the before and after line by line. Ask about any new claim. The rewrite must not add ownership, scale, production use, causality, or a metric the author did not establish. Keep useful constraints; cut filler.

Ask the author to approve the exact final rewrite and the published byline in a comment. A useful reply is: “I approve this wording and the byline ‘Anonymous’ for publication under the MIT License.” Do not fill this in for them. Changed wording needs fresh approval.

## Before merging

Copy this checklist into a PR comment and resolve every item. Record that comment's permalink under **Review** in the entry.

- [ ] The submitter wrote the original, can share it, and agreed to the MIT License.
- [ ] Names, contacts, employers, clients, private URLs, and identifying incident details are removed from both versions and their context.
- [ ] The rewrite separates individual work from team results. It adds no unsupported scope, ownership, scale, causality, or seniority.
- [ ] The outcome and its check are explained. Any number has a unit, scope, time window, method, and comparison baseline where applicable. Local benchmarks are labeled. No private evidence is attached.
- [ ] “Why the edit helps” explains a reusable writing decision, not a claim that this wording gets interviews.
- [ ] The author approved the final wording and byline in a linked comment. They understand that Anonymous does not hide their GitHub history.
- [ ] The file and index follow the conventions below, and the local check passes.

Review checks the submitted explanation; it does not independently audit an employer's data. If a claim needs confidential evidence to make sense, remove the claim. If permission, ownership, or privacy is unresolved, do not merge.

## Publish one stable entry

- Store it at `accepted/<career-stage>-<discipline>-<short-topic>.md`, using lowercase words and hyphens. Keep that path stable after merging.
- Complete **Submission**, **Author approval**, and **Review** with links in this repository. Approval and review must link to the actual comments, not just the PR page.
- Add one row inside the reviewed-index markers in [`README.md`](README.md). Use a relative link to the file, its discipline and career stage, and one short lesson. Sort by career stage, then discipline, then filename.
- On the first acceptance, remove “No accepted examples yet.” Do not list drafts. Keep an existing example only while its context and review record remain valid.
- Run `python3 scripts/check_community_examples.py` from the repository root. No TeX installation is needed for this check.

Open the approval and review links before merging; the checker cannot verify their contents.

For a correction after publication, use another PR and get the author's approval again if the claim changes. Remove an entry from the current index if it cannot be corrected safely. Removing a file does not erase Git history, forks, or issue comments; do not promise full deletion.
