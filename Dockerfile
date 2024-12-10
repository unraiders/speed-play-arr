FROM python:3.11-alpine

LABEL maintainer="unraiders"
LABEL version="1.0.0"
LABEL description="Speed control for torrent clients based on Plex activity"

# Crear usuario no root
RUN adduser -D speedplay

WORKDIR /app

# Copiar solo los archivos necesarios
COPY requirements.txt .
COPY speed-play-arr.py .

# Instalar dependencias y limpiar caché
RUN pip install --no-cache-dir -r requirements.txt && \
    chown -R speedplay:speedplay /app

# Cambiar al usuario no root
USER speedplay

CMD ["python", "speed-play-arr.py"]
