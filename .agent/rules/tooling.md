---
trigger: always_on
---

### MANDATORY PROJECT RULES

#### Environment Management

- ALWAYS use `pipenv` for dependency management and Python command execution
- ALL commands must be run from project root (where Pipfile exists)
- Never use `pip` directly - always use `pipenv install` or `pipenv run`

#### Database Migrations

- Ask the user to run `./tools/db_generate_migration.sh -y` to generate new Alembic migrations (auto-generates based on model changes)
- Ask the user to run `./tools/db_apply_migration.sh` to apply migrations to database (only with user's approval)
- Always check if model imports in `src/db/alembic/env.py` are up to date before running `db_generate_migration.sh`

#### Development Workflow

- Use `./tools/run_dev.sh` for development server (includes hot reload, verbose logging, dev API key)
- Use `./tools/run_tests.sh` for running `pytest` (handles `.env` setup automatically), never anything raw
- Use `./tools/run_lint.sh --fix` for code quality checks with `ruff` (this flag will auto-fix issues it can)
- Use `./tools/run_prod.sh` for production runs

#### Code Quality

- Always run linting before commits: `./tools/run_lint.sh --fix`
- All scripts handle environment setup automatically (PYTHONPATH, .env files)

#### Project Structure

- All scripts are in `tools` directory and use common `messages.sh` for colored output
- Scripts validate project root location and fail safely if run from wrong directory
- Version is managed through `.version` file in project root
- You can see other rules in `.cursor` directory, if you need those rules
- You can see the CI/CD pipeline in `.github/workflows` directory
- You can see the API docs in `docs/` directory (keep it updated!)

#### LLM/AI Rules

- Never write plans or walkthroughs unless the user specifically asks you to
- Never assume anything. Ask validating questions. Sync with the user to validate your assumptions. Optimize for accuracy, not speed
- Consistency is key. Look at coding patterns in and around the file you are editing as if you have OCD
- Tests must run offline. Write tests if the unit is simply testable. If the unit requires extensive mocking, advise the user before proceeding