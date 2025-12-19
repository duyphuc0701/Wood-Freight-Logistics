# 🚛 Wood Freight Logistics: IoT & Fleet Analytics Platform

[cite_start]This project represents a sophisticated backend ecosystem designed for a high-scale timber transportation company[cite: 1, 33]. [cite_start]It transitions legacy manual logistics tracking into a robust, automated analytical platform, utilizing **SOLID principles**, **Event-Driven Architecture (EDA)**, and **N-Layered design patterns** to manage fleet telemetry and hardware fault diagnostics[cite: 34, 36, 37].

## 🌟 Key Technical Features

### 📡 Real-Time Telemetry & Fault Processing
* [cite_start]**Fragmented Payload Reconstruction**: Implements a reconstruction algorithm to assemble multi-part hardware fault bits into complete data structures based on sequence markers and total counts[cite: 17, 18, 19].
* [cite_start]**Fault Suppression Engine**: Reduces "alert fatigue" by implementing time-based suppression windows—where a fault lasting $x$ seconds causes subsequent identical codes to be ignored—calculated from big-endian payload integers[cite: 23, 24, 25].
* [cite_start]**Reliability Layer**: Built-in resilience for external API dependencies, featuring **Redis-backed caching** [cite: 5] [cite_start]to handle "Internal Server Errors" (500) and "Rate Limit Exceeded" (429) scenarios[cite: 10, 12].
* [cite_start]**Data Sanitization**: Automated filtering of redundant transmissions, records with missing velocity/mileage values, and signals from unrecognized hardware IDs[cite: 13, 14].

### 📊 Advanced Fleet Analytics
* [cite_start]**Finite State Machine (FSM) Journey Logic**: Automates the detection of distinct "trips" (EngineOff, EngineOnStationary, Moving) by tracking vehicle state transitions from raw GPS streams[cite: 42, 52, 54].
* [cite_start]**Daily Operational Summaries**: Aggregates raw telemetry into persistent summaries containing total distance ($km$), operational hours, and number of distinct trips[cite: 41, 42].
* [cite_start]**Geospatial Hotspot Analysis**: Identifies idling "hotspots" by grouping coordinate data using rounding or geohashing to improve fleet fuel efficiency[cite: 175, 181, 206].

### 🏗️ Architectural Excellence
* [cite_start]**N-Layered Service Design**: Strict separation between API (Presentation), Service (Application logic), and Data Access layers[cite: 102, 118].
* **SOLID Implementation**:
    * [cite_start]**Strategy Pattern**: Swappable algorithms for trip definitions [cite: 58, 59][cite_start], utilization scoring (Distance vs. Hours) [cite: 109, 110][cite_start], and time-based aggregation[cite: 165, 166].
    * [cite_start]**Repository Pattern**: Abstracted database interactions (e.g., `IDailySummaryRepository`) ensure the core logic remains independent of the database technology (DIP)[cite: 48, 61, 116].
    * [cite_start]**Fan-in Architecture**: A consolidated notification pipeline that accepts disparate GPS and Fault data schemas into a single alerting schema[cite: 28, 29].

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
Clone the repository and initialize your environment settings from the provided template:
```sh
cp .env.example .env
# Update .env with your specific API keys and database credentials
# Initialize Virtual Environment
python3 -m venv env
source ./env/bin/activate

# Install and Sync dependencies
pip install pip-tools
pip-sync requirements.txt requirements-dev.txt

# Install Pre-commit hooks for Linting/Formatting
pre-commit install

# Launch Platform (FastAPI, RabbitMQ, Redis, Postgres)
docker-compose up --build -d

# Run Comprehensive Test Suite with Coverage
pytest tests --cov=src/fastapi