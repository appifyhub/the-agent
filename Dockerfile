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

# Copy the contents over (respecting .dockerignore)
COPY . .

# Set the entrypoint command
CMD ["sh", "tools/run_prod.sh"]
