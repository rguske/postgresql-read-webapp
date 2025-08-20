FROM --platform=linux/amd64 registry.access.redhat.com/ubi9/python-312
LABEL maintainer="Robert Guske"
LABEL description="Python 3.12 web application which reads from a PostgreSQL instance"

WORKDIR /app

# Install Python deps
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy app
COPY app ./app

# Network
EXPOSE 8000

# Start server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# After (shell form, uses $PORT or 8080)
CMD sh -c 'uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}'