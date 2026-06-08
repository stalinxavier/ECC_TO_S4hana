# Use official Python slim image to keep the image size small
FROM python:3.13.3-slim

# Set working directory
WORKDIR /app

# Install system dependencies needed by some packages (e.g. hdbcli, cryptography)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies first (layer-cached until requirements change)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY func/ ./func/
COPY llm/ ./llm/
COPY agent.py .
COPY main.py .

# .env is NOT baked into the image — mount it at runtime with --env-file
# Environment variables expected:
#   url, username1, password        (ECC OData)
#   S4_URL, S4_USERNAME, S4_PASSWORD (S/4HANA OData)
#   AICORE_AUTH_URL, AICORE_CLIENT_ID, AICORE_CLIENT_SECRET,
#   AICORE_RESOURCE_GROUP, AICORE_BASE_URL, LLM_DEPLOYMENT_ID

# Run the agent (full pipeline, no user input required)
CMD ["python", "agent.py"]
