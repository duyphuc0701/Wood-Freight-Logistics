from enum import Enum


class Granularity(str, Enum):
    daily = "daily"
    weekly = "weekly"
    monthly = "monthly"
