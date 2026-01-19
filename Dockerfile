# Python API Backend Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY *.py ./

# Create necessary directories (data will be mounted or added separately)
RUN mkdir -p data/pdfs data/excel analytics_output outputs

# Environment variables
ENV ENVIRONMENT=production
ENV PORT=8000

# Expose port
EXPOSE 8000

# Run the application
CMD ["python", "-c", "import uvicorn; uvicorn.run('api_server:app', host='0.0.0.0', port=int(__import__('os').environ.get('PORT', 8000)), log_level='info')"]
