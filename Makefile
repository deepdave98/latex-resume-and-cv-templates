.PHONY: all no-internship new-grad experienced preview downloads test test-unit test-pdf-text test-personal-pdf test-downloads test-starters test-placeholders test-layout test-page-limits test-contacts clean
.PHONY: application-versions application-download preview-application-versions test-application-versions clean-application-versions
.PHONY: ai-engineer ml-engineer preview-ai-ml test-ai-ml
.PHONY: graduate-admissions preview-graduate-admissions test-graduate-admissions

LATEXMK := latexmk
PYTHON := python3
BUILD_DIR := build
PREVIEW_DIR := preview
OUTPUT_DIR := output/pdf
NO_INTERNSHIP_SOURCE := templates/no-internship-resume.tex
NEW_GRAD_SOURCE := templates/new-grad-resume.tex
EXPERIENCED_SOURCE := templates/experienced-resume.tex
NEW_GRAD_BUILD_DIR := $(BUILD_DIR)/new-grad
NO_INTERNSHIP_BUILD_DIR := $(BUILD_DIR)/no-internship
EXPERIENCED_BUILD_DIR := $(BUILD_DIR)/experienced

all: no-internship new-grad experienced ai-engineer ml-engineer graduate-admissions

ai-engineer ml-engineer graduate-admissions:
	@mkdir -p "$(BUILD_DIR)/$@"
	$(LATEXMK) -xelatex -interaction=nonstopmode -halt-on-error -file-line-error -outdir="$(BUILD_DIR)/$@" "templates/$@-resume.tex"

no-internship:
	@mkdir -p "$(NO_INTERNSHIP_BUILD_DIR)"
	$(LATEXMK) -xelatex -interaction=nonstopmode -halt-on-error -file-line-error -outdir="$(NO_INTERNSHIP_BUILD_DIR)" "$(NO_INTERNSHIP_SOURCE)"

new-grad:
	@mkdir -p "$(NEW_GRAD_BUILD_DIR)"
	$(LATEXMK) -xelatex -interaction=nonstopmode -halt-on-error -file-line-error -outdir="$(NEW_GRAD_BUILD_DIR)" "$(NEW_GRAD_SOURCE)"

experienced:
	@mkdir -p "$(EXPERIENCED_BUILD_DIR)"
	$(LATEXMK) -xelatex -interaction=nonstopmode -halt-on-error -file-line-error -outdir="$(EXPERIENCED_BUILD_DIR)" "$(EXPERIENCED_SOURCE)"

downloads:
	$(PYTHON) scripts/package_templates.py
	$(PYTHON) scripts/package_application_versions.py

test: test-unit test-pdf-text test-personal-pdf test-downloads test-starters test-placeholders test-layout test-page-limits test-contacts test-application-versions test-ai-ml test-graduate-admissions

test-unit:
	$(PYTHON) -m unittest discover -s tests -p 'test_*.py'

test-pdf-text: all
	$(PYTHON) tests/check_pdf_text.py --no-internship "$(NO_INTERNSHIP_BUILD_DIR)/no-internship-resume.pdf" --new-grad "$(NEW_GRAD_BUILD_DIR)/new-grad-resume.pdf" --experienced "$(EXPERIENCED_BUILD_DIR)/experienced-resume.pdf" --ai-engineer "$(BUILD_DIR)/ai-engineer/ai-engineer-resume.pdf" --ml-engineer "$(BUILD_DIR)/ml-engineer/ml-engineer-resume.pdf" --graduate-admissions "$(BUILD_DIR)/graduate-admissions/graduate-admissions-resume.pdf"
	$(PYTHON) tests/check_pdf_text.py --no-internship "$(OUTPUT_DIR)/no-internship-resume.pdf" --new-grad "$(OUTPUT_DIR)/new-grad-resume.pdf" --experienced "$(OUTPUT_DIR)/experienced-resume.pdf" --ai-engineer "$(OUTPUT_DIR)/ai-engineer-resume.pdf" --ml-engineer "$(OUTPUT_DIR)/ml-engineer-resume.pdf" --graduate-admissions "$(OUTPUT_DIR)/graduate-admissions-resume.pdf"

