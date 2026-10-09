# ==========================================
# STAGE 1: Builder (Linux Nuitka Compilation Environment)
# ==========================================
FROM python:3.11-slim-bookworm AS builder

# Prevent Python from writing bytecode files & force unbuffered stdout
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Install Linux build tools, GCC/G++ compiler, and PostgreSQL dev headers
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    libpq-dev \
    patchelf \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install build dependencies + Nuitka
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt pydantic[email] nuitka psycopg2-binary

# Copy application files for compilation
COPY . .

# Run Nuitka Standalone compilation for Linux target
RUN python -m nuitka \
    --standalone \
    --assume-yes-for-downloads \
    --include-package=fastapi \
    --include-package=uvicorn \
    --include-package=sqlalchemy \
    --include-package=asyncpg \
    --include-package=psycopg2 \
    --include-package=passlib \
    --include-package=bcrypt \
    --output-dir=build_nuitka \
    entry_build.py

# ==========================================
# STAGE 2: Final Minimal Runtime Image (Zero Source Code)
# ==========================================
FROM python:3.11-slim-bookworm AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000

WORKDIR /app

# Install runtime PostgreSQL client library & curl for health check
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy ONLY the compiled Nuitka dist directory (C binary & shared libraries) from builder stage
COPY --from=builder /app/build_nuitka/entry_build.dist /app/dist

# Set working directory to compiled distribution folder
WORKDIR /app/dist

# Expose FastAPI application port
EXPOSE 8000

# Execute compiled Linux binary (entry_build.bin)
CMD ["./entry_build.bin"]
