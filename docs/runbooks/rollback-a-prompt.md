# Runbook: Rollback a Prompt

## Scenario

A deployed prompt version (e.g., `researcher/v2.md`) is performing poorly in production.

## Steps

1. **Identify the bad version** in `prompts/registry.yaml`:
   ```yaml
   roles:
     researcher:
       active_version: v2  # ← This is live
   ```

2. **Find the previous good version** (check eval scores in registry):
   ```yaml
   roles:
     researcher:
       active_version: v1  # ← Was good (eval_score: 0.92)
   ```

3. **Edit `prompts/registry.yaml`** to point to the previous version:
   ```yaml
   roles:
     researcher:
       active_version: v1  # ← Rollback
   ```

4. **Commit and push**:
   ```bash
   git commit -am "Rollback researcher prompt to v1"
   git push
   ```

5. **Verify via logs/traces** that new requests use the old prompt.

## Prevention

- Always test prompts locally with `make eval` before pushing
- Keep old versions for easy rollback
- Document why new version was deployed
