# LaTeX Resume and CV Templates

Resumes for software, AI, and ML engineers, plus a graduate-admissions CV. Edit in Overleaf or build with XeLaTeX.

## Pick a template

| Template | Pages | Edit | Download |
| --- | --- | --- | --- |
| No internship | 1 | [Open in Overleaf](https://www.overleaf.com/docs?snip_uri=https%3A%2F%2Fraw.githubusercontent.com%2Fdeepdave98%2Flatex-resume-and-cv-templates%2Fmain%2Fdownloads%2Fno-internship-resume.zip&engine=xelatex&main_document=resume.tex) | [ZIP](https://raw.githubusercontent.com/deepdave98/latex-resume-and-cv-templates/main/downloads/no-internship-resume.zip) · [PDF](https://raw.githubusercontent.com/deepdave98/latex-resume-and-cv-templates/main/output/pdf/no-internship-resume.pdf) |
| New grad | 1 | [Open in Overleaf](https://www.overleaf.com/docs?snip_uri=https%3A%2F%2Fraw.githubusercontent.com%2Fdeepdave98%2Flatex-resume-and-cv-templates%2Fmain%2Fdownloads%2Fnew-grad-resume.zip&engine=xelatex&main_document=resume.tex) | [ZIP](https://raw.githubusercontent.com/deepdave98/latex-resume-and-cv-templates/main/downloads/new-grad-resume.zip) · [PDF](https://raw.githubusercontent.com/deepdave98/latex-resume-and-cv-templates/main/output/pdf/new-grad-resume.pdf) |
| Experienced | 2 | [Open in Overleaf](https://www.overleaf.com/docs?snip_uri=https%3A%2F%2Fraw.githubusercontent.com%2Fdeepdave98%2Flatex-resume-and-cv-templates%2Fmain%2Fdownloads%2Fexperienced-resume.zip&engine=xelatex&main_document=resume.tex) | [ZIP](https://raw.githubusercontent.com/deepdave98/latex-resume-and-cv-templates/main/downloads/experienced-resume.zip) · [PDF](https://raw.githubusercontent.com/deepdave98/latex-resume-and-cv-templates/main/output/pdf/experienced-resume.pdf) |
| AI engineer | 1 | [Open in Overleaf](https://www.overleaf.com/docs?snip_uri=https%3A%2F%2Fraw.githubusercontent.com%2Fdeepdave98%2Flatex-resume-and-cv-templates%2Fmain%2Fdownloads%2Fai-engineer-resume.zip&engine=xelatex&main_document=resume.tex) | [ZIP](https://raw.githubusercontent.com/deepdave98/latex-resume-and-cv-templates/main/downloads/ai-engineer-resume.zip) · [PDF](https://raw.githubusercontent.com/deepdave98/latex-resume-and-cv-templates/main/output/pdf/ai-engineer-resume.pdf) |
| ML engineer | 1 | [Open in Overleaf](https://www.overleaf.com/docs?snip_uri=https%3A%2F%2Fraw.githubusercontent.com%2Fdeepdave98%2Flatex-resume-and-cv-templates%2Fmain%2Fdownloads%2Fml-engineer-resume.zip&engine=xelatex&main_document=resume.tex) | [ZIP](https://raw.githubusercontent.com/deepdave98/latex-resume-and-cv-templates/main/downloads/ml-engineer-resume.zip) · [PDF](https://raw.githubusercontent.com/deepdave98/latex-resume-and-cv-templates/main/output/pdf/ml-engineer-resume.pdf) |
| Graduate admissions | 1 (starter) | [Open in Overleaf](https://www.overleaf.com/docs?snip_uri=https%3A%2F%2Fraw.githubusercontent.com%2Fdeepdave98%2Flatex-resume-and-cv-templates%2Fmain%2Fdownloads%2Fgraduate-admissions-resume.zip&engine=xelatex&main_document=resume.tex) | [ZIP](https://raw.githubusercontent.com/deepdave98/latex-resume-and-cv-templates/main/downloads/graduate-admissions-resume.zip) · [PDF](https://raw.githubusercontent.com/deepdave98/latex-resume-and-cv-templates/main/output/pdf/graduate-admissions-resume.pdf) |

For admissions, follow the program's length requirements. [Image previews](output/pdf/README.md) · [Section order](docs/section-order.md) · [AI/ML guide](docs/ai-ml-resumes.md) · [Admissions guide](docs/graduate-admissions.md).

## Edit the content

1. Open a template above, or upload its ZIP to Overleaf. Select **XeLaTeX** and `resume.tex`.
2. Replace contacts, education, credentials, and sample work in `resume.tex`. Delete unused entries.
3. Recompile. Check placeholder warnings, every page, and the PDF's links. Warnings can miss unfinished text.

[Editing reference](docs/editing.md) · [Bullet examples](examples/engineering-bullets.md). Styling lives in `resume.cls`.

## Build locally

[Install XeLaTeX and latexmk](docs/local-setup.md), then run inside an extracted starter:

```bash
latexmk resume.tex
```

Output: `resume.pdf`. In a clone, `make` builds all starters to `build/`.

Run `make doctor` in a clone to check for missing tools, LaTeX packages, and fonts.

## Optional tools

- **[PDF reviewer](https://raw.githubusercontent.com/deepdave98/latex-resume-and-cv-templates/main/downloads/pdf-review.zip):** unzip and open `pdf-review.html`. Inspect pages, text, and links; check upload limits or edit a text copy for application forms. Works offline; the PDF stays unchanged. [Limits and privacy](tools/pdf-review/README.md).
- **[Shared-content example](examples/application-versions/README.md):** keep facts in one place and select different bullets per application. [Overleaf](https://www.overleaf.com/docs?snip_uri=https%3A%2F%2Fraw.githubusercontent.com%2Fdeepdave98%2Flatex-resume-and-cv-templates%2Fmain%2Fdownloads%2Fapplication-versions.zip&engine=xelatex&main_document=backend.tex) · [ZIP](https://raw.githubusercontent.com/deepdave98/latex-resume-and-cv-templates/main/downloads/application-versions.zip) · PDFs: [backend](https://raw.githubusercontent.com/deepdave98/latex-resume-and-cv-templates/main/output/pdf/application-backend.pdf), [frontend](https://raw.githubusercontent.com/deepdave98/latex-resume-and-cv-templates/main/output/pdf/application-frontend.pdf), [infrastructure](https://raw.githubusercontent.com/deepdave98/latex-resume-and-cv-templates/main/output/pdf/application-infrastructure.pdf). Send the PDF, not the source ZIP: it includes unselected work.

[Contribute](CONTRIBUTING.md) · [Community examples](examples/community/README.md) · [Tests](tests/README.md) · [MIT License](LICENSE) · [Report a security issue privately](https://github.com/deepdave98/latex-resume-and-cv-templates/security/advisories/new).
