FROM python:3.11-slim

# Workdir
WORKDIR /app

# Python settings
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# System deps (keeps wheels building reliably)
RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential \
 && rm -rf /var/lib/apt/lists/*

# Install Python deps first (better layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app
COPY . .

# Cloud Run listens on $PORT (defaults to 8080)
ENV PORT=8080

# Start with gunicorn (app:app is your Flask instance)
CMD ["gunicorn", "-b", "0.0.0.0:$PORT", "app:app", "--workers=1", "--threads=4", "--timeout", "120", "--access-logfile", "-", "--error-logfile", "-"]
