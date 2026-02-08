FROM python:3.13-slim

WORKDIR /app

# Upgrade pip and install uv
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir uv

# Copy configuration files
COPY pyproject.toml /app/

# Compile requirements
RUN uv pip compile pyproject.toml > requirements.txt

# Install dependencies system-wide
RUN uv pip install -r requirements.txt --system

# Copy application code
COPY . /app/

CMD ["python", "-m", "src.app.main"]