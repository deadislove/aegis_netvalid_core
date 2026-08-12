# Contributing to Aegis NetValid Core

Thanks for considering a contribution. This project is still early — expect rough edges, and please open an issue before a large PR so we can agree on direction first.

## Setup

```bash
git clone https://github.com/da-weilin/Aegis_NetValid_Core.git
cd Aegis_NetValid_Core
python3 -m venv venv
source venv/bin/activate
pip install -e .
pip install pytest ruff
```

Use `-e` (editable install) — otherwise `aegis` runs a stale copy instead of your working tree. See [docs/troubleshooting.md](docs/troubleshooting.md#5-sudo-aegis-doesnt-reflect-code-changes-you-just-made) if that bites you.

Try your changes without root, hardware, or `iperf3` using demo mode:
```bash
python main_aegis.py --demo
```

## Before opening a PR

```bash
pytest -q
ruff check .
```

Both must pass. If you're touching an engine, add or update tests under `tests/` — see [docs/engine_development.md](docs/engine_development.md) for the engine interface, and existing files like `tests/test_stresser_engine.py` for the mocking patterns used in this codebase.

If your change is user-visible (a new dashboard field, a CLI command, a config key), update [docs/user_guide.md](docs/user_guide.md) in the same PR — this repo has a history of docs drifting from the actual code, and we're trying to stop that.

## Code style

- No `shell=True` in `subprocess` calls — use argument lists (see `lib/os_helpers.py`).
- Match the existing engine interface: `__init__(self, core, config)`, `start()`, `stop()`, `get_report()`. See [docs/engine_development.md](docs/engine_development.md).
- Keep comments to the non-obvious "why," not a restatement of the code.
- `ruff check .` is the only enforced linter for now (see `pyproject.toml` for the enabled rule set).

## Reporting bugs / security issues

Regular bugs: open a GitHub issue. Security-relevant issues (the kind that shouldn't be public until fixed): see [SECURITY.md](SECURITY.md).
