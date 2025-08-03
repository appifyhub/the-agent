#!/usr/bin/env sh

. "$(dirname "$0")/messages.sh"

if [ ! -f "Pipfile" ]; then
    echowarn "No 'Pipfile' found. This script must be run from the project root!" >&2
    echoerr "Exiting..." -n >&2
    exit 1
fi

# Read version file, fail if missing
if [ ! -f ".version" ]; then
    echoerr "No '.version' file found. This script must be run from the project root!" >&2
    echoerr "Exiting..." -n >&2
    exit 1
fi

# Export version for config.py
export VERSION="$(cat .version)"
export LOG_LEVEL=${LOG_LEVEL:-info}
echoinfo "Detected version: ${VERSION}"

# Generate a random API key in case it's not set already
generate_api_key() {
    echoinfo "Generating a random API key..."
    API_KEY=$(openssl rand -hex 8 | tr 'a-f' 'A-F' | sed 's/.\{4\}/&-/g;s/-$//')
    echodebug "API Key: '$API_KEY'"
    export API_KEY="$API_KEY"
}
if [ -z "$API_KEY" ]; then
    generate_api_key
else
    echoinfo "Using the environment API key."
fi

# Run database migrations if needed
echoinfo "Running database migrations..."
sh "./tools/db_apply_migration.sh" -y

echoinfo "Running the server in pipenv environment..." -n

# We run with 2 workers in production
pipenv run uvicorn \
    --workers 2 \
    --host 0.0.0.0 \
    --port 80 \
    --log-level ${LOG_LEVEL} \
    src.fast_api:app
