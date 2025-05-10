#!/usr/bin/env sh

. "$(dirname "$0")/messages.sh"

if [ ! -f "Pipfile" ]; then
    echowarn "No 'Pipfile' found. This script must be run from the project root!" >&2
    echoerr "Exiting..." -n >&2
    exit 1
fi

export VERBOSE=true
export API_KEY=developer

echoinfo "Installing dependencies in pipenv dev environment..." -n
pipenv install
pipenv install --dev

# Read version file, fail if missing
if [ ! -f ".version" ]; then
    echoerr "No '.version' file found. This script must be run from the project root!" >&2
    echoerr "Exiting..." -n >&2
    exit 1
fi

# Export version for config.py
export VERSION="$(cat .version)"
echoinfo "Detected version: ${VERSION}"

echoinfo "Setting up local API_KEY: '${API_KEY}' and VERBOSE mode..."
echoinfo "Running dev server..." -n

# We run with 1 worker in dev mode (with hot reload)
pipenv run uvicorn \
    --workers 1 \
    --host 0.0.0.0 \
    --port 80 \
    --reload \
    --log-level debug \
    src.fast_api:app
