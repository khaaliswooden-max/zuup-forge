"""Zuup Forge CLI — The Platform That Builds Platforms."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from forge.compiler import compile_platform
from forge.compiler.parser import load_all_specs, load_spec


def cmd_compile(args):
    """Compile a single spec file (e.g. forge compile specs/aureon.platform.yaml)."""
    path = Path(args.spec)
    if not path.exists():
        print(f"Error: spec not found: {path}", file=sys.stderr)
        sys.exit(1)
    spec = load_spec(path)
    out_dir = Path(args.output) if getattr(args, "output", None) else Path("platforms") / spec.platform.name
    result = compile_platform(spec, out_dir)
    print(f"[OK] {result.summary()}")
    for f in result.files_generated:
        print(f"  -> {f}")


def cmd_init(args):
    spec = load_spec(Path(args.spec))
    result = compile_platform(spec, Path("platforms") / spec.platform.name)
    print(f"[OK] {result.summary()}")
    for f in result.files_generated:
        print(f"  -> {f}")

def cmd_generate(args):
    if args.platform:
        spec = load_spec(Path("specs") / f"{args.platform}.platform.yaml")
        result = compile_platform(spec, Path("platforms") / args.platform)
        print(f"[OK] {result.summary()}")
    else:
        for name, spec in load_all_specs("specs").items():
            result = compile_platform(spec, Path("platforms") / name)
            print(f"[OK] {result.summary()}")

def cmd_dev(args):
    import subprocess

    subprocess.run(
        [
            sys.executable, "-m", "uvicorn",
            f"platforms.{args.platform}.app:app",
            "--reload", "--port", "8000",
        ]
    )


def cmd_ui(args):
    import subprocess
    subprocess.run([
        sys.executable, "-m", "uvicorn", "forge.ui.app:app",
        "--reload" if getattr(args, "reload", False) else "--no-reload",
        "--port", str(getattr(args, "port", "8765")),
    ])


def main():
    parser = argparse.ArgumentParser(
        prog="forge",
        description="Zuup Forge — The Platform That Builds Platforms",
    )
    sub = parser.add_subparsers(dest="command")

    p = sub.add_parser("compile", help="Compile a platform from a YAML spec file")
    p.add_argument("spec", help="Path to .platform.yaml (e.g. specs/aureon.platform.yaml)")
    p.add_argument("-o", "--output", help="Output directory (default: platforms/<name>)")
    p = sub.add_parser("init")
    p.add_argument("platform")
    p.add_argument("--from", dest="spec", required=True)
    p = sub.add_parser("generate")
    p.add_argument("platform", nargs="?")
    p = sub.add_parser("dev")
    p.add_argument("platform")
    p = sub.add_parser("eval")
    p.add_argument("platform")
    p.add_argument("--suite", default="default")
    p = sub.add_parser("ui")
    p.add_argument("--port", default="8765")
    p.add_argument("--reload", action="store_true")

    args = parser.parse_args()
    commands = {
        "compile": cmd_compile,
        "init": cmd_init,
        "generate": cmd_generate,
        "dev": cmd_dev,
        "ui": cmd_ui,
    }
    commands.get(args.command, lambda _: parser.print_help())(args)

if __name__ == "__main__":
    main()
