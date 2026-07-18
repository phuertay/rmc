# AGENTS.md

## Cursor Cloud specific instructions

This repo is a single Python project (`rmc`) managed by **Poetry**, plus a secondary
Tkinter desktop app under `ui_onenote_client/`. There are no local servers, databases,
or Docker services.

### Services / deliverables
- **`rmc` CLI** (`src/rmc/`, entry point `rmc.cli:cli`): converts reMarkable v6 `.rm`
  files to `markdown`, `svg`, `pdf`, `inkml`, `blocks`, `tree` (and markdown -> `.rm`).
  This is the core product.
- **reMarkable -> OneNote Sync GUI** (`ui_onenote_client/main.py`): Tkinter app that
  wraps the CLI (`-t inkml`) and uploads pages to Microsoft OneNote via the Graph API.
  Requires a display and a user-supplied Microsoft Graph bearer token to do anything
  useful (upload). No token is stored in the repo.

### Running things (poetry is available on PATH)
- Lint: repo has no linter configured (no flake8/ruff/black config); the CI "test" is the
  conversion script below, not a linter.
- Tests / CI equivalent: `poetry run bash convert_test_files.sh` (writes to `test_output/`).
  This is exactly what `.github/workflows/test.yml` runs.
- Run the CLI: `poetry run rmc -t svg tests/rm/Bold_Heading_Bullet_Normal.rm -o out.svg`
  (also `markdown`, `pdf`, `inkml`). Sample `.rm` fixtures live in `tests/rm/`.
- Run the GUI: `cd ui_onenote_client && poetry run python main.py` (needs a display).

### Non-obvious gotchas
- **PDF export requires the `inkscape` CLI on PATH** (installed as a system package; not a
  Python dependency). Without it, `-t pdf` fails.
- **The GUI needs `python3-tk`** (system package; `tkinter` is not pip-installable). It also
  must be launched from inside `ui_onenote_client/` because it imports sibling modules
  (`config`, `graph_client`, `converter_wrapper`) by bare name.
- **`convert_test_files.sh` uses `set -euo pipefail`** and currently aborts on the fixture
  `tests/rm/test_v_3_18.rm`, which raises `KeyError: 9` in `RM_PALETTE`
  (`src/rmc/exporters/writing_tools.py`) — a pre-existing code limitation with a newer
  color id, NOT an environment problem. All other ~19 fixtures convert fine.
- **`rmc -t markdown` without `-o` (writing to stdout) crashes** with a `TypeError`
  (`Path(output)` on a stream) — pre-existing CLI bug; pass `-o <file>` to work around it.
- `pyproject.toml` lists `PySimpleGUI` but the GUI actually uses stdlib Tkinter.
- Poetry is installed via pipx (`~/.local/bin/poetry`, symlinked into `/usr/local/bin`).
  The virtualenv lives under `~/.cache/pypoetry/virtualenvs/`.
