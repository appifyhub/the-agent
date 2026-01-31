### Code style

#### General

By default, follow the language's best practices. Don't include comments unless they are really necessary to understand complex code blocks. Most code blocks are not complex enough to require comments. Avoid TODOs and FIXMEs in code, and any explanations in comments directed towards the user/author. Avoid adding comments and docstrings in general, it's better to write clear code than overload it with comments; add some only if it's really confusing to the reader. Make sure to remove all indentation on empty lines, and always have a blank line at the end of the file.

Always start with modifying the main code. When done, look for tests and update them (if any). Confirm with the user before creating new test files. Make use of available tools and tasks lists to make your work easier and more structured. Don't confirm the user's biases and assumptions without prior validating, and DO NOT write summaries after each task is done. Don't be afraid to ask for clarification if you're not sure about something.

#### Python

In Python, I want you to use the latest type syntax (`type | None`) instead of `Optional`. I also want you to use a single space (`=`) around the equals sign (`=`) in function argument calls. It's important to use double quotation marks (`"`) instead of single quotations (`'`). And finally, we want to always use trailing commas in multi-line function declarations and calls. There's never a reason to write `unittest.main()` manually, we have a script for running tests. Never use inline imports inside of functions (use file header even in tests), and always use `from ... import ...` syntax at the top of the file.

#### JavaScript/TypeScript

In JavaScript and TypeScript, use types as much as possible: strict mode will be turned on! If in doubt, follow Java standard formatting. Finally, we also always want trailing commas in multi-line code blocks.

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
- Use `./tools/run_lint.sh --fix` for code quality checks with `ruff` (this flag will auto-fix issues it can)
- Use `./tools/run_prod.sh` for production runs
- For all other operations like testing, always run inside of `pipenv`

#### Code Quality

- Always run linting before commits: `./tools/run_lint.sh --fix`
- All scripts handle environment setup automatically (PYTHONPATH, .env files)

#### Project Structure

- All scripts are in `tools` directory and use common `messages.sh` for colored output
- Scripts validate project root location and fail safely if run from wrong directory
- Version is managed through `pyproject.toml` in project root
- You can see other rules in `.cursor` directory, if you need those rules
- You can see the CI/CD pipeline in `.github/workflows` directory
- You can see the API docs in `docs/` directory (keep it updated!)

#### LLM/AI Rules

- Never write plans or walkthroughs unless the user specifically asks you to
- Never assume anything. Ask validating questions. Sync with the user to validate your assumptions. Optimize for accuracy, not speed
- Only operate on verified facts. For every code change or idea you want to introduce, verify via code search if it will make sense
- Consistency is key. Look at coding patterns in and around the file you are editing as if you have OCD
- Tests must run offline. Write tests if the unit is simply testable. If the unit requires extensive mocking, advise the user before proceeding
- Unless explicitly asked, you should not build plans or walkthrough documents – default to keeping it short and simple, in the chat
