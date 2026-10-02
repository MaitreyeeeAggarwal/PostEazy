FROM python:3.11-slim

# Install system dependencies including ffmpeg and fonts
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    fonts-montserrat \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy Python requirements & install dependencies
COPY Backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy frontend static files
COPY frontend /frontend

# Copy backend application code
COPY Backend /app

# Set FRONTEND_DIR environment variable
ENV FRONTEND_DIR=/frontend

# Expose server port
EXPOSE 8000

# Run FastAPI uvicorn server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
