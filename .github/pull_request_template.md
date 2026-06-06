## PR Checklist

- [ ] All tests pass: `make test`
- [ ] Linting passes: `make lint`
- [ ] Eval passes (if agent/tool/prompt changes): `make eval`
- [ ] No secrets committed (check `.env`, API keys)
- [ ] Prompt versions are immutable (v1.md not edited if shipped)
- [ ] Updated `prompts/registry.yaml` if adding new prompt version
- [ ] Added unit test(s) for new functionality
- [ ] Updated documentation if architectural changes
- [ ] Eval report attached (if applicable)

## Description

_Describe your changes and why they're needed._

## Type of Change

- [ ] Bug fix
- [ ] New feature
- [ ] Prompt update (describe delta)
- [ ] Agent/tool modification
- [ ] Infrastructure / CI/CD
- [ ] Documentation

## Related Issues

Closes #(issue number)

## Eval Impact

- [ ] No eval impact (refactoring, docs, etc.)
- [ ] Regression detected (justify below)
- [ ] Score improved by X%

_If regression, explain:_
