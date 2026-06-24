FROM python:3.10-slim

# Set environment variable defaults
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=5000

# Set working directory inside the container
WORKDIR /app

# Install system dependencies (build-essential for compiling any packages if needed)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install python packages
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy project source code into container
COPY . /app/

# Expose port
EXPOSE 5000

# Run gunicorn server
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]
