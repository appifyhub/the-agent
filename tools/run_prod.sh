#!/usr/bin/env sh

. "$(dirname "$0")/messages.sh"

if [ ! -f "Pipfile" ]; then
    echowarn "No 'Pipfile' found. This script must be run from the project root!" >&2
    echoerr "Exiting..." -n >&2
    exit 1
fi

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
sh "./tools/db_apply_head_schema.sh" -y

# Base command - we run with 2 workers, seems to be enough
CMD="pipenv run uvicorn --workers 2 --host 0.0.0.0 --port 80"
# Enable extensive logging if needed
echodebug "Enabling verbose logging..."
if [ "$VERBOSE" = "true" ]; then
    CMD="$CMD --log-level debug"
fi
# Finally, append the app name
CMD="$CMD src.fast_api:app"

# Run the command
echoinfo "Running the server in pipenv environment..." -n
eval "$CMD"
