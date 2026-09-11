# SPEC-PLAN-001: Codebase Context Discovery

## 1. Purpose & Scope
This specification defines the functional requirements for inspecting target codebases prior to planning. The discovery engine scans the source repository to identify runtime environments, dependency manifests, web/API frameworks, database schemas, existing Architectural Decision Records (ADRs), and route definitions.

---

## 2. Functional Requirements

| Req ID | Requirement Title | Specification Description |
| :--- | :--- | :--- |
| **REQ-DISC-01** | Stack & Framework Detection | The discovery tool must inspect repository manifests (`package.json`, `pyproject.toml`, `requirements.txt`, `*.csproj`, `go.mod`, `pom.xml`, `Cargo.toml`) and accurately detect runtime languages, web frameworks, and test frameworks. |
| **REQ-DISC-02** | Structural Boundary Discovery | The discovery tool must identify key architectural directories (e.g., Clean Architecture layers: domain, application, infrastructure, api/web) and detect existing ADRs or architecture documentation (`docs/adr`, `spec/`, etc.). |
| **REQ-DISC-03** | Interface & Route Discovery | The discovery tool must detect API routing files, controllers, OpenAPI/Swagger specifications, and database schema definition files (e.g., SQL migrations, EF Core contexts, Prisma schemas). |
| **REQ-DISC-04** | Context Snapshotting | Discovered project context must be serialized into a deterministic JSON snapshot under `01-plan/runs/latest/context.json` so planning agents do not need to repeatedly rescan the disk. |

---

## 3. Acceptance Criteria
1. When pointed to a target directory, `context_discovery.py` outputs a structured dictionary containing `project_type`, `language`, `frameworks`, `routes_found`, `schemas_found`, and `existing_adrs`.
2. Missing manifests or unknown languages degrade gracefully without unhandled exceptions.
3. Discovery runs within 5 seconds for typical repositories up to 10,000 files.
