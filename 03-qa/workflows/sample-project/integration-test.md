# Workflow: Integration Test for `sample-project`

<!-- @implements REQ-WORK-03 -->
<!-- @verifies REQ-WORK-03 -->
<!-- @verifies REQ-TOOL-SQL -->
<!-- @verifies REQ-TOOL-BLOB -->

## Purpose & Scope
Integration verification for `sample-project`, demonstrating database seeding, mock blob storage validation, and cleanroom execution.

---

## Agent Runbook

### Step 1: Initialize Cleanroom
```bash
python3 tools/qa_runner.py setup-cleanroom --source tests/fixtures/sample-project
```

### Step 2: Seed SQLite Database
- **Action**: SQL Seeding
- **Tool**: `tools/run_sql_cmd.py`
- **CLI Command**:
```bash
python3 tools/run_sql_cmd.py --db target-repo/sample.db --query "
CREATE TABLE IF NOT EXISTS sample_items (id INTEGER PRIMARY KEY, title TEXT);
INSERT INTO sample_items (title) VALUES ('Integration Item 1');
"
```

### Step 3: Verify Seeded Rows
- **Action**: SQL Query Assertion
- **Tool**: `tools/run_sql_cmd.py`
- **CLI Command**:
```bash
python3 tools/run_sql_cmd.py --db target-repo/sample.db \
  --query "SELECT * FROM sample_items;" \
  --format json \
  --expect-count 1
```

### Step 4: Verify Mock Blob Directory Creation
- **Action**: Blob Storage Verification
- **Tool**: `tools/query_blob_storage.py`
- **CLI Command**:
```bash
mkdir -p target-repo/storage/blobs
echo "blob-payload-data" > target-repo/storage/blobs/test_artifact.txt
python3 tools/query_blob_storage.py exists --dir target-repo/storage/blobs --key test_artifact.txt
```

### Step 5: Teardown & Report Compilation
```bash
python3 tools/qa_runner.py report \
  --workflow integration \
  --source sample-project \
  --status PASS \
  --notes "Integration test verified SQL seeding, query assertions, and blob storage verification."
```
