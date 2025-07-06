#!/usr/bin/env sh

. "$(dirname "$0")/messages.sh"

if [ ! -f "Pipfile" ]; then
    echowarn "No 'Pipfile' found. This script must be run from the project root!" >&2
    echoerr "Exiting..." -n >&2
    exit 1
fi

echoinfo "Have you imported the latest models in 'src/db/alembic/env.py' imports? (y/n) "
read -r RESPONSE
if [ ! "$RESPONSE" = "Y" ]; then
    echowarn "Let's import the latest models before continuing."
    echoerr "Exiting..." -n >&2
    exit 1
fi

echoinfo "What would you like to call this schema? "
read -r SCHEMA_NAME_RAW
SCHEMA_NAME=$(echo "$SCHEMA_NAME_RAW" | xargs)

if [ -z "$SCHEMA_NAME" ]; then
    echowarn "You must provide a schema name."
    echoerr "Exiting..." -n >&2
    exit 1
fi

echoinfo "Running the schema migration generator..." -n
pipenv run alembic revision --autogenerate -m "$SCHEMA_NAME"
