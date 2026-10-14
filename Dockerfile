# Use official lightweight Python image
FROM python:3.11-slim

# Prevent Python from writing pyc files and buffering stdout
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONIOENCODING=utf-8

WORKDIR /app

# Install basic build tools and curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code and simulated data
COPY . .

# Expose Streamlit default port
EXPOSE 8501

# Health check to ensure Streamlit is responding
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health || exit 1

# Launch application via Python entrypoint
CMD ["python", "start.py"]
