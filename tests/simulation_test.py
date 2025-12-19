import asyncio
import base64
import os
import random
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import Optional

import aio_pika
from dotenv import load_dotenv

load_dotenv()

RABBITMQ_USER = os.getenv("RABBITMQ_USER")
RABBITMQ_PASSWORD = os.getenv("RABBITMQ_PASSWORD")

# Configuration
DA_NANG = (16.047079, 108.206230)  # latitude, longitude
HO_CHI_MINH = (10.762622, 106.660172)

DISTANCE_KM = 960  # Approximate distance between Da Nang and Ho Chi Minh
UPDATE_INTERVAL = 1  # seconds
NUM_TRUCKS = 10
IDLE_TIME = 20
OFF_TIME = 300

RABBITMQ_URL = f"amqp://{RABBITMQ_USER}:{RABBITMQ_PASSWORD}@localhost:5672/"
EXCHANGE_NAME = "events_exchange"

FAULT_PROBABILITY = 0.3
DUPLICATE_PROBABILITY = 0.2
NULL_FIELD_PROBABILITY = 0.2
UNKNOWN_DEVICE_PROBABILITY = 0.2
UNKNOWN_DEVICE_ID_RANGE = range(1001, 1011)


# Abstract Base Class
class Event(ABC):
    def __init__(self, device_id: str):
        self.device_id = device_id
        self.timestamp = float(datetime.now(UTC).timestamp())

    @abstractmethod
    def encode(self) -> str:
        pass

    @abstractmethod
    def to_payload(self) -> dict:
        pass


# GPS Event
class GPSEvent(Event):
    def __init__(
        self,
        device_id: str,
        speed: float | None,
        odometer: float | None,
        power_on: bool,
        latitude: float,
        longitude: float,
        fuel_gauge: float,
    ):
        super().__init__(device_id)

        self.speed = speed
        self.odometer = odometer
        self.power_on = power_on
        self.latitude = latitude
        self.longitude = longitude
        self.fuel_gauge = fuel_gauge

    def encode(self):
        speed = "" if self.speed is None else self.speed
        odometer = "" if self.odometer is None else self.odometer
        raw_str = (
            f"{self.device_id}:{self.timestamp}:"
            f"{speed}:{odometer}:{self.power_on}:"
            f"{self.latitude}:{self.longitude}:"
            f"{self.fuel_gauge}"
        )
        return base64.b64encode(raw_str.encode()).decode()

    def to_payload(self):
        return {
            "type": "gps",
            "event": self.encode(),
            "latitude": self.latitude,
            "longitude": self.longitude,
        }


# Fault Event
class FaultEvent(Event):
    def __init__(self, device_id: str, fault_code: int, total_number: int):
        super().__init__(device_id)
        self.fault_code = fault_code
        self.total_number = total_number
        self.bits = [self._generate_fault_bits() for _ in range(total_number)]
        self.sequence = 0

    def _generate_fault_bits(self):
        return "".join(random.choices("01", k=8))

    def encode(self):
        fault_bit = self.bits[self.sequence]
        raw_str = (
            f"{self.device_id}:{self.timestamp}"
            f":{fault_bit}:{self.fault_code}"
            f":{self.sequence}:{self.total_number}"
        )
        return base64.b64encode(raw_str.encode()).decode()

    def to_payload(self):
        encoded_event = self.encode()
        self.sequence += 1
        return {"type": "fault", "event": encoded_event}

    def is_complete(self):
        return self.sequence >= self.total_number


