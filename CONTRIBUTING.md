# Contributing

Use an issue for a question or bug; open a PR for a change.

## Template and documentation changes

- Keep shared layout and styling in `resume.cls`.
- Keep each shipped starter at one page; preserve support for longer resumes and CVs.
- Keep examples shipped in the resume templates and maintainer-written guides fictional: use placeholder companies, roles, metrics, links, and contact details.
- Run `make` with XeLaTeX.
- Run `make preview` and review every page if the output changes.
- Run `make downloads` after changing template content, styling, the license, or starter instructions.
- Run `make test`; it checks PDF text, ZIP freshness, builds from the actual downloads, and placeholder warnings. See the [test guide](tests/README.md) for dependencies and baseline updates.
- Run `git diff --check`.

Include before-and-after screenshots for layout changes.

For AI/ML examples, distinguish offline evaluation from production results. State the baseline and data split when they affect the claim. Do not invent research, publications, degrees, or metrics. See the [role guide](docs/ai-ml-resumes.md).

## Writing examples

Suggest improvements to the [bullet guide](examples/engineering-bullets.md) in an issue or PR. Use fictional examples that teach one writing decision. Keep claims specific without implying that a phrase or format guarantees interviews.

Issues, PRs, and their history are public. Remove personal details and confidential work before posting; do not attach someone's resume or private evidence.
