#!/usr/bin/env python3
"""
Test Discovery Engine for Clean Room QA Testing.
Scans a target project directory to detect documentation, test guidelines,
framework configurations, and executable test commands.
"""

import os
import re
import json
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional, Union

DOC_CANDIDATES = [
    "TESTING.md", "testing.md", "TESTS.md", "test.md", "TEST.md",
    "README.md", "readme.md",
    "CONTRIBUTING.md", "contributing.md",
    "docs/TESTING.md", "docs/testing.md", "docs/tests.md"
]

BOX_DRAWING_CHARS = frozenset("└├┤┬┴┼─│═║╔╗╚╝╠╣╳×")

# A doc line is only treated as a runnable command when it starts with a
# known runner (or `$`). Bare-substring matching ("python" in prose) and
# ASCII-tree art ("└── tests/") previously produced junk recommendations.
COMMAND_PREFIXES = (
    "dotnet ", "dotnet\t",
    "pytest", "python -m pytest", "python3 -m pytest",
    "npm ", "npx ", "node ", "yarn ", "pnpm ", "bun ",
    "cargo ", "go test", "go ",
    "make ", "ctest", "gradle", "mvn ",
    "vitest", "jest", "playwright", "cypress",
    "python ", "python3 ",
)

# Single-word runner invocations that are valid without trailing args.
COMMAND_BARE = frozenset({
    "pytest", "dotnet", "cargo", "make", "gradle", "mvn",
    "vitest", "jest", "playwright", "cypress",
})

def find_documentation_files(target_dir: Path) -> List[Path]:
    """
    Find existing documentation markdown files in target directory with accurate case handling.
    @implements REQ-DISC-01
    """
    if not target_dir.exists():
        return []

    actual_files = {}
    for p in target_dir.iterdir():
        if p.is_file():
            actual_files[p.name.lower()] = p

    docs_dir = target_dir / "docs"
    if docs_dir.is_dir():
        for p in docs_dir.iterdir():
            if p.is_file():
                actual_files[f"docs/{p.name.lower()}"] = p

    found = []
    for candidate in DOC_CANDIDATES:
        cand_lower = candidate.lower()
        if cand_lower in actual_files:
            real_file = actual_files[cand_lower]
            if real_file not in found:
                found.append(real_file)
    return found

def _strip_inline_comment(line: str) -> str:
    """Remove a trailing `# comment`, respecting quotes."""
    in_single = in_double = False
    for i, ch in enumerate(line):
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        elif ch == "#" and not in_single and not in_double:
            # Require whitespace (or start) before the comment marker.
            if i == 0 or line[i - 1] in (" ", "\t"):
                return line[:i].rstrip()
    return line


def _looks_like_command(line: str) -> bool:
    """Check a cleaned line starts with a known test/build runner."""
    lowered = line.lower()
    if any(c in line for c in BOX_DRAWING_CHARS):
        return False
    if lowered in COMMAND_BARE:
        return True
    return lowered.startswith(COMMAND_PREFIXES)


def extract_markdown_commands(file_path: Path) -> List[str]:
    """
    Extract shell commands from code blocks in markdown file.
    @implements REQ-DISC-02
    """
    try:
        content = file_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return []

    commands = []
    # Match ```bash / ```sh / ``` or lines in code blocks
    code_blocks = re.findall(r"```(?:bash|sh|shell)?\s*\n(.*?)\n```", content, re.DOTALL)
    for block in code_blocks:
        for line in block.strip().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            # Strip common shell prompts ($, >, %)
            if line[:2] in ("$ ", "> ", "% "):
                line = line[2:].strip()
            elif line[:1] in ("$", ">", "%") and len(line) > 1:
                line = line[1:].strip()
            if not line or line.startswith("#"):
                continue
            line = _strip_inline_comment(line)
            if line and _looks_like_command(line):
                commands.append(line)
    return commands

