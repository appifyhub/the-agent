FROM python:3.12.12-slim

# Install system dependencies and pipenv
RUN apt-get update && apt-get install -y --no-install-recommends \
    libffi8 libssl3 ca-certificates ffmpeg \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir pipenv

# Set up working directory
WORKDIR /app

# Copy the contents over (respecting .dockerignore)
COPY . .
RUN mv .github/ISSUE_TEMPLATE src/templates && rm -rf .github

# Install the dependencies
RUN pipenv install --deploy --ignore-pipfile --verbose \
    && find /usr/local/lib/python3.12 -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true \
    && find /usr/local/lib/python3.12 -type f -name "*.pyc" -delete \
    && rm -rf /root/.cache/pip /root/.cache/pipenv

# Set the entrypoint command
CMD ["sh", "tools/run_prod.sh"]
