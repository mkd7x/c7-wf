#!/usr/bin/env python3
"""
Context Discovery Engine.
Scans target codebases to detect:
- Runtime environments & languages
- Dependency manifests & frameworks
- Directory boundaries & Clean Architecture layers
- API routes & database schemas
- Existing ADRs & documentation

@implements REQ-DISC-01
@implements REQ-DISC-02
@implements REQ-DISC-03
@implements REQ-DISC-04
"""

import os
import re
import json
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional

DEFAULT_RUNS_DIR = Path(__file__).resolve().parent.parent / "runs" / "latest"


def detect_manifests(root: Path) -> Dict[str, Any]:
    """
    Detect project manifests and infer languages and frameworks.
    @implements REQ-DISC-01
    """
    manifests = {}
    frameworks = []
    language = "unknown"

    # Python
    pyproject = root / "pyproject.toml"
    reqs = root / "requirements.txt"
    setup_py = root / "setup.py"
    if pyproject.exists() or reqs.exists() or setup_py.exists():
        language = "python"
        manifests["python"] = {
            "pyproject": pyproject.exists(),
            "requirements_txt": reqs.exists(),
            "setup_py": setup_py.exists()
        }
        # Check frameworks in requirements or pyproject
        content = ""
        if pyproject.exists():
            content += pyproject.read_text(encoding="utf-8", errors="replace")
        if reqs.exists():
            content += reqs.read_text(encoding="utf-8", errors="replace")
        for fw in ["fastapi", "django", "flask", "sqlalchemy", "pydantic", "pytest", "celery"]:
            if re.search(rf"\b{fw}\b", content, re.IGNORECASE):
                frameworks.append(fw)

    # Node / JavaScript / TypeScript
    pkg_json = root / "package.json"
    if pkg_json.exists():
        manifests["node"] = True
        try:
            data = json.loads(pkg_json.read_text(encoding="utf-8", errors="replace"))
            deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
            if any("typescript" in d for d in deps):
                language = "typescript"
            elif language == "unknown":
                language = "javascript"
            for fw in ["express", "react", "next", "vue", "prisma", "jest", "mocha", "vitest", "fastify"]:
                if any(fw in d for d in deps):
                    frameworks.append(fw)
        except Exception:
            pass

    # .NET / C#
    csproj_files = list(root.glob("**/*.csproj"))
    sln_files = list(root.glob("**/*.sln"))
    if csproj_files or sln_files:
        language = "csharp"
        manifests["dotnet"] = {
            "csproj_count": len(csproj_files),
            "sln_count": len(sln_files)
        }
        for csproj in csproj_files[:5]:
            try:
                c = csproj.read_text(encoding="utf-8", errors="replace")
                for fw in ["Microsoft.AspNetCore", "Microsoft.EntityFrameworkCore", "xunit", "NUnit", "Aspire"]:
                    if fw.lower() in c.lower() and fw not in frameworks:
                        frameworks.append(fw)
            except Exception:
                pass

    # Go
    go_mod = root / "go.mod"
    if go_mod.exists():
        language = "go"
        manifests["go"] = True
        try:
            c = go_mod.read_text(encoding="utf-8", errors="replace")
            for fw in ["gin-gonic", "fiber", "gorilla/mux", "gorm.io"]:
                if fw in c:
                    frameworks.append(fw)
        except Exception:
            pass

    # Rust
    cargo = root / "Cargo.toml"
    if cargo.exists():
        language = "rust"
        manifests["rust"] = True
        try:
            c = cargo.read_text(encoding="utf-8", errors="replace")
            for fw in ["actix-web", "axum", "tokio", "diesel", "sqlx"]:
                if fw in c:
                    frameworks.append(fw)
        except Exception:
            pass

    return {
        "language": language,
        "manifests": manifests,
        "frameworks": list(set(frameworks))
    }


def detect_boundaries_and_adrs(root: Path) -> Dict[str, Any]:
    """
    Detect structural architecture directories and existing ADRs.
    @implements REQ-DISC-02
    """
    clean_arch_layers = []
    layer_names = ["domain", "application", "infrastructure", "api", "web", "services", "controllers", "models", "core"]
    for item in root.glob("**/*"):
        if item.is_dir() and item.name.lower() in layer_names and ".git" not in item.parts:
            clean_arch_layers.append(str(item.relative_to(root)))

    # Detect existing ADRs
    adrs = []
    adr_dirs = [root / "docs" / "adr", root / "adr", root / "docs" / "adrs", root / "spec"]
    for adr_dir in adr_dirs:
        if adr_dir.exists() and adr_dir.is_dir():
            for f in adr_dir.glob("*.md"):
                adrs.append(str(f.relative_to(root)))

    return {
        "architecture_layers": sorted(list(set(clean_arch_layers)))[:15],
        "existing_adrs": sorted(adrs)[:10]
    }


