#!/usr/bin/env sh

. "$(dirname "$0")/messages.sh"

if [ ! -f "Pipfile" ]; then
    echowarn "No 'Pipfile' found. This script must be run from the project root!" >&2
    echoerr "Exiting..." -n >&2
    exit 1
fi

echoinfo "Installing dependencies in pipenv environment..."
pipenv install

echoinfo "Running tests in pipenv environment..." -n
pipenv run pytest -v test
