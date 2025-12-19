# Using pip compile to compile the lock version of requirements.in
```sh
pip-compile requirements.in -o requirements.txt
```

# Using pip compile dev requirements, but need to aware the feature packages
```sh
pip-compile requirements-dev.in -c requirements.txt -o requirements-dev.txt
```

# Virtual env
```sh
python3 -m venv .venv
./.venv/bin/activate
pip install pip-tools
pip-sync requirements.txt requirements-dev.txt
```

# Run code lint, static type checking and formatting
```sh
pre-commit install  # install pre-commit hooks
isort .
black src/
mypy src/
flake8 src/
```

# Run test
```sh
pytest tests --cov=src/fastapi
```


# Run app
## 📦 Setup .env
Create a `.env` file in the root directory and add the following environment
variables in `.env.example`:

```dotenv
ENVIRONMENT=development/production
RABBITMQ_HOST=rabbitmq
RABBITMQ_PORT=5672
RABBITMQ_USER=your_rabbitmq_user
RABBITMQ_PASSWORD=your_rabbitmq_password
POSTGRES_USER=your_postgres_user
POSTGRES_PASSWORD=your_postgres_password
POSTGRES_HOST=your_postgres_host
POSTGRES_PORT=5432
POSTGRES_DB=your_postgres_name
FASTAPI_API_KEY_HEADER=your_fastapi_api_key_header
FASTAPI_API_KEY=your_fastapi_api_key
FASTAPI_CORS_ORIGINS=https://localhost
REDIS_HOST=localhost
REDIS_PORT=6379
DEVICE_API_URL=your_device_api_url
FAULT_API_URL=your_fault_api_url
ALERTING_HOST=your_alerting_host
ALERTING_PORT=your_alerting_port
```

## 🚀 Running the Application

### 1. Build & Start all services

```sh
# Create
docker-compose up --build -d
```

### 2. Access Services

- **FastAPI** (API & Swagger UI):
http://localhost:8000
    - Swagger: http://localhost:8000/docs

- **RabbitMQ** (messaging):
http://localhost:15672

---
