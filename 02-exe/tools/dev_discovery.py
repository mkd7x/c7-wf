#!/usr/bin/env python3
"""
Development & Toolchain Discovery Engine for 02-exe.
Inspects a target repository or workspace to identify runtimes, package managers,
dev server / watch commands, fast test loops, linters, and environment templates.

@implements REQ-DISC-01
@implements REQ-DISC-02
@implements REQ-DISC-03
@implements REQ-DISC-04
"""

import os
import sys
import re
import json
import argparse
from pathlib import Path
from typing import Dict, Any, List, Optional


def discover_runtime_and_pm(target_dir: Path) -> Dict[str, Any]:
    """
    Detect project runtime and package managers.
    @implements REQ-DISC-02
    """
    results = {
        "runtime": "unknown",
        "package_manager": "unknown",
        "install_command": "",
        "detected_files": []
    }

    # Node.js
    if (target_dir / "package.json").is_file():
        results["runtime"] = "Node.js"
        results["detected_files"].append("package.json")
        if (target_dir / "pnpm-lock.yaml").is_file():
            results["package_manager"] = "pnpm"
            results["install_command"] = "pnpm install"
            results["detected_files"].append("pnpm-lock.yaml")
        elif (target_dir / "yarn.lock").is_file():
            results["package_manager"] = "yarn"
            results["install_command"] = "yarn install"
            results["detected_files"].append("yarn.lock")
        elif (target_dir / "bun.lockb").is_file() or (target_dir / "bun.lock").is_file():
            results["package_manager"] = "bun"
            results["install_command"] = "bun install"
        else:
            results["package_manager"] = "npm"
            results["install_command"] = "npm install"
        return results

    # Python
    py_files = [f for f in ["pyproject.toml", "setup.py", "requirements.txt", "Pipfile"] if (target_dir / f).is_file()]
    if py_files:
        results["runtime"] = "Python"
        results["detected_files"].extend(py_files)
        if (target_dir / "poetry.lock").is_file() or ((target_dir / "pyproject.toml").is_file() and "poetry" in (target_dir / "pyproject.toml").read_text(encoding="utf-8", errors="ignore")):
            results["package_manager"] = "poetry"
            results["install_command"] = "poetry install"
        elif (target_dir / "uv.lock").is_file():
            results["package_manager"] = "uv"
            results["install_command"] = "uv sync"
        else:
            results["package_manager"] = "pip"
            results["install_command"] = "pip install -r requirements.txt" if (target_dir / "requirements.txt").is_file() else "pip install -e ."
        return results

    # .NET
    sln_files = list(target_dir.glob("*.sln")) + list(target_dir.glob("*.slnx"))
    csproj_files = list(target_dir.rglob("*.csproj"))
    if sln_files or csproj_files:
        results["runtime"] = ".NET"
        results["package_manager"] = "dotnet"
        results["install_command"] = "dotnet restore"
        results["detected_files"].extend([p.name for p in (sln_files or csproj_files)[:3]])
        return results

    # Rust
    if (target_dir / "Cargo.toml").is_file():
        results["runtime"] = "Rust"
        results["package_manager"] = "cargo"
        results["install_command"] = "cargo check"
        results["detected_files"].append("Cargo.toml")
        return results

    # Go
    if (target_dir / "go.mod").is_file():
        results["runtime"] = "Go"
        results["package_manager"] = "go"
        results["install_command"] = "go mod download"
        results["detected_files"].append("go.mod")
        return results

    return results


