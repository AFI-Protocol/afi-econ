# AFI Econ Kit Makefile

.PHONY: help build build-dev test golden golden-ci demo clean install simulate audit

# Configuration
CONFIG_FILE := config.yaml
OUTPUT_DIR := out
AUDIT_DIR := out_audit

help:
	@echo "AFI Econ Kit Build System"
	@echo "Targets:"
	@echo "  build         - Build production Docker image (STRICT=1)"
	@echo "  build-dev     - Build development Docker image (STRICT=0)"
	@echo "  test          - Run all tests"
	@echo "  golden        - Run golden image tests (local mode - prints digest, assertion skipped)"
	@echo "  golden-ci     - Run golden image tests (CI enforcement mode - strict assertions)"
	@echo "  simulate      - Run economic simulation"
	@echo "  audit         - Run end-to-end audit for whitepaper readiness"
	@echo "  install       - Install package in development mode"
	@echo "  clean         - Remove output files"
	@echo "  spotless      - Remove all generated files"

# Build production Docker image
build:
	@echo "Building production Docker image (STRICT=1)..."
	docker buildx build --platform linux/amd64 --build-arg STRICT=1 -t afi-econ-kit:latest .

# Build development Docker image
build-dev:
	@echo "Building development Docker image (STRICT=0)..."
	docker buildx build --platform linux/amd64 --build-arg STRICT=0 -t afi-econ-kit:dev .

# Install package in development mode
install:
	@echo "Installing package in development mode..."
	pip install -e .[dev]

# Run all tests
test:
	@echo "Running tests..."
	pytest -q

# Run golden image tests (local mode - prints digest, assertion skipped)
golden:
	@echo "Running golden image tests (local mode)..."
	AFI_ECON_KIT_GOLDEN_TEST=1 pytest tests/test_gauge_shares_golden.py -v -s

# Run golden image tests with CI enforcement (strict mode)
golden-ci:
	@echo "Running golden image tests (CI enforcement mode)..."
	AFI_ECON_KIT_ENFORCE_GOLDEN=1 AFI_ECON_KIT_GOLDEN_TEST=1 MPLBACKEND=Agg TZ=UTC PYTHONHASHSEED=0 pytest tests/test_gauge_shares_golden.py -v

# Generate golden hash (for development)
regen-golden:
	@echo "Regenerating golden image hash..."
	AFI_ECON_KIT_REGEN_GOLDEN=1 AFI_ECON_KIT_GOLDEN_TEST=1 MPLBACKEND=Agg TZ=UTC PYTHONHASHSEED=0 pytest tests/test_gauge_shares_golden.py -v -s

# Run economic simulation
simulate:
	@echo "Running economic simulation..."
	python -m afi_econ_kit.cli simulate --config $(CONFIG_FILE) --outdir $(OUTPUT_DIR)
	@echo "Simulation complete. Check $(OUTPUT_DIR)/ for outputs."

# Run end-to-end audit for whitepaper readiness
# make audit OUT=out_audit_clean FRESH=1   # recreate outdir safely
audit:
	@echo "Running end-to-end audit..."
	python -B scripts/end_to_end_audit.py --out $(or $(OUT),$(AUDIT_DIR)) $(if $(FRESH),--fresh-outdir,)
	@echo "Audit complete. See $(or $(OUT),$(AUDIT_DIR))/AUDIT.md and $(or $(OUT),$(AUDIT_DIR))/audit_report.json"

# Clean output files
clean:
	@echo "Cleaning output files..."
	rm -rf $(OUTPUT_DIR) $(AUDIT_DIR) out_base out_with ci_test ci_sim perf_test

# Remove all generated files
spotless: clean
	@echo "Removing all generated files..."
	rm -rf .pytest_cache __pycache__ src/afi_econ_kit/__pycache__ tests/__pycache__
	rm -rf build dist *.egg-info
	rm -rf .venv .temp_venv
	find . -name "*.pyc" -delete
	find . -name "*.pyo" -delete
