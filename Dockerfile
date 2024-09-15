FROM python:3.12.6-alpine

# Install dependencies
RUN apk add --no-cache libffi openssl ca-certificates ffmpeg \
    && pip install --no-cache-dir pipenv

# Set up working directory
WORKDIR /app

# Copy the contents over (respecting .dockerignore)
COPY . .

# Install the dependencies
RUN pipenv install --deploy --ignore-pipfile

# Set the entrypoint command
CMD ["sh", "tools/run_prod.sh"]
