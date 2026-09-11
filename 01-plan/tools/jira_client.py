#!/usr/bin/env python3
"""
Jira REST API Client & Synchronization Engine.
Provides bidirectional Jira integration:
- Fetch issue summary, description, acceptance criteria, components
- Post structured Markdown comments with execution plan links
- Transition Jira issue status (e.g. to "In Progress")
- Create child subtasks corresponding to planned tasks
- Supports automatic offline/mock mode when unconfigured or running in CI

@implements REQ-WORK-01
@implements REQ-WORK-03
"""

import os
import re
import sys
import json
import base64
import urllib.request
import urllib.error
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
import task_graph

DEFAULT_RUNS_DIR = Path(__file__).resolve().parent.parent / "runs" / "latest"
TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
COMMENT_TEMPLATE_FILE = TEMPLATES_DIR / "JIRA_COMMENT_TEMPLATE.md"


class JiraClient:
    def __init__(self, base_url: Optional[str] = None, email: Optional[str] = None,
                 api_token: Optional[str] = None, dry_run: bool = False):
        self.base_url = (base_url or os.environ.get("JIRA_BASE_URL", "")).rstrip("/")
        self.email = email or os.environ.get("JIRA_EMAIL", "")
        self.api_token = api_token or os.environ.get("JIRA_API_TOKEN", "")
        self.dry_run = dry_run or not (self.base_url and self.api_token)

    def _get_headers(self) -> Dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        if self.email and self.api_token:
            auth_str = f"{self.email}:{self.api_token}"
            b64_auth = base64.b64encode(auth_str.encode("utf-8")).decode("utf-8")
            headers["Authorization"] = f"Basic {b64_auth}"
        elif self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"
        return headers

    def fetch_issue(self, ticket_key: str) -> Dict[str, Any]:
        """
        Fetch Jira issue details.
        @implements REQ-WORK-01
        """
        ticket_key = ticket_key.upper().strip()

        if self.dry_run:
            mock_data = {
                "key": ticket_key,
                "summary": f"Feature / Task specification for {ticket_key}",
                "description": f"Automated requirement specification for issue {ticket_key}.",
                "acceptance_criteria": [
                    f"Core functionality for {ticket_key} is implemented",
                    "Unit and integration tests pass with zero errors",
                    "Clean Architecture boundary is preserved"
                ],
                "components": ["Core", "API"],
                "status": "To Do",
                "reporter": "planner-agent",
                "is_mock": True
            }
            self._record_sync("fetch_issue", ticket_key, mock_data)
            return mock_data

        url = f"{self.base_url}/rest/api/2/issue/{ticket_key}"
        req = urllib.request.Request(url, headers=self._get_headers(), method="GET")
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                fields = data.get("fields", {})
                desc = fields.get("description") or ""

                # Attempt to extract acceptance criteria from description
                ac_list = []
                ac_match = re.search(r"(?:Acceptance Criteria|ACs?):\s*\n((?:\s*[-*]\s*.+\n?)+)", desc, re.IGNORECASE)
                if ac_match:
                    for line in ac_match.group(1).splitlines():
                        c = re.sub(r"^\s*[-*]\s*", "", line).strip()
                        if c:
                            ac_list.append(c)
                if not ac_list:
                    ac_list = [f"Complete work for {ticket_key}"]

                issue_info = {
                    "key": data.get("key", ticket_key),
                    "summary": fields.get("summary", ""),
                    "description": desc,
                    "acceptance_criteria": ac_list,
                    "components": [c.get("name", "") for c in fields.get("components", [])],
                    "status": fields.get("status", {}).get("name", "Unknown"),
                    "reporter": fields.get("reporter", {}).get("displayName", "Unknown"),
                    "is_mock": False
                }
                self._record_sync("fetch_issue", ticket_key, issue_info)
                return issue_info
        except Exception as e:
            print(f"[WARN] Failed to fetch Jira issue '{ticket_key}' from API: {e}. Falling back to offline mode.")
            self.dry_run = True
            return self.fetch_issue(ticket_key)

    def post_comment(self, ticket_key: str, comment_text: str) -> Dict[str, Any]:
        """
        Post a Markdown comment to the Jira issue.
        @implements REQ-WORK-03
        """
        ticket_key = ticket_key.upper().strip()

        if self.dry_run:
            res = {
                "key": ticket_key,
                "status": "COMMENT_POSTED_MOCK",
                "comment_length": len(comment_text),
                "is_mock": True
            }
            self._record_sync("post_comment", ticket_key, res)
            return res

        url = f"{self.base_url}/rest/api/2/issue/{ticket_key}/comment"
        body = json.dumps({"body": comment_text}).encode("utf-8")
        req = urllib.request.Request(url, data=body, headers=self._get_headers(), method="POST")
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                res = {
                    "key": ticket_key,
                    "comment_id": data.get("id"),
                    "status": "COMMENT_POSTED",
                    "is_mock": False
                }
                self._record_sync("post_comment", ticket_key, res)
                return res
        except Exception as e:
            print(f"[WARN] Failed to post comment to Jira: {e}")
            return {"key": ticket_key, "error": str(e), "status": "FAILED"}

    def transition_issue(self, ticket_key: str, target_status: str) -> Dict[str, Any]:
        """
        Transition issue to a new status (e.g. 'In Progress').
        @implements REQ-WORK-03
        """
        ticket_key = ticket_key.upper().strip()

        if self.dry_run:
            res = {
                "key": ticket_key,
                "transitioned_to": target_status,
                "status": "TRANSITIONED_MOCK",
                "is_mock": True
            }
            self._record_sync("transition_issue", ticket_key, res)
            return res

        url = f"{self.base_url}/rest/api/2/issue/{ticket_key}/transitions"
        req = urllib.request.Request(url, headers=self._get_headers(), method="GET")
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                transitions = data.get("transitions", [])
                matched_id = None
                for tr in transitions:
                    if tr.get("name", "").lower() == target_status.lower():
                        matched_id = tr.get("id")
                        break
                if not matched_id and transitions:
                    matched_id = transitions[0].get("id")

                if matched_id:
                    post_body = json.dumps({"transition": {"id": matched_id}}).encode("utf-8")
                    tr_req = urllib.request.Request(url, data=post_body, headers=self._get_headers(), method="POST")
                    urllib.request.urlopen(tr_req, timeout=15)
                    res = {"key": ticket_key, "transitioned_to": target_status, "status": "SUCCESS"}
                else:
                    res = {"key": ticket_key, "error": f"Transition '{target_status}' not found", "status": "FAILED"}
                self._record_sync("transition_issue", ticket_key, res)
                return res
        except Exception as e:
            print(f"[WARN] Failed to transition issue {ticket_key}: {e}")
            return {"key": ticket_key, "error": str(e), "status": "FAILED"}

    def _post_json(self, url: str, payload: Dict[str, Any]) -> Tuple[bool, Any]:
        """POST a JSON payload; return (ok, parsed response or error string)."""
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=body, headers=self._get_headers(), method="POST")
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                raw = resp.read().decode("utf-8")
                try:
                    return True, json.loads(raw) if raw else {}
                except json.JSONDecodeError:
                    return True, {}
        except Exception as e:
            err_msg = str(e)
            if hasattr(e, "read"):
                try:
                    raw_body = e.read().decode("utf-8", errors="replace")
                    if raw_body:
                        try:
                            parsed_body = json.loads(raw_body)
                            msgs = parsed_body.get("errorMessages", [])
                            field_errs = parsed_body.get("errors", {})
                            parts = []
                            if msgs:
                                parts.extend(msgs)
                            if field_errs:
                                parts.extend([f"{k}: {v}" for k, v in field_errs.items()])
                            if parts:
                                err_msg = f"{e}: {'; '.join(parts)}"
                            else:
                                err_msg = f"{e}: {raw_body}"
                        except json.JSONDecodeError:
                            err_msg = f"{e}: {raw_body}"
                except Exception:
                    pass
                finally:
                    if hasattr(e, "close"):
                        try:
                            e.close()
                        except Exception:
                            pass
            return False, err_msg

    def create_subtasks(self, parent_key: str, tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Create Jira subtasks for planned tasks via POST /rest/api/2/issue.
        Each subtask payload sets parent, project, summary, description, and
        issuetype Sub-task. Failures are recorded per-subtask with status FAILED
        instead of fabricating keys; dry-run returns deterministic mock keys.
        @implements REQ-WORK-03
        """
        created = []
        parent_key = parent_key.upper().strip()
        project_key = parent_key.split("-")[0] if "-" in parent_key else "PROJ"

        for idx, task in enumerate(tasks, 1):
            summary = f"[{task.get('id', f'TASK-{idx}')}] {task.get('title', 'Untitled task')}"
            if self.dry_run:
                created.append({
                    "subtask_key": f"{project_key}-{1000 + idx}",
                    "parent_key": parent_key,
                    "summary": summary,
                    "is_mock": True,
                    "status": "CREATED_MOCK",
                })
                continue
            payload = {
                "fields": {
                    "project": {"key": project_key},
                    "parent": {"key": parent_key},
                    "summary": summary[:255],
                    "description": task.get("title", ""),
                    "issuetype": {"name": "Sub-task"},
                }
            }
            ok, data = self._post_json(f"{self.base_url}/rest/api/2/issue", payload)
            if ok:
                created.append({
                    "subtask_key": data.get("key", f"{project_key}-UNKNOWN"),
                    "parent_key": parent_key,
                    "summary": summary,
                    "is_mock": False,
                    "status": "CREATED",
                })
            else:
                created.append({
                    "subtask_key": None,
                    "parent_key": parent_key,
                    "summary": summary,
                    "is_mock": False,
                    "status": "FAILED",
                    "error": data,
                })

        self._record_sync("create_subtasks", parent_key, {"subtasks": created})
        return created

    def _record_sync(self, action: str, ticket_key: str, data: Any) -> None:
        """Record Jira interaction into session logs."""
        try:
            DEFAULT_RUNS_DIR.mkdir(parents=True, exist_ok=True)
            log_file = DEFAULT_RUNS_DIR / "jira_sync.jsonl"
            record = {
                "action": action,
                "ticket_key": ticket_key,
                "data": data
            }
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(record) + "\n")
        except Exception:
            pass


def render_plan_comment(plan_id: str, plan_title: str, plan_file: str,
                       target_branch: str, commit_sha: str,
                       tasks: List[Dict[str, Any]]) -> str:
    """
    Render JIRA_COMMENT_TEMPLATE.md for a packaged plan.
    Includes a wave-scheduled task summary table and the QA scenario count.
    Falls back to a plain-text summary if the template file is missing.
    @implements REQ-WORK-03
    """
    qa_count = sum(1 for t in tasks if t.get("qa_criteria"))
    try:
        waves = task_graph.compute_execution_waves(tasks)
        wave_lines = task_graph.generate_waves_markdown(waves).splitlines()
    except ValueError:
        wave_lines = []
    summary_rows = [
        "| Wave # | Task ID | Title | Dependencies |",
        "| :--- | :--- | :--- | :--- |",
    ]
    for line in wave_lines[2:]:
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        # wave table columns: Wave #, Task ID, Title, Component, Dependencies
        if len(cells) >= 5:
            summary_rows.append(
                f"| {cells[0]} | {cells[1]} | {cells[2]} | {cells[4]} |"
            )
        else:
            summary_rows.append(line)
    if len(summary_rows) == 2:
        summary_rows.append("| — | *No tasks scheduled* | — | — |")
    replacements = {
        "{{PLAN_ID}}": plan_id,
        "{{PLAN_TITLE}}": plan_title,
        "{{PLAN_FILE_PATH}}": plan_file,
        "{{TARGET_BRANCH}}": target_branch,
        "{{COMMIT_SHA}}": commit_sha,
        "{{TASK_SUMMARY_TABLE}}": "\n".join(summary_rows),
        "{{TOTAL_QA_SCENARIOS}}": str(qa_count),
    }
    try:
        template = COMMENT_TEMPLATE_FILE.read_text(encoding="utf-8")
    except OSError:
        return (
            f"Execution plan {plan_id} ({plan_title}) ready: "
            f"{len(tasks)} tasks, {qa_count} QA scenarios. "
            f"Branch {target_branch}, commit {commit_sha}."
        )
    for key, value in replacements.items():
        template = template.replace(key, value)
    return template


def main():
    parser = argparse.ArgumentParser(description="Jira Integration Client")
    parser.add_argument("action", choices=["fetch", "comment", "transition", "subtasks"], help="Action to perform")
    parser.add_argument("--ticket", required=True, help="Jira ticket key (e.g. PROJ-1024)")
    parser.add_argument("--text", help="Comment text or status name")
    parser.add_argument("--file", help="Path to plan markdown (used with 'subtasks' to load real tasks)")
    parser.add_argument("--dry-run", action="store_true", help="Force offline / dry-run mode")
    parser.add_argument("--json", action="store_true", help="Print JSON output")
    args = parser.parse_args()

    client = JiraClient(dry_run=args.dry_run)

    if args.action == "fetch":
        res = client.fetch_issue(args.ticket)
        if args.json:
            print(json.dumps(res, indent=2))
        else:
            print(f"=== Jira Issue: {res['key']} ===")
            print(f"Summary:     {res['summary']}")
            print(f"Status:      {res['status']}")
            print(f"Components:  {', '.join(res['components'])}")
            print(f"Acceptance Criteria ({len(res['acceptance_criteria'])} items):")
            for ac in res['acceptance_criteria']:
                print(f"  - {ac}")

    elif args.action == "comment":
        res = client.post_comment(args.ticket, args.text or "Execution plan prepared.")
        print(json.dumps(res, indent=2))

    elif args.action == "transition":
        res = client.transition_issue(args.ticket, args.text or "In Progress")
        print(json.dumps(res, indent=2))

    elif args.action == "subtasks":
        tasks: List[Dict[str, Any]] = []
        if args.file:
            plan_path = Path(args.file)
            if not plan_path.exists():
                print(f"[!] Plan file not found: {plan_path}", file=sys.stderr)
                sys.exit(1)
            tasks = task_graph.parse_tasks_from_markdown(
                plan_path.read_text(encoding="utf-8", errors="replace")
            )
            if not tasks:
                print(f"[!] No tasks parsed from {plan_path}", file=sys.stderr)
                sys.exit(1)
        elif args.text:
            try:
                raw = json.loads(args.text)
                tasks = raw if isinstance(raw, list) else raw.get("tasks", [])
            except json.JSONDecodeError as e:
                print(f"[!] --text must be a JSON task list: {e}", file=sys.stderr)
                sys.exit(1)
        else:
            print("[!] 'subtasks' requires --file <plan.md> or --text '<JSON task list>'",
                  file=sys.stderr)
            sys.exit(1)
        res = client.create_subtasks(args.ticket, tasks)
        print(json.dumps(res, indent=2))
        if any(s.get("status") == "FAILED" for s in res):
            sys.exit(1)


if __name__ == "__main__":
    main()
