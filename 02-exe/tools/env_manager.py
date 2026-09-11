#!/usr/bin/env python3
"""
Environment & Credential Manager for 02-exe.
Handles declarative credential resolution from multiple providers (1Password, AWS Secrets,
Doppler, Vault, Env Vars, File Mocks), safe .env synthesis from templates, gitignore safety checks,
and secret masking.

@implements REQ-ENV-01
@implements REQ-ENV-02
@implements REQ-ENV-03
@implements REQ-ENV-04
"""

import os
import sys
import re
import json
import shutil
import subprocess
import argparse
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

try:
    from tools import audit_logger
except ImportError:
    import audit_logger


class CredentialProvider:
    """Base interface for credential providers."""
    def resolve(self, reference: str) -> Optional[str]:
        raise NotImplementedError


class EnvVarProvider(CredentialProvider):
    """Resolves credentials directly from existing environment variables."""
    def resolve(self, reference: str) -> Optional[str]:
        return os.environ.get(reference)


class FileMockProvider(CredentialProvider):
    """Resolves credentials from local JSON/key-value file for local/mock testing."""
    def __init__(self, file_path: Optional[Path] = None):
        self.file_path = file_path or Path(__file__).resolve().parent.parent / ".secrets" / "mock_secrets.json"

    def resolve(self, reference: str) -> Optional[str]:
        if not self.file_path.exists():
            return None
        try:
            data = json.loads(self.file_path.read_text(encoding="utf-8"))
            return data.get(reference)
        except Exception:
            return None


class OnePasswordProvider(CredentialProvider):
    """Resolves credentials using 1Password CLI (`op read`)."""
    def resolve(self, reference: str) -> Optional[str]:
        # reference format: op://vault/item/field
        if not shutil.which("op"):
            # Fallback to local env if mock exists
            env_key = reference.replace("op://", "").replace("/", "_").upper()
            return os.environ.get(env_key)
        try:
            res = subprocess.run(["op", "read", reference], capture_output=True, text=True, check=True)
            return res.stdout.strip()
        except Exception:
            return None


class AwsSecretsProvider(CredentialProvider):
    """Resolves credentials from AWS Secrets Manager."""
    def resolve(self, reference: str) -> Optional[str]:
        # reference format: secret-id:json-key or secret-id
        if not shutil.which("aws"):
            env_key = reference.replace(":", "_").replace("-", "_").upper()
            return os.environ.get(env_key)
        secret_id = reference.split(":")[0]
        json_key = reference.split(":")[1] if ":" in reference else None
        try:
            res = subprocess.run(
                ["aws", "secretsmanager", "get-secret-value", "--secret-id", secret_id, "--query", "SecretString", "--output", "text"],
                capture_output=True, text=True, check=True
            )
            raw = res.stdout.strip()
            if json_key:
                parsed = json.loads(raw)
                return str(parsed.get(json_key, ""))
            return raw
        except Exception:
            return None


class DopplerProvider(CredentialProvider):
    """Resolves credentials from Doppler CLI."""
    def resolve(self, reference: str) -> Optional[str]:
        if not shutil.which("doppler"):
            return os.environ.get(reference)
        try:
            res = subprocess.run(["doppler", "secrets", "get", reference, "--plain"], capture_output=True, text=True, check=True)
            return res.stdout.strip()
        except Exception:
            return None


class VaultProvider(CredentialProvider):
    """Resolves credentials from HashiCorp Vault CLI."""
    def resolve(self, reference: str) -> Optional[str]:
        # reference format: path/to/secret:field
        if not shutil.which("vault"):
            env_key = reference.replace("/", "_").replace(":", "_").upper()
            return os.environ.get(env_key)
        path = reference.split(":")[0]
        field = reference.split(":")[1] if ":" in reference else "value"
        try:
            res = subprocess.run(["vault", "kv", "get", f"-field={field}", path], capture_output=True, text=True, check=True)
            return res.stdout.strip()
        except Exception:
            return None


