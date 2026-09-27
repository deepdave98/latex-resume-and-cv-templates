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
git clone https://github.com/deepdave98/swe-resume-templates.git
cd swe-resume-templates
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

## PDF checker dependencies

The [terminal checker](../tests/README.md#check-your-own-resume) needs Python 3.9+ and Poppler's `pdftotext` on `PATH`. No pip packages.

- macOS: `brew install python poppler`
- Ubuntu/Debian: `sudo apt install python3 poppler-utils`
- Windows: install Python and Poppler, add Poppler's `bin` directory to `PATH`, and use `py -3` instead of `python3`.

[Back to the README](../README.md#build-locally)
