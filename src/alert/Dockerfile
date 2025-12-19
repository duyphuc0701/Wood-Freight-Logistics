FROM python:3.12.9-slim

WORKDIR /app

COPY ../../requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ./src/alert ./src/alert
COPY ./src/__init__.py ./src/__init__.py

EXPOSE 8001

CMD ["python", "-m", "src.alert.main"]