PROVIDERS: Dict[str, CredentialProvider] = {
    "env-var": EnvVarProvider(),
    "file": FileMockProvider(),
    "1password": OnePasswordProvider(),
    "aws-secrets": AwsSecretsProvider(),
    "doppler": DopplerProvider(),
    "vault": VaultProvider(),
}


def get_provider(provider_name: str) -> CredentialProvider:
    """Retrieve registered credential provider or default to EnvVarProvider."""
    return PROVIDERS.get(provider_name.lower(), EnvVarProvider())


def is_file_gitignored(file_path: Path, workspace_dir: Path) -> bool:
    """Check if the given file path is excluded by .gitignore in workspace or parent."""
    # Check if git recognizes it as ignored
    if shutil.which("git") and workspace_dir.exists():
        try:
            res = subprocess.run(
                ["git", "check-ignore", "-q", str(file_path)],
                cwd=workspace_dir,
                capture_output=True
            )
            if res.returncode == 0:
                return True
        except Exception:
            pass

    # Fallback to manual check in .gitignore files
    for check_dir in [workspace_dir, file_path.parent, workspace_dir.parent]:
        gi = check_dir / ".gitignore"
        if gi.is_file():
            try:
                lines = gi.read_text(encoding="utf-8").splitlines()
                target_name = file_path.name
                for line in lines:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        if line == target_name or line == f"/{target_name}" or line == "*.env" or line == ".env*":
                            return True
            except Exception:
                pass
    return False


def resolve_credentials(secrets_config: List[Dict[str, Any]]) -> Dict[str, str]:
    """Resolve a list of secret definitions using configured providers."""
    resolved = {}
    for item in secrets_config:
        name = item.get("name")
        if not name:
            continue
        provider_name = item.get("provider", "env-var") or "env-var"
        reference = item.get("reference", name) or name
        fallback = item.get("fallback")

        provider = get_provider(str(provider_name))
        value = provider.resolve(str(reference))
        if value is None:
            value = fallback

        if value is not None:
            resolved[name] = str(value)
            # Register in audit logger for masking
            audit_logger.register_secret(str(value))
    return resolved


