FROM python:3.11-slim

# Install system dependencies including ffmpeg, fonts, and the Node creative renderer.
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    fonts-montserrat \
    nodejs \
    npm \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libdrm2 \
    libgbm1 \
    libnss3 \
    libx11-xcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy Python requirements & install dependencies
COPY Backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install the creative rendering toolchain before copying application source so
# dependency installation is cached between source-only changes.
COPY Backend/creative_renderer/package*.json /app/creative_renderer/
RUN npm ci --prefix /app/creative_renderer --omit=dev
RUN npx --prefix /app/creative_renderer remotion browser ensure

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
