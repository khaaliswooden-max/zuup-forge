.PHONY: install dev test lint compile seed demo generate smoke clean

install:
	pip install -e ".[dev]" --break-system-packages

test:
	pytest tests/ -v --tb=short

lint:
	ruff check forge/ tests/
	black --check forge/ tests/ 2>/dev/null || true
	mypy -p forge --ignore-missing-imports 2>/dev/null || true

compile:
	forge compile specs/aureon.platform.yaml

seed: compile
	@if [ -n "$$SAM_GOV_API_KEY" ]; then python scripts/seed_sam_gov.py; else echo "Set SAM_GOV_API_KEY for real SAM.gov data"; fi

demo: compile seed
	cd platforms/aureon && uvicorn app:app --reload --port 8000

generate:
	forge generate

generate-aureon:
	forge init aureon --from specs/aureon.platform.yaml

dev:
	forge dev aureon

smoke: install compile test
	@echo "✓ Smoke test passed"

clean:
	rm -rf platforms/ *.db test_output/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