def inspect_package_json(target_dir: Path) -> Optional[Dict[str, Any]]:
    """
    Inspect package.json if present for npm/node scripts.
    @implements REQ-DISC-03
    """
    pkg_path = target_dir / "package.json"
    if not pkg_path.is_file():
        return None
    try:
        with open(pkg_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        scripts = data.get("scripts", {})
        return {
            "type": "Node.js (package.json)",
            "scripts": scripts,
            "has_test": "test" in scripts,
            "has_smoke": any("smoke" in k.lower() for k in scripts),
            "has_unit": any("unit" in k.lower() for k in scripts),
            "has_build": "build" in scripts,
            "has_lint": "lint" in scripts,
        }
    except Exception:
        return {"type": "Node.js (package.json - parse error)", "scripts": {}}

def inspect_python_project(target_dir: Path) -> Optional[Dict[str, Any]]:
    """
    Inspect Python test and config files.
    @implements REQ-DISC-03
    """
    py_indicators = ["pyproject.toml", "setup.py", "setup.cfg", "pytest.ini", "requirements.txt"]
    found_indicators = [ind for ind in py_indicators if (target_dir / ind).is_file()]
    if not found_indicators and not list(target_dir.glob("*.py")):
        return None

    has_pytest = (target_dir / "pytest.ini").is_file() or any(
        "pytest" in (target_dir / f).read_text(encoding="utf-8", errors="replace")
        for f in found_indicators if (target_dir / f).is_file() and (target_dir / f).stat().st_size < 100000
    )
    return {
        "type": "Python",
        "indicators": found_indicators,
        "uses_pytest": has_pytest,
        "has_tests_dir": (target_dir / "tests").is_dir() or (target_dir / "test").is_dir()
    }

def inspect_makefile(target_dir: Path) -> Optional[Dict[str, Any]]:
    """
    Inspect Makefile for test targets.
    @implements REQ-DISC-03
    """
    makefile = target_dir / "Makefile"
    if not makefile.is_file():
        return None
    try:
        content = makefile.read_text(encoding="utf-8", errors="replace")
        targets = re.findall(r"^([a-zA-Z0-9_-]+):", content, re.MULTILINE)
        test_targets = [t for t in targets if any(k in t.lower() for k in ["test", "smoke", "unit", "check"])]
        return {
            "type": "Makefile",
            "targets": targets,
            "test_targets": test_targets
        }
    except Exception:
        return None

def inspect_rust(target_dir: Path) -> Optional[Dict[str, Any]]:
    """
    Inspect Cargo.toml.
    @implements REQ-DISC-03
    """
    cargo = target_dir / "Cargo.toml"
    if cargo.is_file():
        return {"type": "Rust (Cargo)", "command": "cargo test"}
    return None

def inspect_go(target_dir: Path) -> Optional[Dict[str, Any]]:
    """
    Inspect go.mod.
    @implements REQ-DISC-03
    """
    gomod = target_dir / "go.mod"
    if gomod.is_file():
        return {"type": "Go", "command": "go test ./..."}
    return None


def inspect_dotnet(target_dir: Path) -> Optional[Dict[str, Any]]:
    """
    Inspect .NET solution/project files (*.sln, *.slnx, *.csproj).
    @implements REQ-DISC-03
    """
    solutions = sorted(
        [p for pat in ("*.sln", "*.slnx") for p in target_dir.glob(pat) if p.is_file()],
        key=lambda p: p.name,
    )
    # Prefer .slnx (new XML solution format), then .sln, then bare .csproj.
    solution = next((p for p in solutions if p.suffix == ".slnx"), None)
    if solution is None and solutions:
        solution = solutions[0]
    projects = sorted(
        [p for p in target_dir.rglob("*.csproj") if p.is_file()],
        key=lambda p: p.relative_to(target_dir).as_posix(),
    )
    # Avoid descending into vendored/cached trees.
    projects = [p for p in projects
                if not any(part in (".git", "node_modules", ".venv", "bin", "obj", "target-repo")
                           for part in p.parts)]
    if solution is None and not projects:
        return None

    test_projects = [p for p in projects
                     if re.search(r"test", p.relative_to(target_dir).as_posix(), re.IGNORECASE)]

    build_target = solution.name if solution else (
        test_projects[0].name if len(projects) == 1 and test_projects else None
    )
    info: Dict[str, Any] = {
        "type": ".NET",
        "solution": solution.name if solution else None,
        "projects": [p.relative_to(target_dir).as_posix() for p in projects[:25]],
        "project_count": len(projects),
        "test_projects": [p.relative_to(target_dir).as_posix() for p in test_projects[:25]],
        "has_tests": bool(test_projects),
    }
    if build_target:
        info["build_command"] = f"dotnet build {build_target} -c Release"
    info["test_command"] = "dotnet test"
    if solution:
        info["test_command"] = f"dotnet test {solution.name}"
    elif len(test_projects) == 1:
        info["test_command"] = (
            f"dotnet test {test_projects[0].relative_to(target_dir).as_posix()}"
        )
    return info

def discover_project_tests(target_dir: Union[str, Path]) -> Dict[str, Any]:
    """
    Main discovery entry point.
    @implements REQ-DISC-04
    """
    target_path = Path(target_dir).resolve()
    if not target_path.exists():
        return {
            "target_dir": str(target_path),
            "error": f"Target directory {target_path} does not exist."
        }

    docs = find_documentation_files(target_path)
    discovered_doc_names = [d.relative_to(target_path).as_posix() for d in docs]

    doc_commands = []
    for doc in docs:
        cmds = extract_markdown_commands(doc)
        if cmds:
            doc_commands.extend(cmds)

    # Framework checks
    pkg = inspect_package_json(target_path)
    py = inspect_python_project(target_path)
    make = inspect_makefile(target_path)
    rust = inspect_rust(target_path)
    golang = inspect_go(target_path)
    dotnet = inspect_dotnet(target_path)

    # Determine framework & recommended commands
    frameworks = []
    recommended = {
        "build": None,
        "smoke": None,
        "unit": None,
        "integration": None,
        "all": []
    }

    if pkg:
        frameworks.append("Node.js")
        scripts = pkg.get("scripts", {})
        if "build" in scripts: recommended["build"] = "npm run build"
        if "test:smoke" in scripts: recommended["smoke"] = "npm run test:smoke"
        elif "test" in scripts: recommended["smoke"] = "npm test"
        if "test:unit" in scripts: recommended["unit"] = "npm run test:unit"
        elif "test" in scripts: recommended["unit"] = "npm test"
        if "test:integration" in scripts: recommended["integration"] = "npm run test:integration"
        if "test" in scripts: recommended["all"].append("npm test")

    if py:
        frameworks.append("Python")
        runner_cmd = "pytest" if py.get("uses_pytest") else "python3 -m unittest discover"
        if not recommended["smoke"]: recommended["smoke"] = f"{runner_cmd} -q"
        if not recommended["unit"]: recommended["unit"] = runner_cmd
        if not recommended["all"]: recommended["all"].append(runner_cmd)

    if rust:
        frameworks.append("Rust")
        if not recommended["smoke"]: recommended["smoke"] = "cargo check"
        if not recommended["unit"]: recommended["unit"] = "cargo test"
        if not recommended["all"]: recommended["all"].append("cargo test")

    if golang:
        frameworks.append("Go")
        if not recommended["smoke"]: recommended["smoke"] = "go test -short ./..."
        if not recommended["unit"]: recommended["unit"] = "go test -v ./..."
        if not recommended["all"]: recommended["all"].append("go test ./...")

    if make and make.get("test_targets"):
        frameworks.append("Makefile")
        targets = make["test_targets"]
        for t in targets:
            if "smoke" in t: recommended["smoke"] = f"make {t}"
            elif "unit" in t: recommended["unit"] = f"make {t}"
            elif "test" in t and not recommended["all"]: recommended["all"].append(f"make {t}")

    if dotnet:
        frameworks.append(".NET")
        if dotnet.get("build_command"):
            recommended["build"] = dotnet["build_command"]
        if not recommended["smoke"]:
            recommended["smoke"] = dotnet.get("build_command") or "dotnet build -c Release"
        if not recommended["unit"]:
            recommended["unit"] = dotnet.get("test_command", "dotnet test")
        if not recommended["all"]:
            recommended["all"].append(dotnet.get("test_command", "dotnet test"))

    # De-duplicate doc commands while preserving order
    unique_doc_commands = []
    for c in doc_commands:
        if c not in unique_doc_commands:
            unique_doc_commands.append(c)
    doc_commands = unique_doc_commands

    # If documentation contains explicit test commands, prioritize them
    if doc_commands:
        # Check for smoke-specific commands or prioritize first doc command
        smoke_candidates = [c for c in doc_commands if "smoke" in c.lower()]
        unit_candidates = [c for c in doc_commands if "unit" in c.lower()]

        recommended["smoke"] = smoke_candidates[0] if smoke_candidates else doc_commands[0]
        if unit_candidates:
            recommended["unit"] = unit_candidates[0]
        elif not recommended["unit"]:
            recommended["unit"] = doc_commands[0]
        if not recommended["all"]:
            recommended["all"] = doc_commands

    return {
        "target_dir": str(target_path),
        "docs_found": discovered_doc_names,
        "extracted_doc_commands": doc_commands,
        "detected_frameworks": frameworks or ["Generic / Unknown"],
        "package_json": pkg,
        "python_project": py,
        "makefile": make,
        "dotnet": dotnet,
        "recommended_commands": recommended
    }

def main():
    parser = argparse.ArgumentParser(description="Clean Room Test Discovery Engine")
    parser.add_argument("--target", "-t", default="target-repo", help="Path to target directory")
    parser.add_argument("--json", "-j", action="store_true", help="Output raw JSON")
    args = parser.parse_args()

    result = discover_project_tests(args.target)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"=== Clean Room Test Discovery ===")
        print(f"Target: {result.get('target_dir')}")
        print(f"Detected Frameworks: {', '.join(result.get('detected_frameworks', []))}")
        print(f"Documentation Found: {', '.join(result.get('docs_found', [])) or 'None'}")
        if result.get("extracted_doc_commands"):
            print(f"Commands extracted from docs:")
            for c in result["extracted_doc_commands"]:
                print(f"  $ {c}")
        rec = result.get("recommended_commands", {})
        print(f"\nRecommended Commands:")
        print(f"  Build:       {rec.get('build') or 'N/A'}")
        print(f"  Smoke Test:  {rec.get('smoke') or 'N/A'}")
        print(f"  Unit Test:   {rec.get('unit') or 'N/A'}")
        print(f"  Integration: {rec.get('integration') or 'N/A'}")

if __name__ == "__main__":
    main()