def discover_scripts_and_taskrunners(target_dir: Path) -> Dict[str, Any]:
    """
    Scan workspace for scripts and task runners.
    @implements REQ-DISC-01
    """
    scripts = {}
    dev_commands = []
    task_targets = {}

    # package.json
    pkg_json = target_dir / "package.json"
    if pkg_json.is_file():
        try:
            data = json.loads(pkg_json.read_text(encoding="utf-8"))
            raw_scripts = data.get("scripts", {})
            scripts["npm_scripts"] = raw_scripts
            for name, cmd in raw_scripts.items():
                if any(k in name.lower() for k in ["dev", "start", "watch", "serve"]):
                    dev_commands.append(f"npm run {name}")
        except Exception:
            pass

    # Makefile
    makefile = target_dir / "Makefile"
    if makefile.is_file():
        try:
            content = makefile.read_text(encoding="utf-8", errors="ignore")
            targets = re.findall(r"^([a-zA-Z0-9_-]+):", content, re.MULTILINE)
            scripts["make_targets"] = targets
            for t in targets:
                if any(k in t.lower() for k in ["dev", "start", "watch", "run"]):
                    dev_commands.append(f"make {t}")
        except Exception:
            pass

    # Justfile (case-insensitive: Justfile or justfile)
    justfile = None
    for candidate in ("Justfile", "justfile"):
        if (target_dir / candidate).is_file():
            justfile = target_dir / candidate
            break
    if justfile is not None:
        try:
            content = justfile.read_text(encoding="utf-8", errors="ignore")
            targets = re.findall(r"^([a-zA-Z0-9_-]+):", content, re.MULTILINE)
            scripts["just_recipes"] = targets
            task_targets["just"] = targets
            for t in targets:
                if any(k in t.lower() for k in ["dev", "start", "watch"]):
                    dev_commands.append(f"just {t}")
        except Exception:
            pass

    # Taskfile (Task runner: Taskfile.yml / Taskfile.yaml / Taskfile.dist.*)
    for candidate in ("Taskfile.yml", "Taskfile.yaml", "Taskfile.dist.yml", "Taskfile.dist.yaml"):
        taskfile = target_dir / candidate
        if taskfile.is_file():
            try:
                content = taskfile.read_text(encoding="utf-8", errors="ignore")
                # Parse top-level task names under the `tasks:` mapping.
                tasks_block = re.search(r"^tasks:\s*\n((?:[ \t]+.+\n?)+)", content, re.MULTILINE)
                raw_names: List[str] = []
                if tasks_block:
                    for line in tasks_block.group(1).splitlines():
                        name_match = re.match(r"^[ \t]{2}([A-Za-z0-9_.-]+)\s*:", line)
                        if name_match:
                            raw_names.append(name_match.group(1))
                else:
                    raw_names = re.findall(r"^  ([a-zA-Z0-9_.-]+):", content, re.MULTILINE)
                scripts["task_targets"] = raw_names
                task_targets["task"] = raw_names
                for t in raw_names:
                    if any(k in t.lower() for k in ["dev", "start", "watch", "run"]):
                        dev_commands.append(f"task {t}")
                break
            except Exception:
                pass

    # Default dev commands if none extracted
    if not dev_commands:
        if (target_dir / "Cargo.toml").is_file():
            dev_commands.append("cargo watch -x check")
        elif (target_dir / "go.mod").is_file():
            dev_commands.append("go run .")
        elif list(target_dir.glob("*.sln")) or list(target_dir.rglob("*.csproj")):
            dev_commands.append("dotnet watch run")

    return {
        "scripts": scripts,
        "task_targets": task_targets,
        "recommended_dev_commands": dev_commands
    }


