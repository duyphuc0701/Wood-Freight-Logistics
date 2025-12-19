from src.fastapi.idling_hotspots.strategies.geohash import GeohashSpatialGrouper
from src.fastapi.idling_hotspots.strategies.interface import ISpatialGrouper
from src.fastapi.idling_hotspots.strategies.rounded_lat_lon import (
    RoundedLatLonSpatialGrouper,
)


class SpatialGrouperFactory:
    @staticmethod
    def create(aggregation_level: str) -> ISpatialGrouper:
        if aggregation_level.startswith("rounded_lat_lon_"):
            return RoundedLatLonSpatialGrouper()
        elif aggregation_level.startswith("geohash_level_"):
            return GeohashSpatialGrouper()
        else:
            raise ValueError(f"Unsupported aggregation level: {aggregation_level}")
