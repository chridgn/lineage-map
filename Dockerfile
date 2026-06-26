FROM python:3.12-slim

WORKDIR /app

# Install package with server extras
# Static frontend files are pre-built and included in the source tree
COPY pyproject.toml LICENSE README.md ./
COPY lineagemap/ lineagemap/

RUN pip install --no-cache-dir ".[server]"

EXPOSE 3000

# Manifest is expected at /manifest.json — mount yours there at runtime
CMD ["lineagemap", "serve", "--host", "0.0.0.0", "--port", "3000", "--manifest", "/manifest.json"]
