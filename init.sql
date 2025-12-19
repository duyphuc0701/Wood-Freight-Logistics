-- Create table for GPS events
CREATE TABLE IF NOT EXISTS gps_events (
    id SERIAL PRIMARY KEY,
    device_id VARCHAR(255) NOT NULL,
    device_name VARCHAR(255) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    speed FLOAT,
    odometer FLOAT,
    power_on BOOLEAN,
    latitude FLOAT,
    longitude FLOAT,
    fuel_gauge FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create table for Fault events
CREATE TABLE IF NOT EXISTS fault_events (
    id             SERIAL PRIMARY KEY,
    device_id      VARCHAR(100)    NOT NULL,
    device_name    VARCHAR(100)    NOT NULL,
    timestamp      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fault_payload  VARCHAR(100)    NOT NULL,
    fault_code     VARCHAR(100)    NOT NULL,
    fault_label    VARCHAR(100)    NOT NULL
);

-- Create table for Idling summary
CREATE TABLE IF NOT EXISTS idling_hotspots (
  id                      SERIAL PRIMARY KEY,
  asset_id                VARCHAR(100)    NOT NULL,
  date                    DATE            NOT NULL,
  idle_duration_minutes   FLOAT           NOT NULL,
  latitude                FLOAT           NOT NULL,
  longitude               FLOAT           NOT NULL
);