def detect_routes_and_schemas(root: Path) -> Dict[str, Any]:
    """
    Detect API routes, controllers, and database schema files.
    @implements REQ-DISC-03
    """
    routes = []
    schemas = []

    route_patterns = [
        re.compile(r"@(?:app|router)\.(get|post|put|delete|patch)\(['\"]([^'\"]+)['\"]", re.IGNORECASE),
        re.compile(r"(?:app|router)\.(get|post|put|delete|patch)\(['\"]([^'\"]+)['\"]", re.IGNORECASE),
        re.compile(r"\[Http(Get|Post|Put|Delete|Patch)(?:\(['\"]([^'\"]*)['\"])?\]", re.IGNORECASE)
    ]

    for p in root.glob("**/*"):
        if not p.is_file() or ".git" in p.parts or "node_modules" in p.parts or ".venv" in p.parts:
            continue

        # Schemas
        if p.suffix.lower() in [".sql", ".prisma"] or "migration" in p.name.lower():
            schemas.append(str(p.relative_to(root)))

        # Routes in code files
        if p.suffix.lower() in [".py", ".ts", ".js", ".cs", ".go"]:
            try:
                content = p.read_text(encoding="utf-8", errors="replace")
                for pat in route_patterns:
                    matches = pat.findall(content)
                    if matches:
                        routes.append({
                            "file": str(p.relative_to(root)),
                            "count": len(matches)
                        })
                        break
            except Exception:
                pass

    return {
        "detected_schema_files": schemas[:15],
        "detected_route_files": routes[:15]
    }


def discover_codebase(source_path: Path, output_file: Optional[Path] = None) -> Dict[str, Any]:
    """
    Full context discovery pipeline with snapshotting.
    @implements REQ-DISC-01
    @implements REQ-DISC-02
    @implements REQ-DISC-03
    @implements REQ-DISC-04
    """
    source_path = Path(source_path).resolve()
    if not source_path.exists():
        return {
            "source": str(source_path),
            "status": "NOT_FOUND",
            "language": "unknown",
            "frameworks": [],
            "architecture_layers": [],
            "existing_adrs": [],
            "detected_schema_files": [],
            "detected_route_files": []
        }

    manifest_info = detect_manifests(source_path)
    boundary_info = detect_boundaries_and_adrs(source_path)
    route_info = detect_routes_and_schemas(source_path)

    context = {
        "source": str(source_path),
        "status": "DISCOVERED",
        "language": manifest_info["language"],
        "manifests": manifest_info["manifests"],
        "frameworks": manifest_info["frameworks"],
        "architecture_layers": boundary_info["architecture_layers"],
        "existing_adrs": boundary_info["existing_adrs"],
        "detected_schema_files": route_info["detected_schema_files"],
        "detected_route_files": route_info["detected_route_files"]
    }

    # Snapshot to runs directory
    save_path = output_file or (DEFAULT_RUNS_DIR / "context.json")
    save_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        save_path.write_text(json.dumps(context, indent=2), encoding="utf-8")
    except Exception as e:
        print(f"[WARN] Failed to write context snapshot: {e}")

    return context


def main():
    parser = argparse.ArgumentParser(description="Codebase Context Discovery Engine")
    parser.add_argument("--source", default=".", help="Target source path to inspect")
    parser.add_argument("--output", help="Optional output JSON path")
    parser.add_argument("--json", action="store_true", help="Print json output")
    args = parser.parse_args()

    out_file = Path(args.output) if args.output else None
    res = discover_codebase(Path(args.source), output_file=out_file)

    if args.json:
        print(json.dumps(res, indent=2))
    else:
        print(f"=== Codebase Context Discovery: {res['source']} ===")
        print(f"Language:        {res['language']}")
        print(f"Frameworks:      {', '.join(res['frameworks']) or 'None detected'}")
        print(f"Layers Found:    {len(res['architecture_layers'])}")
        print(f"Existing ADRs:   {len(res['existing_adrs'])}")
        print(f"Schema Files:    {len(res['detected_schema_files'])}")
        print(f"Route Files:     {len(res['detected_route_files'])}")


if __name__ == "__main__":
    main()
