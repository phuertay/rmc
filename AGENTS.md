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
- `convert_test_files.sh` uses `set -euo pipefail`; it now converts all fixtures cleanly
  (including `tests/rm/test_v_3_18.rm`). Unknown pen color ids fall back to black with a
  warning instead of aborting (`RM_PALETTE.get(...)` in `src/rmc/exporters/writing_tools.py`).
- `pyproject.toml` lists `PySimpleGUI` but the GUI actually uses stdlib Tkinter.
- Poetry is installed via pipx (`~/.local/bin/poetry`, symlinked into `/usr/local/bin`).
  The virtualenv lives under `~/.cache/pypoetry/virtualenvs/`.

### OneNote ink/text scale calibration
Local RM/SVG checks cannot prove OneNote’s himetric vs CSS px mapping. Use the
self-describing calib page (ink crosses + letters **O**=our `/10` CSS, **H**=true
himetric CSS):

```bash
poetry run python tests/onenote_calib/generate_calib_page.py
poetry run python tests/onenote_calib/check_generate.py
# needs Graph token + section id (never commit tokens):
export ONENOTE_TOKEN=… ONENOTE_SECTION=…
poetry run python tests/onenote_calib/upload_and_fit.py --upload
# open the page → see whether O or H sits on each cross, then:
poetry run python tests/onenote_calib/upload_and_fit.py --apply ours   # or true_himetric
```

That writes `tests/onenote_calib/out/fit_result.json` with the mapping to put in
`inmkl.py`. Readback alone cannot reveal visual pixels (OneNote stores ink as
himetric and HTML as CSS); the O-vs-H page is the experiment.

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
