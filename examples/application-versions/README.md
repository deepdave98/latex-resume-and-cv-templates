# One resume, tailored applications

Keep contacts, dates, projects, and work history in one place. Each application chooses which entries and bullets to show.

[Open in Overleaf](https://www.overleaf.com/docs?snip_uri=https%3A%2F%2Fraw.githubusercontent.com%2Fdeepdave98%2Flatex-resume-and-cv-templates%2Fmain%2Fdownloads%2Fapplication-versions.zip&engine=xelatex&main_document=resume.tex) · [Download ZIP](https://raw.githubusercontent.com/deepdave98/latex-resume-and-cv-templates/main/downloads/application-versions.zip) · [Base PDF](https://raw.githubusercontent.com/deepdave98/latex-resume-and-cv-templates/main/output/pdf/application-resume.pdf) · [Backend PDF](https://raw.githubusercontent.com/deepdave98/latex-resume-and-cv-templates/main/output/pdf/application-backend.pdf)

## Start

Extract the ZIP into a folder for your own resume, outside a public repository. In Overleaf, keep all its files in one project and use XeLaTeX.

- `resume.tex` is your base selection. It starts with education, two projects, and skills; no job is required.
- `backend.tex` uses the same facts, brings query work first, and leaves out one interface bullet.
- `content/` holds the actual text. Nothing appears in a PDF until an entry file selects it.

Replace the example content with your own work. The base resume is a selection too; it does not automatically print every bullet you add.

## Edit facts once

| File | What belongs here |
| --- | --- |
| `content/profile.tex` | Name, city, contacts, and links inside `\SharedHeader` |
| `content/education.tex` | Degrees and dates inside `\SharedEducation` |
| `content/projects.tex` | Project headings and their named bullets |
| `content/experience.tex` | Optional job headings and their named bullets |
| `content/skills.tex` | Skills inside `\SharedSkills` |
| `resume.tex`, `backend.tex` | Section order, selected entries, and selected bullets |
| `setup.tex` | Shared imports and page budget |
| `resume.cls` | Layout; included in the ZIP |

Change a shared fact here, then rebuild the versions that use it. PDFs you already downloaded stay unchanged.

## Make an application version

Copy `resume.tex` to a name such as `company-role.tex`. Keep it beside the original so it uses the same shared files.

In the copy, move whole section or entry blocks to change their order. Inside a `jobduties` list, remove a command to omit a bullet or move it to change the order. For example:

```latex
\SharedToolProject
\begin{jobduties}
  \ToolStorage
  \ToolWorkflow
\end{jobduties}
```

This selects two bullets in that order. It leaves `\ToolRecovery` out of this PDF without deleting it from `content/projects.tex` or changing your base resume.

To omit a project or job, remove its heading command and the following `jobduties` block from that version. Changing a selection never changes the shared facts.

## Bring your existing resume

Start from a copy of your completed starter. Move the content rather than rewriting your achievements to fit these examples.

1. Put your `\resumename` and `\resumecontact` block inside `\SharedHeader` in `content/profile.tex`.
2. Put your education entries inside `\SharedEducation` and your skills list inside `\SharedSkills`, replacing the examples.
3. Move each project heading into a named command in `content/projects.tex`. Move each bullet into its own command, replacing `\item` with `\ResumeBullet{...}`:

```latex
\newcommand{\SharedMyProject}{%
  \jobentry{[Project type and tools]}{[Project name]}{}{[Dates]}
}
\newcommand{\MyProjectFeature}{%
  \ResumeBullet{[Your existing bullet text]}
}
```

4. Select those commands in `resume.tex` and each application that needs them:

```latex
\SharedMyProject
\begin{jobduties}
  \MyProjectFeature
\end{jobduties}
```

Use unique command names containing letters only. Keep `\ResumeBullet` around literal bullet text so selected placeholders are checked. A misspelled command stops compilation.

**From the no-internship starter:** move your projects using the steps above. Keep Other Experience only if relevant; a paid job, club role, or volunteer entry can use the same pattern in `content/experience.tex`. There is no requirement to add software employment.

**From the new-grad starter:** also move your job heading and bullets into `content/experience.tex`. The example provides `\SharedRole`, `\RoleFeature`, and `\RoleFix` to replace with your content. In each entry file, remove the leading `% ` from the lines between `BEGIN OPTIONAL EXPERIENCE` and `END OPTIONAL EXPERIENCE`. Move that whole section above Projects when your work experience is more relevant. Keep the original title and dates across versions.

To add another job or project, repeat the heading-and-bullets pattern with new command names. Select it only in the versions that need it.

## Build and check

In Overleaf, choose an entry file under **Settings > Compiler > Main document** and recompile. An open file containing `\documentclass` may compile instead of the selected main document; confirm the resulting PDF is the application you intend to send. [Overleaf's main-document behavior](https://docs.overleaf.com/getting-started/recompiling-your-project/the-main-document)

Locally, with XeLaTeX and `latexmk` installed:

```bash
latexmk -outdir=build resume.tex backend.tex
```

The bundled `latexmkrc` selects XeLaTeX. Outputs are `build/resume.pdf` and `build/backend.pdf`. Build a new application by passing its filename, such as `latexmk -outdir=build company-role.tex`. These commands work from the extracted folder; a repository clone also provides `make application-versions`.

Read the exported PDF, check contacts and links, and resolve placeholder and page-limit warnings. The one-page budget is in `setup.tex`; change it when a longer resume is intentional. Only selected content is checked, so review an unused bullet when you choose it later.

Send the PDF. The source ZIP includes your whole collection of facts and bullets, including work omitted from that application.
