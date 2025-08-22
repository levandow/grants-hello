# 1) Base image
FROM python:3.11-slim

# 2) System settings for faster installs
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# 3) Workdir
WORKDIR /app

# 4) Install deps
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# 5) Copy source
COPY app /app/app

# 6) Expose and run
EXPOSE 8080
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
