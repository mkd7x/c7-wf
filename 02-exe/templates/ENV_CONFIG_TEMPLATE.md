# Environment Profile Configuration Template

Use this format to define repository environment profiles, secrets, and provider mappings:

```json
{
  "$schema": "https://c7-wf.local/schemas/exe-env-config.json",
  "profile": "local-dev",
  "template_file": ".env.example",
  "destination_file": ".env",
  "variables": {
    "NODE_ENV": "development",
    "LOG_LEVEL": "debug",
    "PORT": "3000"
  },
  "secrets": [
    {
      "name": "DATABASE_URL",
      "provider": "env-var",
      "reference": "LOCAL_DATABASE_URL",
      "fallback": "postgresql://postgres:postgres@localhost:5432/app_dev"
    },
    {
      "name": "THIRD_PARTY_API_KEY",
      "provider": "1password",
      "reference": "op://dev/third-party/api-key",
      "fallback": "mock-api-key-test"
    },
    {
      "name": "AWS_SECRET_KEY",
      "provider": "aws-secrets",
      "reference": "dev/app/keys:secret_key",
      "fallback": "mock-aws-secret"
    }
  ]
}
```
