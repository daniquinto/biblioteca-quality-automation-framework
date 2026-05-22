FROM python:3.12-slim

# Metadatos de la imagen
LABEL maintainer="Biblioteca Quality Framework"
LABEL description="Framework de Calidad, Automatización y Migración de Datos - UNISABANETA"

WORKDIR /app

# Instalar dependencias del sistema necesarias para psycopg2-binary y python-Levenshtein
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copiar e instalar dependencias Python primero (capa cacheada por Docker)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto del código fuente
COPY . .

# Crear directorio de logs en caso de que no exista en el contexto de build
RUN mkdir -p logs

CMD ["python", "main.py"]
