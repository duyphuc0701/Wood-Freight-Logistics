from abc import ABC, abstractmethod
from typing import List

from src.fastapi.idling_hotspots.schemas import IdlingHotspot, IdlingHotspotResponseDTO


class ISpatialGrouper(ABC):
    @abstractmethod
    def group(
        self, records: List[IdlingHotspot], level: str
    ) -> List[IdlingHotspotResponseDTO]: ...
