# Gunakan base image Python yang ringan
FROM python:3.8-slim

# Set direktori kerja di dalam kontainer
WORKDIR /app

# Salin file requirements
COPY requirements.txt .

# Install dependencies
RUN pip install -r requirements.txt

# Salin seluruh kode 'src' ke dalam kontainer
COPY src /app/src

# Default command (akan di-override oleh docker-compose)
CMD ["python", "-m", "src.nodes.lock_manager"]