# Truck Simulator
class TruckSimulator:
    def __init__(self, device_id: str, channel):
        self.device_id: str = device_id
        self.active_fault: Optional[FaultEvent] = None
        self.channel: aio_pika.Channel = channel
        self.exchange: Optional[aio_pika.Exchange] = None
        self.last_gps_payload: Optional[dict[str, str]] = None
        self.position: list[float] = list(random.choice([DA_NANG, HO_CHI_MINH]))
        self.speed: float = 800.0  # km/h
        self.odometer: float = 0.0  # km
        self.fuel_gauge: float = 100.0  # liters
        self.power_on: bool = True
        self.direction: int = 1 if self.position == list(DA_NANG) else -1
        self.route_start: tuple[float, float] = (
            DA_NANG if self.direction == 1 else HO_CHI_MINH
        )
        self.route_end: tuple[float, float] = (
            HO_CHI_MINH if self.direction == 1 else DA_NANG
        )
        self.trip_distance: float = 0.0
        self.pause_timer: int = 10
        self.stop_position: float = 0.01 * DISTANCE_KM
        self.stopped_for_break: bool = False

    async def setup(self):
        self.exchange = await self.channel.declare_exchange(
            EXCHANGE_NAME, aio_pika.ExchangeType.DIRECT, durable=True
        )

    async def update_position(self) -> GPSEvent:
        if self.pause_timer > 0:
            self.pause_timer -= 1
            speed = 0.0
            self.power_on = self.pause_timer <= IDLE_TIME
        else:
            self.power_on = True
            # Check for temporary stop mid-route
            if not self.stopped_for_break and self.trip_distance >= self.stop_position:
                self.pause_timer = IDLE_TIME
                self.stopped_for_break = True
                speed = 0.0
            else:
                print("no longer stop")
                speed = self.speed / 3600  # convert km/h to km/s
                self.trip_distance += speed
                self.odometer += speed
                self.fuel_gauge -= speed  # arbitrary consumption rate

                frac = self.trip_distance / DISTANCE_KM
                if frac > 1:
                    self.pause_timer = OFF_TIME  # 5 minute stop at end
                    self.power_on = False
                    self.direction *= -1
                    self.route_start, self.route_end = self.route_end, self.route_start
                    self.trip_distance = 0
                    self.stopped_for_break = False
                    self.stop_position = 0.01 * DISTANCE_KM
                    frac = 1

                self.position[0] = self.route_start[0] + frac * (
                    self.route_end[0] - self.route_start[0]
                )
                self.position[1] = self.route_start[1] + frac * (
                    self.route_end[1] - self.route_start[1]
                )

        event = GPSEvent(
            device_id=self.device_id,
            speed=(0.0 if self.pause_timer > 0 else self.speed),
            odometer=(round(self.odometer, 2)),
            power_on=True,
            latitude=round(self.position[0], 2),
            longitude=round(self.position[1], 2),
            fuel_gauge=round(self.fuel_gauge, 2),
        )
        return event

    async def send(self, payload: dict):
        routing_key = payload.get("type")
        event_str = payload.get("event")
        if routing_key is None:
            raise ValueError("Payload missing routing key 'type'")
        message = aio_pika.Message(
            body=str(event_str).encode(), delivery_mode=aio_pika.DeliveryMode.PERSISTENT
        )
        assert self.exchange is not None, "Exchange not initialized"
        await self.exchange.publish(message, routing_key=routing_key)
        print(f"[Truck {self.device_id}] Sent {payload['type']} event")

    async def simulate(self):
        await self.setup()

        while True:
            gps_event = await self.update_position()
            if random.random() < UNKNOWN_DEVICE_PROBABILITY:
                unknown_id = random.choice(UNKNOWN_DEVICE_ID_RANGE)
                gps_event.device_id = unknown_id
                await self.send(gps_event.to_payload())
                await asyncio.sleep(1)
                continue

            if self.last_gps_payload and random.random() < DUPLICATE_PROBABILITY:
                print(f"[Truck {self.device_id}] Sending duplicate GPS event")
                await self.send(self.last_gps_payload)
            else:
                allow_nulls = random.random() < NULL_FIELD_PROBABILITY
                if allow_nulls:
                    gps_event.speed = None
                    gps_event.odometer = None

                self.last_gps_payload = gps_event.to_payload()
                await self.send(self.last_gps_payload)

            if self.active_fault:
                if not self.active_fault.is_complete():
                    await self.send(self.active_fault.to_payload())
                else:
                    self.active_fault = None
            elif random.random() < FAULT_PROBABILITY:
                fault_code = random.randint(1, 100)
                total_parts = random.randint(2, 4)
                self.active_fault = FaultEvent(self.device_id, fault_code, total_parts)

            await asyncio.sleep(UPDATE_INTERVAL)


async def main():
    connection = await aio_pika.connect_robust(RABBITMQ_URL)
    channel = await connection.channel()

    tasks = []
    for device_id in range(1, NUM_TRUCKS + 1):
        simulator = TruckSimulator(str(device_id), channel)
        tasks.append(asyncio.create_task(simulator.simulate()))

    print(f"Simulating {NUM_TRUCKS} trucks with RabbitMQ publishing...")
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())
