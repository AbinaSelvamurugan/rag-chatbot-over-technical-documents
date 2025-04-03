FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY pyproject.toml requirements.txt ./
COPY backend ./backend
RUN pip install --no-cache-dir .
COPY data ./data
COPY evaluation/dataset ./evaluation/dataset
COPY scripts ./scripts
RUN mkdir -p /app/runtime /app/evaluation/results && useradd --system --create-home app && chown -R app:app /app/runtime /app/evaluation/results
USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health',timeout=3)"
CMD ["uvicorn","backend.app.main:app","--host","0.0.0.0","--port","8000"]
