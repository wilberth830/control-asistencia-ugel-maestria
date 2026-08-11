"""TEC-D09 TEC-D12."""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.api.deps import require_token
from app.services.report_service import report_service

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])


@router.get("/monthly-export")
def monthly_export(
    month: int,
    year: int,
    import_id: int | None = None,
    session: dict = Depends(require_token),
):
    workbook = report_service.monthly_workbook(month, year, import_id=import_id)
    filename = f"asistencia_{year:04d}_{month:02d}.xlsx"
    return StreamingResponse(
        workbook,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/annex-03")
def annex03(
    month: int,
    year: int,
    import_id: int | None = None,
    format: str = "json",
    session: dict = Depends(require_token),
):
    if format != "json":
        raise HTTPException(status_code=400, detail="Only JSON format is available")
    return report_service.annex_03(month, year, import_id=import_id)


@router.get("/annex-04")
def annex04(
    month: int,
    year: int,
    import_id: int | None = None,
    format: str = "json",
    session: dict = Depends(require_token),
):
    if format != "json":
        raise HTTPException(status_code=400, detail="Only JSON format is available")
    return report_service.annex_04(month, year, import_id=import_id)
