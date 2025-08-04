#!/usr/bin/env sh

. "$(dirname "$0")/messages.sh"

if [ ! -f "Pipfile" ]; then
    echowarn "WARN:     No 'Pipfile' found. This script must be run from the project root!" >&2
    echoerr "ERROR:    Exiting..." -n >&2
    exit 1
fi

echoinfo "INFO:     Installing dependencies in pipenv dev environment..." -n
pipenv install --dev

echoinfo "INFO:     Running dev server via main.py..." -n

# Run the FastAPI app directly in development mode
pipenv run python src/main.py --dev
