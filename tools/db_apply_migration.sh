#!/usr/bin/env sh

. "$(dirname "$0")/messages.sh"

if [ ! -f "Pipfile" ]; then
    echowarn "WARN:     No 'Pipfile' found. This script must be run from the project root!" >&2
    echoerr "ERROR:    Exiting..." -n >&2
    exit 1
fi

if [ "$1" != "-y" ]; then
    echoinfo "Have you applied all previous schemas to the database? (y/n) "
    read -r RESPONSE
    if [ "$RESPONSE" != "Y" ] && [ "$RESPONSE" != "y" ]; then
        echowarn "WARN:     Let's make sure that's done first."
        echoerr "ERROR:    Exiting..." -n >&2
        exit 1
    fi
fi

echoinfo "INFO:     Running the database upgrade..." -n
pipenv run alembic upgrade head
