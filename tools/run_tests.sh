#!/usr/bin/env sh

. "$(dirname "$0")/messages.sh"

if [ ! -f "Pipfile" ]; then
    echowarn "No 'Pipfile' found. This script must be run from the project root!" >&2
    echoerr "Exiting..." -n >&2
    exit 1
fi

echoinfo "Installing dependencies in pipenv environment..."
pipenv install --dev
pipenv install

# Function to revert the .env files
revert_env_files() {
    echoinfo "Reverting .env files..."
    mv .env.backup .env
    rm -f .env.backup
}

# Set PYTHONPATH for pytest
echoinfo "Setting up .env files for test..."
mv .env .env.backup
echo "PYTHONPATH=\"\${PWD}/src:\${PWD}/test\"" > .env
echo "VERBOSE=True" >> .env

# Set a trap to revert environment files on script exit
trap revert_env_files EXIT

echoinfo "Running tests in pipenv environment..." -n
pipenv run pytest -v test
