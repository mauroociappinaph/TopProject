# Dockerfile para FastAPI Agent Engine (AI Workloads)
FROM python:3.10-slim

WORKDIR /app

# Instalar dependencias del sistema necesarias
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copiar requerimientos y dependencias
COPY pyproject.toml ./
RUN pip install --no-cache-dir fastapi uvicorn redis pycryptodome pydantic

# Copiar el código del servicio
COPY ./app ./app

# Exponer el puerto
EXPOSE 8000

# Variables de entorno por defecto
ENV PORT=8000
ENV REDIS_HOST=localhost
ENV REDIS_PORT=6379

# Ejecutar la aplicación
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