def discover_fast_test_and_lint(target_dir: Path) -> Dict[str, Any]:
    """
    Identify fast feedback commands: linters, typecheckers, and targeted tests.
    @implements REQ-DISC-03
    """
    linters = []
    typecheckers = []
    test_commands = []

    # Node.js configs
    if (target_dir / "package.json").is_file():
        try:
            data = json.loads((target_dir / "package.json").read_text(encoding="utf-8"))
            s = data.get("scripts", {})
            if "lint" in s:
                linters.append("npm run lint")
            if "typecheck" in s or "tsc" in s:
                typecheckers.append(f"npm run {('typecheck' if 'typecheck' in s else 'tsc')}")
            elif (target_dir / "tsconfig.json").is_file():
                typecheckers.append("npx tsc --noEmit")
            if "test" in s:
                test_commands.append("npm test")
        except Exception:
            pass

    # Python configs
    if (target_dir / "pyproject.toml").is_file() or (target_dir / "setup.py").is_file():
        linters.append("ruff check .")
        typecheckers.append("mypy .")
        test_commands.append("pytest -m 'not slow'")

    # .NET
    if list(target_dir.glob("*.sln")) or list(target_dir.rglob("*.csproj")):
        linters.append("dotnet format --verify-no-changes")
        test_commands.append("dotnet test --filter Category!=Slow")

    # Rust
    if (target_dir / "Cargo.toml").is_file():
        linters.append("cargo clippy")
        typecheckers.append("cargo check")
        test_commands.append("cargo test --lib")

    # Go
    if (target_dir / "go.mod").is_file():
        linters.append("golangci-lint run")
        test_commands.append("go test -short ./...")

    return {
        "linters": linters,
        "typecheckers": typecheckers,
        "fast_test_commands": test_commands
    }


def discover_environment_and_containers(target_dir: Path) -> Dict[str, Any]:
    """
    Detect configuration templates and container orchestration files.
    @implements REQ-DISC-04
    """
    templates = []
    compose_files = []

    candidates = [
        ".env.example", ".env.template", ".env.sample", ".env.local.example",
        "config.example.json", "local.settings.json.example"
    ]
    for cand in candidates:
        if (target_dir / cand).is_file():
            templates.append(cand)

    compose_candidates = [
        "docker-compose.yml", "docker-compose.yaml",
        "compose.yml", "compose.yaml", "docker-compose.dev.yml"
    ]
    for comp in compose_candidates:
        if (target_dir / comp).is_file():
            compose_files.append(comp)

    return {
        "env_templates": templates,
        "compose_files": compose_files,
        "has_docker": bool(compose_files)
    }


def run_discovery(source_dir: Path) -> Dict[str, Any]:
    """Full discovery scan combining all inspect modules."""
    runtime_info = discover_runtime_and_pm(source_dir)
    scripts_info = discover_scripts_and_taskrunners(source_dir)
    fast_test_info = discover_fast_test_and_lint(source_dir)
    env_info = discover_environment_and_containers(source_dir)

    return {
        "source": str(source_dir),
        "runtime": runtime_info,
        "scripts": scripts_info,
        "fast_verification": fast_test_info,
        "environment": env_info
    }


def main():
    parser = argparse.ArgumentParser(description="02-exe Dev Discovery Engine")
    parser.add_argument("--source", default="workspace", help="Target source directory")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    args = parser.parse_args()

    target = Path(args.source).resolve()
    result = run_discovery(target)

    if args.json:
        print(json.dumps(result, indent=2))
        sys.exit(0)

    print("=" * 65)
    print(f"      02-EXE DEVELOPMENT DISCOVERY: {target.name}")
    print("=" * 65)
    print(f"Runtime:         {result['runtime']['runtime']} ({result['runtime']['package_manager']})")
    print(f"Install Command: {result['runtime']['install_command'] or 'N/A'}")
    print("-" * 65)
    print(f"Recommended Dev Commands:")
    for cmd in result['scripts']['recommended_dev_commands']:
        print(f"  • {cmd}")
    print("-" * 65)
    print(f"Fast Verification:")
    print(f"  • Linters:      {', '.join(result['fast_verification']['linters']) or 'None'}")
    print(f"  • Typecheckers: {', '.join(result['fast_verification']['typecheckers']) or 'None'}")
    print(f"  • Fast Tests:   {', '.join(result['fast_verification']['fast_test_commands']) or 'None'}")
    print("-" * 65)
    print(f"Environment & Containers:")
    print(f"  • Env Templates: {', '.join(result['environment']['env_templates']) or 'None'}")
    print(f"  • Compose Files: {', '.join(result['environment']['compose_files']) or 'None'}")
    print("=" * 65)


if __name__ == "__main__":
    main()