test-personal-pdf:
	$(PYTHON) scripts/check_resume.py output/pdf/no-internship-resume.pdf --max-pages 1
	$(PYTHON) scripts/check_resume.py output/pdf/new-grad-resume.pdf --max-pages 1
	$(PYTHON) scripts/check_resume.py output/pdf/experienced-resume.pdf --max-pages 2
	$(PYTHON) scripts/check_resume.py output/pdf/ai-engineer-resume.pdf --max-pages 1
	$(PYTHON) scripts/check_resume.py output/pdf/ml-engineer-resume.pdf --max-pages 1
	$(PYTHON) scripts/check_resume.py output/pdf/graduate-admissions-resume.pdf --max-pages 1

test-downloads:
	$(PYTHON) scripts/package_templates.py --check

test-starters: test-downloads
	$(PYTHON) tests/check_starter_builds.py

test-placeholders:
	$(PYTHON) tests/check_placeholders.py

test-layout:
	$(PYTHON) tests/check_layout.py

test-page-limits:
	$(PYTHON) tests/check_page_limits.py

test-contacts:
	$(PYTHON) tests/check_contacts.py

test-ai-ml:
	$(PYTHON) tests/check_ai_ml.py

test-graduate-admissions:
	$(PYTHON) tests/check_graduate_admissions.py

preview-graduate-admissions: graduate-admissions
	@mkdir -p "$(PREVIEW_DIR)" "$(OUTPUT_DIR)"
	cp "$(BUILD_DIR)/graduate-admissions/graduate-admissions-resume.pdf" "$(OUTPUT_DIR)/graduate-admissions-resume.pdf"
	@if command -v pdftoppm >/dev/null 2>&1; then \
		pdftoppm -png -singlefile -f 1 -l 1 -r 180 "$(OUTPUT_DIR)/graduate-admissions-resume.pdf" "$(PREVIEW_DIR)/graduate-admissions-resume"; \
	elif command -v magick >/dev/null 2>&1; then \
		magick -density 180 "$(OUTPUT_DIR)/graduate-admissions-resume.pdf[0]" -background white -alpha remove -strip "$(PREVIEW_DIR)/graduate-admissions-resume.png"; \
	else \
		echo "Install Poppler or ImageMagick to generate the PNG previews."; exit 1; \
	fi

preview-ai-ml: ai-engineer ml-engineer
	@mkdir -p "$(PREVIEW_DIR)" "$(OUTPUT_DIR)"
	@for role in ai-engineer ml-engineer; do \
		cp "$(BUILD_DIR)/$$role/$$role-resume.pdf" "$(OUTPUT_DIR)/$$role-resume.pdf" || exit 1; \
		if command -v pdftoppm >/dev/null 2>&1; then \
			pdftoppm -png -singlefile -f 1 -l 1 -r 180 "$(BUILD_DIR)/$$role/$$role-resume.pdf" "$(PREVIEW_DIR)/$$role-resume" || exit 1; \
		elif command -v magick >/dev/null 2>&1; then \
			magick -density 180 "$(BUILD_DIR)/$$role/$$role-resume.pdf[0]" -background white -alpha remove -strip "$(PREVIEW_DIR)/$$role-resume.png" || exit 1; \
		else \
			echo "Install Poppler or ImageMagick to generate the PNG previews."; exit 1; \
		fi; \
	done

# Optional project: leave the default templates and their build targets alone.
application-versions:
	@mkdir -p "$(BUILD_DIR)/application-versions"
	@version_build_dir="$$(cd "$(BUILD_DIR)/application-versions" && pwd)" && \
		cd examples/application-versions && $(LATEXMK) -xelatex -interaction=nonstopmode -halt-on-error -file-line-error -outdir="$$version_build_dir" backend.tex frontend.tex infrastructure.tex

application-download:
	$(PYTHON) scripts/package_application_versions.py

test-application-versions:
	$(PYTHON) scripts/package_application_versions.py --check
	$(PYTHON) tests/check_application_versions.py
	$(PYTHON) tests/check_application_versions.py --published

preview-application-versions: application-versions
	@mkdir -p "$(PREVIEW_DIR)" "$(OUTPUT_DIR)"
	@for version in backend frontend infrastructure; do \
		cp "$(BUILD_DIR)/application-versions/$$version.pdf" "$(OUTPUT_DIR)/application-$$version.pdf" || exit 1; \
		if command -v pdftoppm >/dev/null 2>&1; then \
			pdftoppm -png -singlefile -f 1 -l 1 -r 180 "$(BUILD_DIR)/application-versions/$$version.pdf" "$(PREVIEW_DIR)/application-$$version" || exit 1; \
		elif command -v magick >/dev/null 2>&1; then \
			magick -density 180 "$(BUILD_DIR)/application-versions/$$version.pdf[0]" -background white -alpha remove -strip "$(PREVIEW_DIR)/application-$$version.png" || exit 1; \
		else \
			echo "Install Poppler or ImageMagick to generate the PNG previews."; \
			exit 1; \
		fi; \
	done