def synthesize_env_file(
    template_path: Path,
    output_path: Path,
    resolved_secrets: Dict[str, str],
    static_vars: Optional[Dict[str, str]] = None,
    workspace_dir: Optional[Path] = None,
    enforce_gitignore: bool = True
) -> Tuple[bool, str]:
    """
    Synthesizes a target .env file by taking a template (.env.example),
    substituting resolved secrets and static variables, and verifying gitignore safety.
    """
    workspace = workspace_dir or output_path.parent
    static_vars = static_vars or {}
    gitignore_note = ""

    if enforce_gitignore:
        # If output file is inside workspace, make sure it is ignored.
        # Auto-remediation appends an entry and reports it explicitly so the
        # caller knows .gitignore was mutated (spec: "aborts or warns").
        if not is_file_gitignored(output_path, workspace):
            gi_file = workspace / ".gitignore"
            try:
                with open(gi_file, "a", encoding="utf-8") as f:
                    f.write(f"\n# Added by 02-exe env_manager\n{output_path.name}\n*.env\n")
                gitignore_note = (
                    f" (WARNING: {output_path.name} was not gitignored;"
                    f" auto-appended an entry to {gi_file})"
                )
            except Exception as e:
                return False, f"Destination {output_path.name} is NOT gitignored and could not update .gitignore: {e}"
        else:
            gitignore_note = ""

    if not template_path.exists():
        # If no template, generate standard key-value file from resolved variables
        lines = ["# Generated by 02-exe env_manager\n"]
        merged = {**static_vars, **resolved_secrets}
        for k, v in merged.items():
            lines.append(f"{k}={v}\n")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("".join(lines), encoding="utf-8")
        return True, f"Created {output_path} with {len(merged)} variables (no template provided).{gitignore_note if enforce_gitignore else ''}"

    template_content = template_path.read_text(encoding="utf-8")
    merged_vars = {**static_vars, **resolved_secrets}

    output_lines = []
    for line in template_content.splitlines():
        trimmed = line.strip()
        if not trimmed or trimmed.startswith("#"):
            output_lines.append(line)
            continue

        match = re.match(r"^([A-Za-z_0-9]+)=(.*)$", trimmed)
        if match:
            var_name = match.group(1)
            default_val = match.group(2)
            if var_name in merged_vars:
                output_lines.append(f"{var_name}={merged_vars[var_name]}")
            else:
                output_lines.append(line)
        else:
            output_lines.append(line)

    # Append any variables present in config that were not in template
    existing_vars = set(re.findall(r"^([A-Za-z_0-9]+)=", template_content, re.MULTILINE))
    for k, v in merged_vars.items():
        if k not in existing_vars:
            output_lines.append(f"{k}={v}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(output_lines) + "\n", encoding="utf-8")
    return True, f"Synthesized {output_path} successfully from {template_path.name} ({len(merged_vars)} variables).{gitignore_note}"


def main():
    parser = argparse.ArgumentParser(description="02-exe Environment & Credential Manager")
    subparsers = parser.add_subparsers(dest="action", required=True)

    # setup
    setup_p = subparsers.add_parser("setup", help="Synthesize .env and resolve credentials")
    setup_p.add_argument("--config", help="Path to env config JSON or workflow markdown")
    setup_p.add_argument("--template", default=".env.example", help="Template file name/path")
    setup_p.add_argument("--output", default=".env", help="Output file name/path")
    setup_p.add_argument("--workspace", default="workspace", help="Target workspace path")
    setup_p.add_argument("--no-strict-gitignore", action="store_true", help="Skip gitignore check")

    # fetch-secret
    fetch_p = subparsers.add_parser("fetch-secret", help="Fetch a single secret via provider")
    fetch_p.add_argument("--provider", default="env-var", choices=list(PROVIDERS.keys()), help="Provider name")
    fetch_p.add_argument("--ref", required=True, help="Secret reference or key name")

    args = parser.parse_args()

    if args.action == "fetch-secret":
        provider = get_provider(args.provider)
        secret = provider.resolve(args.ref)
        if secret is not None:
            # Mask when printing
            audit_logger.register_secret(secret)
            print(f"[✓] Secret resolved for {args.ref}: {audit_logger.redact_text(secret)}")
            sys.exit(0)
        else:
            print(f"[!] Secret could not be resolved for reference: {args.ref}", file=sys.stderr)
            sys.exit(1)

    elif args.action == "setup":
        workspace_dir = Path(args.workspace).resolve()
        template_file = workspace_dir / args.template if not Path(args.template).is_absolute() else Path(args.template)
        output_file = workspace_dir / args.output if not Path(args.output).is_absolute() else Path(args.output)

        secrets_cfg = []
        static_vars = {}

        if args.config and Path(args.config).exists():
            cfg_path = Path(args.config)
            if cfg_path.suffix == ".json":
                try:
                    data = json.loads(cfg_path.read_text(encoding="utf-8"))
                    secrets_cfg = data.get("secrets", [])
                    static_vars = data.get("variables", {})
                except Exception as e:
                    print(f"[!] Failed to parse config {args.config}: {e}", file=sys.stderr)
                    sys.exit(1)

        resolved_secrets = resolve_credentials(secrets_cfg)
        ok, msg = synthesize_env_file(
            template_path=template_file,
            output_path=output_file,
            resolved_secrets=resolved_secrets,
            static_vars=static_vars,
            workspace_dir=workspace_dir,
            enforce_gitignore=not args.no_strict_gitignore
        )
        if ok:
            print(f"[✓] {msg}")
            sys.exit(0)
        else:
            print(f"[!] {msg}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
