FROM python:3.11.12-slim-bookworm
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 HEARTML_ROOT=/app
WORKDIR /app
COPY requirements-serve.txt constraints.txt pyproject.toml ./
RUN pip install --no-cache-dir -r requirements-serve.txt
COPY src ./src
RUN pip install --no-cache-dir --no-deps . && useradd --uid 10001 --create-home appuser
COPY --chown=10001:10001 artifacts/model ./artifacts/model
USER 10001:10001
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/ready', timeout=3)"
CMD ["uvicorn", "heartml.api:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]

