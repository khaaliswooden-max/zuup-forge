.PHONY: install dev test lint generate smoke clean

install:
	pip install -e ".[dev]" --break-system-packages

generate:
	forge generate

generate-aureon:
	forge init aureon --from specs/aureon.platform.yaml

dev:
	forge dev aureon

test:
	pytest tests/ -v

lint:
	ruff check forge/ tests/
	mypy forge/

smoke:
	python -c "from forge.compiler.parser import load_spec; s = load_spec('specs/aureon.platform.yaml'); print(f'✓ Parsed: {s.platform.display_name} — {len(s.entities)} entities, {len(s.api.routes)} routes')"
	forge init aureon --from specs/aureon.platform.yaml
	ls platforms/aureon/
	@echo "✓ Smoke passed"

clean:
	rm -rf platforms/ *.db __pycache__ .pytest_cache
