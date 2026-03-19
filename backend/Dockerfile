# Use a Python image with uv pre-installed
FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim AS builder

# Set the working directory
WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Copy project files
COPY pyproject.toml uv.lock ./

# Install dependencies
# We remove --frozen to allow uv to update the environment based on pyproject.toml
# if the lock file is out of sync.
RUN uv sync --no-install-project --no-dev

# Final stage
FROM python:3.11-slim-bookworm

WORKDIR /app

# Copy the environment from the builder
COPY --from=builder /app/.venv /app/.venv

# Add .venv/bin to PATH
ENV PATH="/app/.venv/bin:$PATH"

# Copy the application code
COPY . .

# Verify that all dependencies are installed, including Langfuse
# This step will fail the build if a core dependency is missing
RUN python -c "import langfuse; from importlib.metadata import version; print('Langfuse version:', version('langfuse'))"

# Expose the port
EXPOSE 8080

# Run the application
# We use python -m uvicorn to ensure it uses the correct site-packages in the virtual environment
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--proxy-headers", "--forwarded-allow-ips", "*"]
