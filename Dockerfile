FROM python:3.11-slim-bookworm

WORKDIR /app

# Copy application files
COPY pyproject.toml .
COPY app.py .
COPY config.py .
COPY src/ src/

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Unbuffered Python output for real-time logs
ENV PYTHONUNBUFFERED=1

EXPOSE 8877

# Run with gunicorn (production-ready server)
ENV PORT=8877
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 --access-logfile - app:app
