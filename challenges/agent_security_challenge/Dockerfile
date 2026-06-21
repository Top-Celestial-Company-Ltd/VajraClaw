FROM python:3.12-alpine

WORKDIR /app

# Install build dependencies if needed, alpine python packages
RUN apk add --no-cache git build-base

# Copy files
COPY pyproject.toml README.md /app/
COPY dros_cli/ /app/dros_cli/
COPY dros_sdk/ /app/dros_sdk/
COPY src/ /app/src/
COPY atr_rules/ /app/atr_rules/
COPY templates/ /app/templates/

# Install the dros-guard package
RUN pip install --no-cache-dir -e .

# Expose ports: 5050 for Sandbox, 8000 for Control Plane
EXPOSE 5050
EXPOSE 8000

ENV PYTHONPATH=/app

# Default command can be overridden in docker-compose.yml
CMD ["python", "src/challenge_sandbox.py"]
