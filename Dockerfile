# Multi-stage Dockerfile for AFI Econ Kit
# Supports STRICT=1 (require-hashes) and STRICT=0 (dev) modes

ARG PYTHON_VERSION=3.10
FROM python:${PYTHON_VERSION}-slim as base

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

# Create non-root user
RUN groupadd -r afi && useradd -r -g afi afi

# ============================================================================
# STRICT=1 Stage: Production with hash verification
# ============================================================================
FROM base as strict

# Install pip-tools for hash verification
RUN pip install pip-tools==7.3.0

# Copy requirements with hashes
COPY requirements.txt /tmp/requirements.txt

# Verify and install dependencies with hash checking
RUN pip-sync /tmp/requirements.txt

# Copy source code
COPY . /app
WORKDIR /app

# Install package in production mode
RUN pip install --no-deps .

# Switch to non-root user
USER afi

# Set working directory for runtime
WORKDIR /work

# Default command
CMD ["afi-econ-kit", "--help"]

# ============================================================================
# STRICT=0 Stage: Development without hash verification
# ============================================================================
FROM base as dev

# Copy requirements without hash verification
COPY requirements.txt /tmp/requirements.txt

# Install dependencies without hash checking
RUN pip install -r /tmp/requirements.txt

# Copy source code
COPY . /app
WORKDIR /app

# Install package in development mode
RUN pip install -e .

# Switch to non-root user
USER afi

# Set working directory for runtime
WORKDIR /work

# Default command
CMD ["afi-econ-kit", "--help"]

# ============================================================================
# Final stage selection based on STRICT argument
# ============================================================================
FROM ${STRICT:+strict} ${STRICT:-dev} as final

# Add labels for metadata
LABEL org.opencontainers.image.title="AFI Econ Kit"
LABEL org.opencontainers.image.description="AFI Economic System Implementation"
LABEL org.opencontainers.image.vendor="AFI Protocol"
LABEL org.opencontainers.image.source="https://github.com/AFI-Protocol/afi-econ-kit"
LABEL org.opencontainers.image.documentation="https://github.com/AFI-Protocol/afi-econ-kit/blob/main/README.md"

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD afi-econ-kit --version || exit 1

# Expose any ports if needed (none for CLI tool)
# EXPOSE 8080

# Final working directory
WORKDIR /work

# Default entrypoint
ENTRYPOINT ["afi-econ-kit"]
CMD ["--help"]
