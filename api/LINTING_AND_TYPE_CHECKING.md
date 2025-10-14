# Linting and Type Checking Guide

This document explains how to run type checking and linting on the Python codebase, equivalent to TypeScript's `tsc` and `eslint`.

## Quick Start

```bash
# Install dependencies
npm install              # Installs pyright
pip install ruff mypy    # Python linters/type checkers

# Run type checking (like tsc)
npm run typecheck

# Run linting (like eslint)
npm run lint

# Run everything (lint + typecheck + tests)
npm run check
```

## Type Checking (Python equivalent of `tsc`)

### Option 1: Pyright (Recommended - Same as VS Code Pylance)

Pyright is the type checker used by VS Code's Pylance extension. It's the fastest and most accurate.

```bash
# Run type checking (no install needed with npx)
npx pyright

# Or via npm script
npm run typecheck

# Watch mode (re-runs on file changes)
npm run typecheck:watch
```

**Configuration:** `pyrightconfig.json`

### Option 2: mypy (Alternative)

mypy is another popular Python type checker.

```bash
# Install
pip install mypy

# Run type checking
mypy functions/ shared/ services/ models/ --config-file=pyproject.toml
```

**Configuration:** `pyproject.toml` under `[tool.mypy]`

## Linting (Python equivalent of `eslint`)

### Ruff (Recommended - Fast, All-in-One)

Ruff is a fast linter written in Rust that replaces multiple tools (flake8, isort, pyupgrade, etc.)

```bash
# Install
pip install ruff

# Check for issues
ruff check .

# Fix auto-fixable issues
ruff check --fix .

# Format code (like prettier)
ruff format .

# Or via npm scripts
npm run lint        # Check only
npm run lint:fix    # Fix issues
npm run format      # Format code
```

**Configuration:** `pyproject.toml` under `[tool.ruff]`

## CI/CD Integration

Add to your GitHub Actions workflow:

```yaml
- name: Install dependencies
  run: |
    npm install
    pip install ruff mypy

- name: Run type checking
  run: npm run typecheck

- name: Run linting
  run: npm run lint

- name: Run tests
  run: npm run test
```

## VS Code Integration

### Recommended Extensions

1. **Pylance** (Microsoft) - Provides type checking as you type
2. **Ruff** (Astral Software) - Provides linting and formatting

### Settings (.vscode/settings.json)

```json
{
  "python.languageServer": "Pylance",
  "python.analysis.typeCheckingMode": "basic",
  "python.linting.enabled": true,
  "python.linting.ruffEnabled": true,
  "python.formatting.provider": "none",
  "[python]": {
    "editor.formatOnSave": true,
    "editor.defaultFormatter": "charliermarsh.ruff",
    "editor.codeActionsOnSave": {
      "source.fixAll": true,
      "source.organizeImports": true
    }
  }
}
```

## Fixing Common Type Errors

See [TYPE_CHECKING_GUIDE.md](./TYPE_CHECKING_GUIDE.md) for detailed solutions to common type checking issues.

### Quick Fixes

**Issue:** `Cannot access attribute "context" for class "HttpRequest"`

```python
# ❌ Before
context = req.context

# ✅ After
from shared.types import get_context
context = get_context(req)
```

**Issue:** `Argument of type "str | None" cannot be assigned to parameter of type "str"`

```python
# ❌ Before
param = req.route_params.get("param")

# ✅ After
from shared.types import get_route_param
param = get_route_param(req, "param")
```

## Commands Summary

| Task | Command | TypeScript Equivalent |
|------|---------|----------------------|
| Type check | `npm run typecheck` | `tsc --noEmit` |
| Type check (watch) | `npm run typecheck:watch` | `tsc --noEmit --watch` |
| Lint | `npm run lint` | `eslint .` |
| Lint + fix | `npm run lint:fix` | `eslint --fix .` |
| Format | `npm run format` | `prettier --write .` |
| Run all checks | `npm run check` | N/A (custom script) |
| Run tests | `npm run test` | `jest` or `vitest` |

## Configuration Files

- **pyrightconfig.json** - Pyright type checker configuration
- **pyproject.toml** - Python project configuration (mypy, ruff, etc.)
- **package.json** - npm scripts for running checks

## Pre-commit Hooks (Optional)

Install pre-commit to run checks automatically:

```bash
pip install pre-commit

# Create .pre-commit-config.yaml
cat > .pre-commit-config.yaml << 'EOF'
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.9
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.8.0
    hooks:
      - id: mypy
        additional_dependencies: [types-all]
EOF

# Install hooks
pre-commit install
```

## Troubleshooting

### Pyright not finding modules

Add to `pyrightconfig.json`:

```json
{
  "extraPaths": [".", "shared", "functions", "services"]
}
```

### Too many type errors

Start with basic mode:

```json
{
  "typeCheckingMode": "basic"  // or "off" to disable
}
```

### Import errors

Add to `pyproject.toml`:

```toml
[tool.mypy]
ignore_missing_imports = true
```

## Performance Comparison

| Tool | Speed | Features |
|------|-------|----------|
| Pyright | ⚡⚡⚡ Fastest | Type checking |
| mypy | ⚡⚡ Fast | Type checking |
| Ruff | ⚡⚡⚡ Fastest | Linting + Formatting |
| flake8 | ⚡ Slow | Linting only |

**Recommendation:** Use Pyright + Ruff for best performance.
