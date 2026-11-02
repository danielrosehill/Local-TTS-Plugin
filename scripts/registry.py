#!/usr/bin/env python3
"""Local TTS registry: the plugin's memory of what is installed on this machine.

One JSON file records every installed engine (venv, model files, device, voices,
last smoke test), every cloned voice profile, and the defaults. Skills read it
before doing anything and write it after installing or cloning.

Location: $LOCAL_TTS_HOME/registry.json, default ~/.local/share/local-tts/.
stdlib only, so it runs under any python3 without an engine venv.

Usage:
  registry.py path                       print the data dir
  registry.py show                       whole registry as JSON
  registry.py get-engine NAME            one engine's record
  registry.py set-engine NAME JSON       create or merge an engine record
  registry.py remove-engine NAME
  registry.py set-default KEY VALUE      e.g. set-default engine kokoro
  registry.py add-voice NAME JSON        create or merge a cloned-voice profile
  registry.py remove-voice NAME
"""
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = 1


def home() -> Path:
    base = os.environ.get("LOCAL_TTS_HOME")
    if base:
        return Path(base).expanduser()
    xdg = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local/share")
    return Path(xdg) / "local-tts"


def reg_path() -> Path:
    return home() / "registry.json"


def load() -> dict:
    p = reg_path()
    if p.exists():
        return json.loads(p.read_text())
    return {"schema": SCHEMA, "defaults": {}, "engines": {}, "voices": {}}


def save(reg: dict) -> None:
    p = reg_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    reg["updated"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    fd, tmp = tempfile.mkstemp(dir=p.parent, suffix=".tmp")
    with os.fdopen(fd, "w") as f:
        json.dump(reg, f, indent=2, sort_keys=True)
        f.write("\n")
    os.replace(tmp, p)


def merge(dst: dict, src: dict) -> dict:
    for k, v in src.items():
        if isinstance(v, dict) and isinstance(dst.get(k), dict):
            merge(dst[k], v)
        else:
            dst[k] = v
    return dst


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    cmd, args = argv[0], argv[1:]
    reg = load()
    out = None
    if cmd == "path":
        print(home())
        return 0
    if cmd == "show":
        out = reg
    elif cmd == "get-engine":
        out = reg["engines"].get(args[0])
        if out is None:
            print(f"engine not installed: {args[0]}", file=sys.stderr)
            return 1
    elif cmd == "set-engine":
        rec = reg["engines"].setdefault(args[0], {})
        merge(rec, json.loads(args[1]))
        rec.setdefault("installed", datetime.now(timezone.utc).date().isoformat())
        reg["defaults"].setdefault("engine", args[0])
        save(reg)
        out = rec
    elif cmd == "remove-engine":
        reg["engines"].pop(args[0], None)
        if reg["defaults"].get("engine") == args[0]:
            reg["defaults"].pop("engine")
        save(reg)
        out = reg["engines"]
    elif cmd == "set-default":
        reg["defaults"][args[0]] = args[1]
        save(reg)
        out = reg["defaults"]
    elif cmd == "add-voice":
        rec = reg["voices"].setdefault(args[0], {})
        merge(rec, json.loads(args[1]))
        rec.setdefault("created", datetime.now(timezone.utc).date().isoformat())
        save(reg)
        out = rec
    elif cmd == "remove-voice":
        reg["voices"].pop(args[0], None)
        save(reg)
        out = reg["voices"]
    else:
        print(__doc__)
        return 2
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
