NAME = main.py
RUN  = uv run

all: run

install:
	uv sync

run:
	$(RUN) $(NAME)

debug:
	$(RUN) -m pdb $(NAME)

clean:
	rm -rf __pycache__ */__pycache__ */*/__pycache__ .mypy_cache dist .ruff_cache

lint:
	$(RUN) flake8 . --exclude .venv
	$(RUN) mypy . --warn-return-any --warn-unused-ignores --ignore-missing-imports --disallow-untyped-defs --check-untyped-defs

format:
	$(RUN) ruff format .

.PHONY: install run debug clean lint format
