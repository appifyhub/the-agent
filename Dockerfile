FROM python:3.12.3-alpine

# Install dependencies
RUN apk add --no-cache \
      libffi \
      openssl \
      ca-certificates \
    && \
    pip install --no-cache-dir \
      pipenv

# Set up working directory
WORKDIR /

# Copy files over
COPY Pipfile* ./
COPY src ./src
COPY tools ./tools
COPY .env .env

RUN pipenv install

# Set the entrypoint command
CMD ["sh", "tools/run_main.sh"]
