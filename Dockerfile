FROM python:3.10.2-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    libpq-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy entrypoint script and set permissions
COPY entrypoint.sh .
RUN sed -i 's/\r$//' entrypoint.sh && \
    chmod +x entrypoint.sh

# Copy application code
COPY . .

EXPOSE 8080

# Use shell form to execute the entrypoint
CMD ["/bin/bash", "/app/entrypoint.sh"]