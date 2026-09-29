# One source, three application versions

Share contacts, dates, and work history across backend, frontend, and infrastructure applications. Each version selects its own bullets. Recompile to pick up shared edits.

## Start

[Open in Overleaf](https://www.overleaf.com/docs?snip_uri=https%3A%2F%2Fraw.githubusercontent.com%2Fdeepdave98%2Flatex-resume-and-cv-templates%2Fmain%2Fdownloads%2Fapplication-versions.zip&engine=xelatex&main_document=backend.tex) or [download the ZIP](https://raw.githubusercontent.com/deepdave98/latex-resume-and-cv-templates/main/downloads/application-versions.zip).

The ZIP contains all three versions and their shared files. Keep them in one project; three separate Overleaf projects would stop sharing edits.

In Overleaf, go to **Settings > Compiler > Main document** and choose `backend.tex`, `frontend.tex`, or `infrastructure.tex`. The import starts with `backend.tex` and XeLaTeX. Recompile after changing the selection. When editing a shared file, Overleaf builds the selected main document. [Main document settings](https://docs.overleaf.com/getting-started/recompiling-your-project/the-main-document)

Locally, run this inside the extracted ZIP or `examples/application-versions/`:

```bash
latexmk -outdir=build backend.tex frontend.tex infrastructure.tex
```

The included `latexmkrc` selects XeLaTeX. The PDFs are `build/backend.pdf`, `build/frontend.pdf`, and `build/infrastructure.pdf`. To build only one, pass only that file. This command also works on Windows with `latexmk` on `PATH`.

From the repository root, `make application-versions` writes the PDFs to `build/application-versions/`.

## Edit facts once

| File | Edit here |
| --- | --- |
| `content/profile.tex` | Name, city, contacts, and profile links |
| `content/experience.tex` | Titles, employers, dates, and the full set of work bullets |
| `content/education.tex` | Education |
| `content/skills.tex` | Skills |
| `backend.tex`, `frontend.tex`, `infrastructure.tex` | Bullet selection and order for each application |
| `setup.tex` | Shared imports and the one-page warning |
| `resume.cls` | Styling; supplied in the ZIP, reused from the root in a clone |

Replace every example with your own facts. Do not change your title or employer to match a job posting. Select work that is relevant and that you can explain.

## Select bullets

Each named command in `content/experience.tex` holds one bullet. The version files list the commands to include inside `jobduties`. Remove a command to omit a bullet; move it to change the order. The text stays in the shared file.

To add a bullet, define it once in `content/experience.tex`:

```latex
\newcommand{\BulletExportRecovery}{%
  \ResumeBullet{Fixed [export failure] by [change]; verified [recovery behavior] with [test].}%
}
```

Then select it inside the relevant role's `jobduties` list:

```latex
\BulletExportRecovery
```

Use a unique command name containing letters only. Keep `\ResumeBullet{...}` around the text: it adds the list item and checks that selected bullet for placeholders. Do not add another `\item` before it. An unknown command is a compile error, not an omitted bullet.

To add a role, copy one shared role command and define it under a new name. Add that command and its selected bullet list to each version where the role belongs. Keep entries in reverse chronological order. The versions choose content explicitly; new roles and bullets are not included automatically.

## Check before sending

Rebuild every version you plan to send. Editing a shared file does not update a PDF you already downloaded.

- Read each PDF, including contacts, dates, links, and page breaks.
- Check the compile log for placeholders and the one-page limit.
- Unselected bullets are not checked. Review them when you select them later. Text hidden inside your own commands may also escape the checks.
- Only a PDF contains the selected version. The source ZIP contains the entire bullet bank, including unselected material. Do not send it with an application or post private work in a public fork.
