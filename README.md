# 🚛 Wood Freight Logistics: IoT & Fleet Analytics Platform

This project represents a sophisticated backend ecosystem designed for a high-scale timber transportation company. It transitions legacy manual logistics tracking into a robust, automated analytical platform, utilizing **SOLID principles**, **Event-Driven Architecture (EDA)**, and **N-Layered design patterns** to manage fleet telemetry and hardware fault diagnostics.

## 🌟 Key Technical Features

### 📡 Real-Time Telemetry & Fault Processing
* **Fragmented Payload Reconstruction**: Implements a reconstruction algorithm to assemble multi-part hardware fault bits into complete data structures based on sequence markers and total counts.
* **Fault Suppression Engine**: Reduces "alert fatigue" by implementing time-based suppression windows—where a fault lasting $x$ seconds causes subsequent identical codes to be ignored—calculated from big-endian payload integers.
* **Reliability Layer**: Built-in resilience for external API dependencies, featuring **Redis-backed caching** to handle "Internal Server Errors" (500) and "Rate Limit Exceeded" (429) scenarios.
* **Data Sanitization**: Automated filtering of redundant transmissions, records with missing velocity/mileage values, and signals from unrecognized hardware IDs.

### 📊 Advanced Fleet Analytics
* **Finite State Machine (FSM) Journey Logic**: Automates the detection of distinct "trips" (EngineOff, EngineOnStationary, Moving) by tracking vehicle state transitions from raw GPS streams.
* **Daily Operational Summaries**: Aggregates raw telemetry into persistent summaries containing total distance ($km$), operational hours, and number of distinct trips.
* **Geospatial Hotspot Analysis**: Identifies idling "hotspots" by grouping coordinate data using rounding or geohashing to improve fleet fuel efficiency.

### 🏗️ Architectural Excellence
* **N-Layered Service Design**: Strict separation between API (Presentation), Service (Application logic), and Data Access layers.
* **SOLID Implementation**:
    * **Strategy Pattern**: Swappable algorithms for trip definitions, utilization scoring (Distance vs. Hours), and time-based aggregation.
    * **Repository Pattern**: Abstracted database interactions (e.g., `IDailySummaryRepository`) ensure the core logic remains independent of the database technology (DIP).
    * **Fan-in Architecture**: A consolidated notification pipeline that accepts disparate GPS and Fault data schemas into a single alerting schema.

---

## 🛠️ Technology Stack

| Category | Technology |
| :--- | :--- |
| **Framework** | FastAPI (Python 3.10+) |
| **Messaging** | RabbitMQ (Event Streaming) |
| **Data Store** | PostgreSQL (Relational Analytics), Redis (Caching) |
| **DevOps** | Docker Compose, Pre-commit Hooks |
| **Quality** | Pytest (Coverage), MyPy (Static Typing), Black/Flake8 |

---

## 🚀 Getting Started

### 1. Environment Configuration
Create a `.env` file in the root directory and add the following environment variables (see `.env.example`):

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
TIMEZONE=your_timezone
```

# Using pip compile to compile the lock version of requirements.in
pip-compile requirements.in -o requirements.txt

# Using pip compile dev requirements
pip-compile requirements-dev.in -c requirements.txt -o requirements-dev.txt

# Initialize Virtual Environment and Sync
python3 -m venv .venv
./.venv/bin/activate
pip install pip-tools
pip-sync requirements.txt requirements-dev.txt

# Install Pre-commit hooks for Linting/Formatting
pre-commit install

# Build & Start all services
docker-compose up --build -d

# Run code lint, static type checking and formatting
isort .
black src/
mypy src/
flake8 src/

# Run Comprehensive Test Suite with Coverage
pytest tests --cov=src/fastapi