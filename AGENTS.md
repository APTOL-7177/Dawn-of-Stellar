# Repository Guidelines

## Project Structure & Module Organization
- `src/`: Core gameplay modules (`core`, `combat`, `character`, `world`, `ai`, `ui`, `multiplayer`, `systems`, `tutorial`, `bot`, etc.). Keep cross-module imports lean; prefer injecting dependencies through `core` helpers.
- `data/`: Authoritative YAML/JSON game data (`skills/`, `characters/`, `teamwork_skills.yaml`, `tutorials/`). Preserve IDs and ordering to avoid save incompatibilities.
- `assets/`: Fonts/audio; avoid committing large new binaries without need. `config/` holds input/vibration/meta settings. `scripts/` contains balancing/validation utilities. `tests/` is the pytest suite; `web/` hosts the experimental browser build. `docs/`, `examples/`, and `user_data/` (local saves) should stay uncommitted.

## Build, Test, and Development Commands
- Install: `pip install -e .[dev]` for full tooling, or `pip install -r requirements.txt` for runtime-only.
- Run game: `python main.py` (add `--dev` to unlock all jobs, `--debug --log=DEBUG` for verbose logs).
- Package: `./build_final_linux.sh` or `build_final.bat` to produce platform builds; Windows installer scripts live in `build_installer.bat` / `install*.nsi`.
- Lint/format: `black src tests` and `isort src tests`. Static/type checks: `pylint src` and `mypy src`.

## Coding Style & Naming Conventions
- Python 3.10+, 4-space indent, 100-char lines (Black/isort/pylint configs). Prefer explicit return/argument types; new functions should be fully type-hinted to satisfy mypy.
- Naming: snake_case for functions/vars, PascalCase for classes. Domain shorthands (`hp`, `mp`, `atb`, `brv`) are accepted. Keep YAML keys lowercase snake_case and skill/job IDs unique and stable.
- Docstrings are encouraged for complex systems; keep comments focused on intent, not restating code.

## Testing Guidelines
- Pytest with strict markers; default addopts are `-ra -q --strict-markers`. Common commands:
  - Full suite: `pytest tests`
  - Fast cycle: `pytest tests -m "not slow"`
  - Coverage: `pytest tests --cov=src --cov-report=term-missing`
- Integration-heavy areas have dedicated files (e.g., `tests/test_multiplayer_*.py`, teamwork suites). Use `run_multiplayer_tests.py` when validating multiplayer changes end-to-end.

## Commit & Pull Request Guidelines
- Follow the Conventional Commit style seen in history (`feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`). Keep subjects short, present tense; English or Korean is fine if consistent.
- Before opening a PR: describe the change and motivation, list test commands run, call out data/asset impacts, and attach screenshots or logs for gameplay/UI adjustments. Link related issues and keep diffs focused (avoid committing `dist/` outputs or local `user_data/` saves).
