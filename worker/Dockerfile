FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml .
RUN pip install --no-cache-dir .
COPY src/ ./src/
ENV PYTHONPATH=/app/src
CMD ["python", "-m", "nmia_worker.main"]
