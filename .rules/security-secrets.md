# Security & Secrets Policy (Canonical)

**Law**: secrets live ONLY as Windows user/system environment variables. They are read from
the inherited environment at runtime. Nothing else.

## 1. Recognized secret variables (read, never written)

| Variable | Purpose |
|---|---|
| `OPENROUTER_API_KEY` | LLM routing via OpenRouter (used by the `openrouter-claude` profile) |
| `TWILIO_API_KEY` (+ SID vars when present) | Twilio messaging |
| `SENDGRID_API_KEY` | SendGrid email |
| `OPENMEMORY_API_KEY` | Local OpenMemory / mem0 (`oi-openmemory-prod`) |
| `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` (when set) | Direct provider access |

## 2. Hard rules

1. **Never** write a secret value into any file: no `.env`, no config JSON/TOML, no code,
   no prompt text, no log line, no memory record, no test fixture.
2. **Never** `echo`, `print`, or otherwise disclose a secret value in output. Referencing the
   variable *name* is always fine.
3. Config files reference secrets by *env var name* only (ClawTeam profiles do this via
   `api_key_env` / `env_map`, resolved at spawn time from the live environment).
4. Spawned agents inherit the user environment — read the variable when a call requires it;
   do not copy it anywhere.
5. If a secret seems missing, report `VAR_NAME missing from environment` and stop that
   integration. Do not work around it by embedding a key.

## 3. Setup verification

`scripts/setup_local.ps1` checks presence (names only, never values) and prints a
SET/MISSING table. Adding a new secret = set it as a Windows environment variable
(`[Environment]::SetEnvironmentVariable('NAME','value','User')`), then restart terminals.
