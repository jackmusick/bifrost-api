# msp-automation-platform Development Guidelines

Auto-generated from all feature plans. Last updated: 2025-10-12

## Active Technologies
- Python 3.11 (Azure Functions v2 programming model) + azure-functions, azure-data-tables, Pydantic for models, GitHub Actions for CI/CD (002-i-want-to)
- Python 3.11 (Azure Functions v2 programming model) + azure-functions, azure-data-tables, aiohttp (for OAuth HTTP calls), pydantic (for models), cryptography (for token encryption) (004-oauth-helper-for)
- Azure Table Storage (OAuth configs, credentials, status), Azure Key Vault (encryption keys for credentials at rest) (004-oauth-helper-for)

## Project Structure
```
src/
tests/
```

## Commands
cd src [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] pytest [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] ruff check .

## Code Style
Python 3.11 (Azure Functions v2 programming model): Follow standard conventions

## Recent Changes
- 004-oauth-helper-for: Added Python 3.11 (Azure Functions v2 programming model) + azure-functions, azure-data-tables, aiohttp (for OAuth HTTP calls), pydantic (for models), cryptography (for token encryption)
- 002-i-want-to: Added Python 3.11 (Azure Functions v2 programming model) + azure-functions, azure-data-tables, Pydantic for models, GitHub Actions for CI/CD

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
