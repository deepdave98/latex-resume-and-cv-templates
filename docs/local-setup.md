# Local setup

Skip this if you use Overleaf. Local builds need XeLaTeX, `latexmk`, and LaTeX 2020-10-01 or newer.

## Install

macOS:

```bash
brew install --cask mactex-no-gui
```

Ubuntu or Debian:

```bash
sudo apt update
sudo apt install latexmk texlive-xetex texlive-latex-extra
```

Windows: install TeX Live or MiKTeX and put `latexmk` on `PATH`.

## Build a starter ZIP

Extract it, open a terminal in its folder, and run:

```bash
latexmk resume.tex
```

The bundled `latexmkrc` selects XeLaTeX. Output: `resume.pdf`.

## Build from a clone

```bash
git clone https://github.com/deepdave98/latex-resume-and-cv-templates.git
cd latex-resume-and-cv-templates
make
```

Edit files in `templates/`. `make` builds all starters to `build/`. To build one, use `make no-internship`, `make new-grad`, `make experienced`, `make ai-engineer`, `make ml-engineer`, or `make graduate-admissions`.

On Windows or without `make`, run the relevant command from the repository root:

```bash
latexmk -xelatex -outdir=build/no-internship templates/no-internship-resume.tex
latexmk -xelatex -outdir=build/new-grad templates/new-grad-resume.tex
latexmk -xelatex -outdir=build/experienced templates/experienced-resume.tex
latexmk -xelatex -outdir=build/ai-engineer templates/ai-engineer-resume.tex
latexmk -xelatex -outdir=build/ml-engineer templates/ml-engineer-resume.tex
latexmk -xelatex -outdir=build/graduate-admissions templates/graduate-admissions-resume.tex
```

`make preview` refreshes published PDFs in `output/pdf/` and PNGs in `preview/`; it also needs Poppler or ImageMagick. See [contributing](../CONTRIBUTING.md) before changing published files.

## Rebuild while editing

In a clone, start a watcher for the template you are editing:

```bash
make watch-new-grad
```

Open `build/new-grad/new-grad-resume.pdf` in your PDF reader. Saving the template, `resume.cls`, or an included content file rebuilds that PDF. The watcher stays running after a compile error; fix the source and save again. Press **Ctrl+C** to stop it.

Other targets: `watch-no-internship`, `watch-experienced`, `watch-ai-engineer`, `watch-ml-engineer`, and `watch-graduate-admissions`. Each writes to its own folder under `build/`. These commands do not refresh the published downloads or open a PDF reader automatically.

Inside an extracted starter, use `latexmk` directly with the bundled `latexmkrc`:

```bash
latexmk -pvc -view=none resume.tex
```

Output: `resume.pdf`. If your PDF reader does not reload changed files, reopen the PDF after each successful build.

## PDF checker dependencies

The [terminal checker](../tests/README.md#check-your-own-resume) needs Python 3.9+ and Poppler's `pdftotext` on `PATH`. No pip packages.

- macOS: `brew install python poppler`
- Ubuntu/Debian: `sudo apt install python3 poppler-utils`
- Windows: install Python and Poppler, add Poppler's `bin` directory to `PATH`, and use `py -3` instead of `python3`.

To check an exported PDF against an application's page and file-size limits:

```bash
python3 scripts/check_resume.py "path/to/your-resume.pdf" --max-pages 1 --max-size-mb 2
```

Both flags are optional. File size uses decimal MB (1 MB = 1,000,000 bytes). The checker also checks for empty text pages and extraction errors; it does not change the PDF.

[Back to the README](../README.md#build-locally)
