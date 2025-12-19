FROM python:3.12.9-slim

WORKDIR /app

COPY ../../requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ./src/fastapi ./src/fastapi
COPY ./src/__init__.py ./src/__init__.py

CMD ["uvicorn", "src.fastapi.main:app", "--host", "0.0.0.0", "--port", "8000"]
