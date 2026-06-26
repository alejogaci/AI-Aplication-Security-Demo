# =============================================================================
# Dockerfile — AI Guard Demo
# Imagen lista para correr el backend + frontend en un solo contenedor.
#
#   docker build -t ai-guard-demo .
#   docker run -p 8000:8000 ai-guard-demo
#   (luego abrí http://localhost:8000)
#
# Para usar la API real de Trend Micro, pasá las variables al correr:
#   docker run -p 8000:8000 -e TREND_API_KEY=tu-key ai-guard-demo
# =============================================================================
FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias primero (mejor cache de Docker)
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código
COPY backend ./backend
COPY frontend ./frontend
COPY .env.example ./.env.example

ENV PORT=8000
EXPOSE 8000

# Arrancar el servidor
CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