clean-application-versions:
	@if test -d "$(BUILD_DIR)/application-versions"; then \
		version_build_dir="$$(cd "$(BUILD_DIR)/application-versions" && pwd)" && \
		cd examples/application-versions && $(LATEXMK) -C -outdir="$$version_build_dir" backend.tex frontend.tex infrastructure.tex; \
	fi

preview: all preview-ai-ml preview-graduate-admissions
	@mkdir -p "$(PREVIEW_DIR)" "$(OUTPUT_DIR)"
	cp "$(NO_INTERNSHIP_BUILD_DIR)/no-internship-resume.pdf" "$(OUTPUT_DIR)/no-internship-resume.pdf"
	cp "$(NEW_GRAD_BUILD_DIR)/new-grad-resume.pdf" "$(OUTPUT_DIR)/new-grad-resume.pdf"
	cp "$(EXPERIENCED_BUILD_DIR)/experienced-resume.pdf" "$(OUTPUT_DIR)/experienced-resume.pdf"
	@if command -v pdftoppm >/dev/null 2>&1; then \
		pdftoppm -png -singlefile -f 1 -l 1 -r 180 "$(NO_INTERNSHIP_BUILD_DIR)/no-internship-resume.pdf" "$(PREVIEW_DIR)/no-internship-resume"; \
		pdftoppm -png -singlefile -f 1 -l 1 -r 180 "$(NEW_GRAD_BUILD_DIR)/new-grad-resume.pdf" "$(PREVIEW_DIR)/new-grad-resume"; \
		pdftoppm -png -singlefile -f 1 -l 1 -r 180 "$(EXPERIENCED_BUILD_DIR)/experienced-resume.pdf" "$(PREVIEW_DIR)/experienced-resume-page-1"; \
		pdftoppm -png -singlefile -f 2 -l 2 -r 180 "$(EXPERIENCED_BUILD_DIR)/experienced-resume.pdf" "$(PREVIEW_DIR)/experienced-resume-page-2"; \
	elif command -v magick >/dev/null 2>&1; then \
		magick -density 180 "$(NO_INTERNSHIP_BUILD_DIR)/no-internship-resume.pdf[0]" -background white -alpha remove -strip "$(PREVIEW_DIR)/no-internship-resume.png"; \
		magick -density 180 "$(NEW_GRAD_BUILD_DIR)/new-grad-resume.pdf[0]" -background white -alpha remove -strip "$(PREVIEW_DIR)/new-grad-resume.png"; \
		magick -density 180 "$(EXPERIENCED_BUILD_DIR)/experienced-resume.pdf[0]" -background white -alpha remove -strip "$(PREVIEW_DIR)/experienced-resume-page-1.png"; \
		magick -density 180 "$(EXPERIENCED_BUILD_DIR)/experienced-resume.pdf[1]" -background white -alpha remove -strip "$(PREVIEW_DIR)/experienced-resume-page-2.png"; \
	else \
		echo "Install Poppler or ImageMagick to generate the PNG previews."; \
		exit 1; \
	fi

clean:
	$(LATEXMK) -C -outdir="$(NO_INTERNSHIP_BUILD_DIR)" "$(NO_INTERNSHIP_SOURCE)"
	$(LATEXMK) -C -outdir="$(NEW_GRAD_BUILD_DIR)" "$(NEW_GRAD_SOURCE)"
	$(LATEXMK) -C -outdir="$(EXPERIENCED_BUILD_DIR)" "$(EXPERIENCED_SOURCE)"
	$(LATEXMK) -C -outdir="$(BUILD_DIR)/ai-engineer" templates/ai-engineer-resume.tex
	$(LATEXMK) -C -outdir="$(BUILD_DIR)/ml-engineer" templates/ml-engineer-resume.tex
	$(LATEXMK) -C -outdir="$(BUILD_DIR)/graduate-admissions" templates/graduate-admissions-resume.tex
