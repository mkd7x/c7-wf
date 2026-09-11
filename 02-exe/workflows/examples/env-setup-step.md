# Example: Environment Setup Step

<!-- @verifies REQ-ENV-01 -->
<!-- @verifies REQ-ENV-03 -->

Synthesize local `.env` configuration file from `.env.example`, resolving required secrets and verifying Git exclusion:

```bash
python3 tools/env_manager.py setup \
  --workspace workspace \
  --template .env.example \
  --output .env
```
