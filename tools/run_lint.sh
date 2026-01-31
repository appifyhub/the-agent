#!/usr/bin/env sh

. "$(dirname "$0")/messages.sh"

if [ ! -f "Pipfile" ]; then
    echowarn "No 'Pipfile' found. This script must be run from the project root!" >&2
    echoerr "Exiting..." -n >&2
    exit 1
fi

echoinfo "Installing dependencies in pipenv environment..."
pipenv install --dev

echoinfo "Running custom checks first..." -n
pipenv run python tools/check_spacing.py "$@"
spacing_exit_code=$?

echoinfo ""
echoinfo "Running ruff linter in pipenv environment..." -n
pipenv run ruff check "$@"
ruff_exit_code=$?

# Check if --fix was passed to avoid redundant suggestion
suggest_fix=true
for arg in "$@"; do
    if [ "$arg" = "--fix" ]; then
        suggest_fix=false
        break
    fi
done

if [ "$suggest_fix" = "true" ]; then
    echoinfo ""
    echoinfo "🧠  Remember, you can run this script with --fix to fix issues automatically." -n
fi

# Exit with failure if either check failed
if [ $spacing_exit_code -ne 0 ] || [ $ruff_exit_code -ne 0 ]; then
    exit 1
fi
