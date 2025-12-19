from collections import defaultdict
from decimal import Decimal
from typing import List

from src.fastapi.idling_hotspots.schemas import IdlingHotspot, IdlingHotspotResponseDTO
from src.fastapi.idling_hotspots.strategies.interface import ISpatialGrouper


class RoundedLatLonSpatialGrouper(ISpatialGrouper):
    def group(
        self, records: List[IdlingHotspot], level: str
    ) -> List[IdlingHotspotResponseDTO]:
        precision = float(level.split("_")[-1])
        decimal_places = abs(int(Decimal(str(precision)).as_tuple().exponent))
        buckets = defaultdict(list)

        for r in records:
            lat = round(r.latitude / precision) * precision
            lon = round(r.longitude / precision) * precision
            key = f"{lat:.{decimal_places}f}_{lon:.{decimal_places}f}"
            buckets[key].append(r)

        return [
            IdlingHotspotResponseDTO(
                location_identifier=key,
                total_idle_incidents=len(group),
                total_idle_duration_minutes=sum(r.idle_duration_minutes for r in group),
                contributing_asset_ids_sample=list({r.asset_id for r in group}),
            )
            for key, group in buckets.items()
        ]
