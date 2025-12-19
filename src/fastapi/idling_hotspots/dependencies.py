from src.fastapi.idling_hotspots.repositories.idling_data import IdlingDataRepository
from src.fastapi.idling_hotspots.services import IdlingReportService


def get_idling_report_service() -> IdlingReportService:
    repo = IdlingDataRepository()
    return IdlingReportService(repo)
