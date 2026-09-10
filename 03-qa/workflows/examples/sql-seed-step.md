# Step Guide: SQL Seeding & Database Assertions

<!-- @verifies REQ-TOOL-SQL -->

## Purpose
Use this step guide when an agent needs to execute database migrations, seed test records, or assert database state before/after test operations.

---

## Tool Reference
**Tool**: `tools/run_sql_cmd.py`

### CLI Flag Reference
- `--db`, `-d`: SQLite database path or connection URI
- `--query`, `-q`: SQL statement(s) to execute
- `--file`, `-f`: Path to `.sql` file to execute
- `--format`: Output format for results (`table`, `json`, `csv`)
- `--read-only`: Disallow mutations (used during state verification)
- `--expect-count`: Assert that exactly N rows are returned by a query

---

## Step Definition Schema

```json
{
  "step_type": "sql_execution",
  "name": "Seed Initial Data",
  "database": "target-repo/data/app.db",
  "operation": "seed",
  "sql": "INSERT OR IGNORE INTO users (id, name, email) VALUES (1, 'QA Lead', 'qa@test.com');",
  "assertions": {
    "expected_rows_affected": 1
  }
}
```

---

## Example Workflow Steps

### Example 1: Schema Initialization & Seeding
```markdown
### Step: Initialize Database Schema and Test User
- **Action**: SQL Seeding
- **Tool**: `tools/run_sql_cmd.py`
- **CLI Execution**:
```bash
python3 tools/run_sql_cmd.py --db target-repo/data/app.db --query "
CREATE TABLE IF NOT EXISTS accounts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT UNIQUE NOT NULL,
  balance REAL DEFAULT 0.0
);
INSERT OR IGNORE INTO accounts (username, balance) VALUES ('test_user', 500.0);
"
```
```

### Example 2: Asserting Post-API Database Mutation
```markdown
### Step: Verify Account Balance Updated
- **Action**: SQL Query Assertion
- **Tool**: `tools/run_sql_cmd.py`
- **CLI Execution**:
```bash
python3 tools/run_sql_cmd.py --db target-repo/data/app.db \
  --query "SELECT balance FROM accounts WHERE username='test_user' AND balance=450.0;" \
  --format json \
  --expect-count 1
```
```
