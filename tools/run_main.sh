#!/usr/bin/env sh

. "$(dirname "$0")/messages.sh"

if [ ! -f "Pipfile" ]; then
    echowarn "No 'Pipfile' found. This script must be run from the project root!" >&2
    echoerr "Exiting..." -n >&2
    exit 1
fi

echoinfo "Installing dependencies in pipenv environment..."
pipenv install

echoinfo "Running the server in pipenv environment..." -n

# Base command - we run with 2 workers, seems to be enough
CMD="pipenv run gunicorn \
    -w 2 \
    -k uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:80 \
    --preload \
    src.fast_api:app"

# Add logging options if VERBOSE is true
if [ "$VERBOSE" = "true" ]; then
    echoinfo "Enabling verbose logging..."
    CMD="$CMD --log-level debug --access-logfile - --error-logfile -"
fi

# Run the command
echoinfo "Running the server in pipenv environment..." -n
eval "$CMD"
