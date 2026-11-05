FROM python:3.12-slim

WORKDIR /app

COPY requirements-ingestion.txt .
RUN pip install --no-cache-dir -r requirements-ingestion.txt

COPY ingestion/ ingestion/

CMD ["python", "-m", "ingestion.extraire"]