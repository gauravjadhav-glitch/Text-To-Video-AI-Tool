# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install system dependencies for MoviePy and ImageMagick
RUN apt-get update && apt-get install -y \
    ffmpeg \
    imagemagick \
    ghostscript \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# Fix ImageMagick policy to allow TextClip to work (MoviePy requirement)
RUN POLICY_FILE=$(find /etc/ImageMagick* -name policy.xml | head -n 1) && \
    if [ -n "$POLICY_FILE" ]; then \
    sed -i 's/domain="path" rights="none" pattern="@\*"/domain="path" rights="read|write" pattern="@\*"/g' "$POLICY_FILE"; \
    fi

# Set work directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "web_app:app", "--host", "0.0.0.0", "--port", "8000"]
