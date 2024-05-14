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

echoinfo "Setting up local API_KEY: '${API_KEY}' and VERBOSE mode..."
echoinfo "Running dev server..." -n

# We run with 1 worker in dev mode
pipenv run gunicorn \
    -w 1 \
    -k uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:80 \
    --preload \
    src.main:app \
    --log-level debug \
    --access-logfile - \
    --error-logfile -
