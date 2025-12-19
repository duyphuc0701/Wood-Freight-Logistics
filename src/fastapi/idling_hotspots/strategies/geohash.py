from collections import defaultdict
from typing import List

import pygeohash as pgh

from src.fastapi.idling_hotspots.schemas import IdlingHotspot, IdlingHotspotResponseDTO
from src.fastapi.idling_hotspots.strategies.interface import ISpatialGrouper


class GeohashSpatialGrouper(ISpatialGrouper):
    def group(
        self, records: List[IdlingHotspot], level: str
    ) -> List[IdlingHotspotResponseDTO]:
        try:
            precision = int(level.split("_")[-1])
        except (IndexError, ValueError):
            raise ValueError(f"Invalid geohash aggregation level: {level}")

        buckets = defaultdict(list)

        for r in records:
            geohash_code = pgh.encode(r.latitude, r.longitude, precision)
            buckets[geohash_code].append(r)

        return [
            IdlingHotspotResponseDTO(
                location_identifier=key,
                total_idle_incidents=len(group),
                total_idle_duration_minutes=sum(r.idle_duration_minutes for r in group),
                contributing_asset_ids_sample=list({r.asset_id for r in group})[:5],
            )
            for key, group in buckets.items()
        ]
