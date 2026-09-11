# Example: Credential Resolution Step

<!-- @verifies REQ-ENV-02 -->

Fetch credentials using pluggable provider adapters (1Password, AWS Secrets Manager, Doppler, Vault, or environment variables):

```bash
# Example 1: Resolve from 1Password
python3 tools/env_manager.py fetch-secret --provider 1password --ref "op://dev/database/password"

# Example 2: Resolve from AWS Secrets Manager
python3 tools/env_manager.py fetch-secret --provider aws-secrets --ref "prod/api/key"

# Example 3: Resolve from environment variable
python3 tools/env_manager.py fetch-secret --provider env-var --ref "LOCAL_DEV_SECRET"
```
