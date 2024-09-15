FROM python:3.12.6-alpine

# Install system dependencies, build dependencies, and pipenv
RUN apk add --no-cache libffi openssl ca-certificates ffmpeg \
    && apk add --no-cache --virtual .build-deps make clang-dev gcc g++ musl-dev \
    && pip install --no-cache-dir pipenv

# Set up working directory
WORKDIR /app

# Copy the contents over (respecting .dockerignore)
COPY . .

# Install the dependencies
RUN pipenv install --deploy --ignore-pipfile --verbose \
    && apk del .build-deps

# Set the entrypoint command
CMD ["sh", "tools/run_prod.sh"]
