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
- Build the standalone binary: `poetry run python build_exe.py` → `dist/rmc` (PyInstaller,
  one-file). This is what the `Build rmc Binaries` workflow (`generate_bins.yml`) and the
  downstream Avalonia sync-app build (`rmc_ref` = branch/SHA of `phuertay/rmc`) run to produce
  `rmc-linux-x64` / `rmc-x64.exe` / `rmc-macos`. `dist/` and `build/` are gitignored.

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
- **The PyInstaller `dist/rmc` binary errors on `--version`** (`RuntimeError: 'rmc' is not
  installed`) because the frozen build ships no package dist-metadata for `click`'s
  `version_option`. Conversions (`-t svg|markdown|pdf|inkml`) — what the sync app invokes —
  work fine. Pre-existing packaging quirk, not an env problem.
- `pyproject.toml` lists `PySimpleGUI` but the GUI actually uses stdlib Tkinter.
- Poetry is installed via pipx (`~/.local/bin/poetry`, symlinked into `/usr/local/bin`).
  The virtualenv lives under `~/.cache/pypoetry/virtualenvs/`.

### Token-efficiency stack (ponytail + caveman ultra + token-savior)

Always-on Cursor rules live in `.cursor/rules/` (`caveman-ultra.mdc`, `ponytail.mdc`,
`token-saviour.mdc`). Skills live in `.agents/skills/` (installed via `npx skills add`).

| Layer | Tool | Verify | Notes |
|-------|------|--------|-------|
| Prose output | **caveman ultra** | skill + always-on rule | Always-on at ultra intensity |
| Code output | **ponytail** | skill + always-on rule | Default mode `ultra` via `~/.config/ponytail/config.json` / `PONYTAIL_DEFAULT_MODE` |
| Routing playbook | **token-saviour** skill | `.agents/skills/token-saviour/` | Routes tasks to the tools below |
| Code-read input | **serena** + **token-savior** CLI/MCP | `serena -V`, `ts get <symbol>` | Serena project at `.serena/`; MCP in `.cursor/mcp.json` |
| Command-output input | **rtk** | `rtk --version`, `rtk git status` | Cursor hook in `~/.cursor/hooks.json` |

Runtime binaries (snapshot-managed, not in the Poetry update script):
- `serena` via `uv tool install -p 3.12 serena-agent` → `~/.local/bin/serena`
- `rtk` via `cargo install --git https://github.com/rtk-ai/rtk` → `/usr/local/cargo/bin/rtk`
- `token-savior` / `ts` via `pip install "token-savior-recall[mcp,memory-vector]"` in
  `~/.local/token-savior-venv` (symlinked into `/usr/local/bin`)

Prefer `ts get` / `ts search` / `ts ctx` (or serena MCP) over reading whole files for symbols;
prefer `rtk <cmd>` for noisy shell output. Announce once:
`🪙 token-saviour: serena + rtk + caveman ultra + ponytail`.
