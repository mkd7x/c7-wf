# SPEC-PLAN-003: Task Decomposition & DAG Scheduling

## 1. Purpose & Scope
This specification defines the functional requirements for decomposing architectural designs into granular, atomic implementation tasks. Tasks must be organized into a Directed Acyclic Graph (DAG) with validated dependencies and sequenced into parallelizable execution waves for `02-exe`.

---

## 2. Functional Requirements

| Req ID | Requirement Title | Specification Description |
| :--- | :--- | :--- |
| **REQ-TASK-01** | Atomic Task Decomposition | Plans must break down work into atomic units where each task possesses a unique identifier (`TASK-XX` or `PROJ-KEY-TX`), title, explicit files to touch, clear Definition of Done (DoD), and test criteria. |
| **REQ-TASK-02** | Explicit Dependency Declaration | Every task in the plan must explicitly declare prerequisite dependencies using the `depends_on: [...]` attribute. Independent root tasks declare `depends_on: []`. |
| **REQ-TASK-03** | DAG Validation & Cycle Detection | The framework must provide a graph validation tool (`task_graph.py`) that parses task dependencies, detects circular references, flags non-existent dependency IDs, and prevents invalid graphs from executing. |
| **REQ-TASK-04** | Topological Wave Batching | The framework must compute topological ordering and organize tasks into discrete execution waves (Wave 1: schema/migrations, Wave 2: core services, Wave 3: controllers/endpoints, Wave 4: tests) for parallel or sequenced execution by `02-exe`. |

---

## 3. Acceptance Criteria
1. `task_graph.py` successfully parses Markdown task lists and builds a directed graph.
2. If task A depends on B and B depends on A, `task_graph.py` exits with code 1 and identifies the cycle.
3. Execution waves group independent tasks together so that tasks in Wave N only depend on completed tasks from Waves < N.
