#!/usr/bin/env python3
"""Install Superlearn into OpenAI Codex and/or Kilo (formerly Kilo Code).

Claude Code needs no installer — use the plugin marketplace or
`claude --plugin-dir /path/to/superlearn`. For the other tools this script
copies the portable Agent Skill (and the researcher sub-agent + slash
command) into their global config directories, stamping this clone's
absolute path into the files so the bundled scripts are always found.

Stdlib only. Re-run after moving the clone. `--uninstall` removes
everything it installed.

  python3 scripts/install.py --codex
  python3 scripts/install.py --kilocode
  python3 scripts/install.py --codex --kilocode --dry-run
"""

from __future__ import annotations

import argparse
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
PLACEHOLDER = "{{SUPERLEARN_ROOT}}"

SKILL_SRC = ROOT / ".agents" / "skills" / "superlearn" / "SKILL.md"
CODEX_AGENT_SRC = ROOT / ".codex" / "agents" / "superlearn-researcher.toml"
KILO_COMMAND_SRC = ROOT / ".kilo" / "commands" / "superlearn.md"
KILO_AGENT_SRC = ROOT / ".kilo" / "agents" / "superlearn-researcher.md"


def plan(home: pathlib.Path, config: pathlib.Path, codex: bool, kilocode: bool):
    """(source, destination) pairs for the requested tools."""
    pairs = []
    if codex:
        # Codex discovers user skills in ~/.agents/skills/ and personal
        # sub-agent roles in ~/.codex/agents/.
        pairs.append((SKILL_SRC, home / ".agents" / "skills" / "superlearn" / "SKILL.md"))
        pairs.append((CODEX_AGENT_SRC, home / ".codex" / "agents" / "superlearn-researcher.toml"))
    if kilocode:
        # Kilo discovers global skills in ~/.kilo/skills/ and global
        # commands/agents under its config dir (~/.config/kilo by default).
        pairs.append((SKILL_SRC, home / ".kilo" / "skills" / "superlearn" / "SKILL.md"))
        pairs.append((KILO_COMMAND_SRC, config / "kilo" / "commands" / "superlearn.md"))
        pairs.append((KILO_AGENT_SRC, config / "kilo" / "agents" / "superlearn-researcher.md"))
    return pairs


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--codex", action="store_true", help="install for OpenAI Codex")
    ap.add_argument("--kilocode", "--kilo", action="store_true", dest="kilocode",
                    help="install for Kilo (formerly Kilo Code)")
    ap.add_argument("--home", type=pathlib.Path, default=None,
                    help="install under this directory instead of $HOME (mainly for tests)")
    ap.add_argument("--dry-run", action="store_true", help="print what would be written, write nothing")
    ap.add_argument("--uninstall", action="store_true", help="remove previously installed files")
    args = ap.parse_args(argv)

    if not (args.codex or args.kilocode):
        ap.error("pick at least one of --codex / --kilocode")

    home = (args.home or pathlib.Path.home()).resolve()
    if args.home is None and os.environ.get("XDG_CONFIG_HOME"):
        config = pathlib.Path(os.environ["XDG_CONFIG_HOME"]).resolve()
    else:
        config = home / ".config"

    for src, dest in plan(home, config, args.codex, args.kilocode):
        if args.uninstall:
            print(("would remove " if args.dry_run else "removed ") + str(dest))
            if not args.dry_run and dest.exists():
                dest.unlink()
                if dest.parent.name == "superlearn" and not any(dest.parent.iterdir()):
                    dest.parent.rmdir()
            continue
        content = src.read_text(encoding="utf-8").replace(PLACEHOLDER, str(ROOT))
        print(("would write " if args.dry_run else "wrote ") + str(dest))
        if not args.dry_run:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(content, encoding="utf-8")

    if not args.uninstall and not args.dry_run:
        print()
        if args.codex:
            print("Codex: invoke with `$superlearn <topic>` (or just ask to learn something).")
            print("  The scrapers and the localhost app need real network access:")
            print("    # ~/.codex/config.toml")
            print("    [sandbox_workspace_write]")
            print("    network_access = true")
        if args.kilocode:
            print("Kilo: invoke with `/superlearn <topic>` in the CLI or VS Code.")
            print("  Using a non-Kilo model provider? Enable Web Search in Settings -> Web Tools")
            print('  (or set "web_search": true in kilo.jsonc) so websearch works.')
        print("Moved the clone? Re-run this installer to restamp the paths.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
