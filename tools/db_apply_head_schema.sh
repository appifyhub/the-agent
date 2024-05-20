#!/usr/bin/env sh

. "$(dirname "$0")/messages.sh"

if [ ! -f "Pipfile" ]; then
    echowarn "No 'Pipfile' found. This script must be run from the project root!" >&2
    echoerr "Exiting..." -n >&2
    exit 1
fi

if [ "$1" != "-y" ]; then
    echoinfo "Have you created all previous schemas and applied them to the database? (Y/n) "
    read -r RESPONSE
    if [ ! "$RESPONSE" = "Y" ]; then
        echowarn "Let's make sure that's done first."
        echoerr "Exiting..." -n >&2
        exit 1
    fi
fi

echoinfo "Running the database upgrade..." -n
pipenv run alembic upgrade head
