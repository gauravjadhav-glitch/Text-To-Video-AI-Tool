# Use a modern supported Python version
FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
# Ensure MoviePy finds ImageMagick
ENV IMAGEMAGICK_BINARY /usr/bin/convert

# Install system dependencies for MoviePy and ImageMagick
RUN apt-get update && apt-get install -y \
    ffmpeg \
    imagemagick \
    ghostscript \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# Fix ImageMagick policy to allow TextClip to work (MoviePy requirement)
# This is crucial for Render/Vercel deployments
RUN sed -i 's/domain="path" rights="none" pattern="@\*"/domain="path" rights="read|write" pattern="@\*"/g' /etc/ImageMagick-6/policy.xml || true

# Set work directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Expose port
EXPOSE 8000

# Run the application with uvicorn (Production mode)
CMD ["uvicorn", "web_app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
