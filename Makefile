
install: build
	uv sync
	uv tool install --force dist/smc_explorer-*.whl

uninstall:
	uv tool uninstall smc_explorer

build: clean
	uv build

clean:
	- rm -rf dist .venv

tests:
	uv run pytest tests

.PHONY: install build clean tests
