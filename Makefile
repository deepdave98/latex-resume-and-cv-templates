.DEFAULT_GOAL := all

LATEXMK := latexmk
PYTHON := python3
BUILD_DIR := build
PREVIEW_DIR := preview
OUTPUT_DIR := output/pdf
TEMPLATES := no-internship new-grad experienced ai-engineer ml-engineer graduate-admissions
APPLICATION_VERSIONS := resume backend

.PHONY: all $(TEMPLATES) preview $(addprefix preview-,$(TEMPLATES)) preview-ai-ml downloads clean
.PHONY: test test-unit test-pdf-text test-personal-pdf test-downloads test-starters test-placeholders test-layout test-page-limits test-contacts test-ai-ml test-graduate-admissions
.PHONY: application-versions application-download preview-application-versions test-application-versions clean-application-versions

all: $(TEMPLATES)

$(TEMPLATES):
	@mkdir -p "$(BUILD_DIR)/$@"
	$(LATEXMK) -xelatex -interaction=nonstopmode -halt-on-error -file-line-error -outdir="$(BUILD_DIR)/$@" "templates/$@-resume.tex"

downloads:
	$(PYTHON) scripts/package_templates.py
	$(PYTHON) scripts/package_application_versions.py

test: test-unit test-pdf-text test-personal-pdf test-downloads test-starters test-placeholders test-layout test-page-limits test-contacts test-application-versions test-ai-ml test-graduate-admissions

test-unit:
	$(PYTHON) -m unittest discover -s tests -p 'test_*.py'

test-pdf-text: all
	$(PYTHON) tests/check_pdf_text.py $(foreach template,$(TEMPLATES),--$(template) "$(BUILD_DIR)/$(template)/$(template)-resume.pdf")
	$(PYTHON) tests/check_pdf_text.py $(foreach template,$(TEMPLATES),--$(template) "$(OUTPUT_DIR)/$(template)-resume.pdf")

test-personal-pdf:
	@for template in $(TEMPLATES); do \
		$(PYTHON) scripts/check_resume.py "$(OUTPUT_DIR)/$$template-resume.pdf" --max-pages 1 || exit 1; \
	done

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

preview: $(addprefix preview-,$(TEMPLATES))

preview-ai-ml: preview-ai-engineer preview-ml-engineer

$(addprefix preview-,$(TEMPLATES)): preview-%: %
	@mkdir -p "$(PREVIEW_DIR)" "$(OUTPUT_DIR)"
	cp "$(BUILD_DIR)/$*/$*-resume.pdf" "$(OUTPUT_DIR)/$*-resume.pdf"
	@if command -v pdftoppm >/dev/null 2>&1; then \
		pdftoppm -png -singlefile -f 1 -l 1 -r 180 "$(OUTPUT_DIR)/$*-resume.pdf" "$(PREVIEW_DIR)/$*-resume"; \
	elif command -v magick >/dev/null 2>&1; then \
		magick -density 180 "$(OUTPUT_DIR)/$*-resume.pdf[0]" -background white -alpha remove -strip "$(PREVIEW_DIR)/$*-resume.png"; \
	else \
		echo "Install Poppler or ImageMagick to generate the PNG previews."; exit 1; \
	fi

# Optional project: leave the default templates and their build targets alone.
application-versions:
	@mkdir -p "$(BUILD_DIR)/application-versions"
	@version_build_dir="$$(cd "$(BUILD_DIR)/application-versions" && pwd)" && \
		cd examples/application-versions && $(LATEXMK) -xelatex -interaction=nonstopmode -halt-on-error -file-line-error -outdir="$$version_build_dir" $(addsuffix .tex,$(APPLICATION_VERSIONS))

application-download:
	$(PYTHON) scripts/package_application_versions.py

test-application-versions:
	$(PYTHON) scripts/package_application_versions.py --check
	$(PYTHON) tests/check_application_versions.py
	$(PYTHON) tests/check_application_versions.py --published

preview-application-versions: application-versions
	@mkdir -p "$(PREVIEW_DIR)" "$(OUTPUT_DIR)"
	@for version in $(APPLICATION_VERSIONS); do \
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
		cd examples/application-versions && $(LATEXMK) -C -outdir="$$version_build_dir" $(addsuffix .tex,$(APPLICATION_VERSIONS)); \
	fi

clean:
	@for template in $(TEMPLATES); do \
		$(LATEXMK) -C -outdir="$(BUILD_DIR)/$$template" "templates/$$template-resume.tex" || exit 1; \
	done
