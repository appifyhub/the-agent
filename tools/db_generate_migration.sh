#!/usr/bin/env sh

. "$(dirname "$0")/messages.sh"

if [ ! -f "Pipfile" ]; then
    echowarn "No 'Pipfile' found. This script must be run from the project root!" >&2
    echoerr "Exiting..." -n >&2
    exit 1
fi

# Parse arguments
AUTO_YES=false
SCHEMA_NAME=""

while [ $# -gt 0 ]; do
    case $1 in
        -y)
            AUTO_YES=true
            shift
            ;;
        --name)
            SCHEMA_NAME="$2"
            shift 2
            ;;
        *)
            echowarn "Unknown option: $1"
            echoerr "Usage: $0 [-y] [--name SCHEMA_NAME]"
            echoerr "Exiting..." -n >&2
            exit 1
            ;;
    esac
done

if [ "$AUTO_YES" != "true" ]; then
    echoinfo "Have you imported the latest models in 'src/db/alembic/env.py' imports? (y/n) "
    read -r RESPONSE
    if [ "$RESPONSE" != "Y" ] && [ "$RESPONSE" != "y" ]; then
        echowarn "Let's import the latest models before continuing."
        echoerr "Exiting..." -n >&2
        exit 1
    fi
fi

if [ -z "$SCHEMA_NAME" ]; then
    if [ "$AUTO_YES" != "true" ]; then
        echoinfo "What would you like to call this schema? "
        read -r SCHEMA_NAME_RAW
        SCHEMA_NAME=$(echo "$SCHEMA_NAME_RAW" | xargs)
    fi
fi

if [ -z "$SCHEMA_NAME" ]; then
    echowarn "You must provide a schema name."
    echoerr "Exiting..." -n >&2
    exit 1
fi

echoinfo "Running the schema migration generator..." -n
pipenv run alembic revision --autogenerate -m "$SCHEMA_NAME"
