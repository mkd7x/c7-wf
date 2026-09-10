# Step Guide: Blob Storage Verification & Mocking

<!-- @verifies REQ-TOOL-BLOB -->

## Purpose
Use this step guide when an agent needs to upload test files into local mock blob storage or verify that an API endpoint created or modified an object in blob storage.

---

## Tool Reference
**Tool**: `tools/query_blob_storage.py`

### CLI Subcommands
- `list --dir <bucket-dir> [--prefix <key-prefix>] [--json]`: List objects in store
- `exists --dir <bucket-dir> --key <object-key>`: Check if a blob exists (exits 0 if found, 1 if not)
- `get --dir <bucket-dir> --key <object-key> [--out <dest>]`: Read/download blob
- `put --dir <bucket-dir> --key <object-key> --file <source>`: Upload file into blob storage
- `delete --dir <bucket-dir> --key <object-key>`: Remove a blob

---

## Step Definition Schema

```json
{
  "step_type": "blob_storage",
  "name": "Verify Document Upload",
  "storage_dir": "target-repo/storage/documents",
  "action": "exists",
  "key": "user_uploads/contract_101.pdf"
}
```

---

## Example Workflow Steps

### Example 1: Uploading a Test Fixture into Blob Storage
```markdown
### Step: Pre-populate Storage Fixture
- **Action**: Blob Put
- **Tool**: `tools/query_blob_storage.py`
- **CLI Execution**:
```bash
python3 tools/query_blob_storage.py put \
  --dir target-repo/storage/uploads \
  --key "fixtures/test_avatar.png" \
  --file fixtures/sample_avatar.png
```
```

### Example 2: Asserting File Creation After Export API
```markdown
### Step: Verify Generated PDF in Blob Store
- **Action**: Blob Exists Assertion
- **Tool**: `tools/query_blob_storage.py`
- **CLI Execution**:
```bash
python3 tools/query_blob_storage.py exists \
  --dir target-repo/storage/exports \
  --key "invoices/inv_2026_09.pdf"
```
```
