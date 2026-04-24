# ── Stage 1: Build Frontend ────────────────────────────────
FROM node:20-slim AS frontend-builder
WORKDIR /app/frontend
COPY ml-lens/frontend/package*.json ./
RUN npm install
COPY ml-lens/frontend/ ./
RUN npm run build

# ── Stage 2: Build Backend & Final Image ──────────────────
FROM python:3.11-slim
WORKDIR /app

# Install system dependencies for PyMuPDF and other tools
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy backend requirements and install
COPY ml-lens/backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source
COPY ml-lens/backend/ ./

# Copy built frontend from Stage 1 to a directory the backend can serve
COPY --from=frontend-builder /app/frontend/dist ./static

# Set environment variables
ENV PORT=8000
ENV PYTHONUNBUFFERED=1

# Expose the port
EXPOSE 8000

# Start the application
# We use uvicorn to serve the FastAPI app
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
