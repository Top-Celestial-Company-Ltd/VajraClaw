FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Copy the entire public repository into the container
COPY . /app/

# Run the sandbox attack script by default
CMD ["python", "FreeTrial-Sandbox/run_demo_attack.py"]
