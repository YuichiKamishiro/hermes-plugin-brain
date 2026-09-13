"""Hermes plugin: inject top-5 brain anchors into the current user message.

Retrieval is delegated to $HERMES_HOME/brain/bin/brain (stdlib CLI) imported as
a module, so the plugin and the CLI share one implementation.

Bootstrap: brain's *data* directory ($HERMES_HOME/brain — bin/brain, SCHEMA.md,
empty domains/decisions/lessons/projects/pages/journals dirs, brain.db) lives
outside this plugin's own directory (plugins live in $HERMES_HOME/plugins/<name>
and get replaced wholesale on `hermes plugins update`; the knowledge graph must
survive that). On first load, if $HERMES_HOME/brain is missing, this plugin
copies its bundled `_bootstrap/` payload there once. Existing data is never
overwritten.
"""
from __future__ import annotations

import importlib.util
import logging
import os
import re
import shutil
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

_PLUGIN_DIR = Path(__file__).resolve().parent
_HERMES_HOME = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
_BRAIN_HOME = Path(os.environ.get("BRAIN_HOME") or _HERMES_HOME / "brain")
_CLI = _BRAIN_HOME / "bin" / "brain"
_BOOTSTRAP_SRC = _PLUGIN_DIR / "_bootstrap"

_TRIVIAL = re.compile(r"^\s*(ok|okay|ок|окей|да|нет|yes|no|thanks|спасибо|k|\+|👍)[.!\s]*$", re.I)


def _bootstrap_brain_home() -> None:
    """Seed $HERMES_HOME/brain from the plugin's bundled template, once.

    Idempotent and non-destructive: only creates paths that don't exist yet.
    """
    if not _BOOTSTRAP_SRC.is_dir():
        return
    try:
        _BRAIN_HOME.mkdir(parents=True, exist_ok=True)
        for item in _BOOTSTRAP_SRC.iterdir():
            dest = _BRAIN_HOME / item.name
            if dest.exists():
                continue
            if item.is_dir():
                shutil.copytree(item, dest)
            else:
                shutil.copy2(item, dest)
        bin_path = _BRAIN_HOME / "bin" / "brain"
        if bin_path.exists():
            bin_path.chmod(0o755)
    except Exception as exc:  # pragma: no cover
        log.warning("brain: bootstrap of %s failed: %s", _BRAIN_HOME, exc)


def _load_cli():
    # file has no .py suffix -> importlib picks no loader; force SourceFileLoader
    from importlib.machinery import SourceFileLoader
    loader = SourceFileLoader("brain_cli", str(_CLI))
    spec = importlib.util.spec_from_loader("brain_cli", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


_bootstrap_brain_home()

_cli = None
try:
    _cli = _load_cli()
except Exception as exc:  # pragma: no cover
    log.warning("brain: CLI import failed: %s", exc)


def _pre_llm_call(user_message: str = "", **_: Any) -> dict[str, str] | None:
    if _cli is None or not user_message or _TRIVIAL.match(user_message) or len(user_message) < 12:
        return None
    try:
        text = _cli.render(_cli.search(user_message))
    except Exception as exc:
        log.debug("brain: search failed: %s", exc)
        return None
    return {"context": text} if text else None


def _cmd_brain(raw_args: str) -> str:
    """/brain <subcommand...> — thin wrapper over the CLI (non-interactive only)."""
    import subprocess
    args = (raw_args or "").split()
    if not args or args[0] == "review":
        return f"Use terminal: {_CLI} review  (interactive)"
    r = subprocess.run([str(_CLI), *args], capture_output=True, text=True)
    return (r.stdout + r.stderr).strip() or f"exit {r.returncode}"


def register(ctx: Any) -> None:
    ctx.register_hook("pre_llm_call", _pre_llm_call)
    ctx.register_command("brain", _cmd_brain, description="brain index|search|add|inbox|lint|new", args_hint="<subcommand> [args]")
