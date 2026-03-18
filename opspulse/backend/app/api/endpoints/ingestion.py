from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Form
from sqlalchemy.orm import Session
from pathlib import Path
import tempfile
import shutil
import logging
from app.database import get_db
from app.etl.ingestion import ingest_csv, ingest_json
from app.etl.loader import load_workforce, load_tickets, load_market_signals
from app.models.facts import StagingError

router = APIRouter(prefix="/ingestion", tags=["ingestion"])
logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {".csv", ".json"}


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    source_type: str = Form(..., description="workforce | tickets | market"),
    db: Session = Depends(get_db),
):
    """Ingest a CSV or JSON file into the data warehouse."""
    if source_type not in ("workforce", "tickets", "market"):
        raise HTTPException(status_code=400, detail="source_type must be workforce, tickets, or market")

    suffix = Path(file.filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"File type {suffix} not allowed")

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = Path(tmp.name)

    try:
        if suffix == ".csv":
            result = ingest_csv(tmp_path, source_type)
        else:
            result = ingest_json(tmp_path)

        df = result["data"]
        if source_type == "workforce":
            loaded = load_workforce(db, df, file.filename)
        elif source_type == "tickets":
            loaded = load_tickets(db, df, file.filename)
        else:
            loaded = load_market_signals(db, df, file.filename)

        return {
            "filename": file.filename,
            "source_type": source_type,
            "raw_rows": result["raw_rows"],
            "clean_rows": result["clean_rows"],
            "loaded_rows": loaded,
            "error_count": result["error_count"],
            "status": "success",
        }
    except Exception as e:
        logger.exception(f"Ingestion failed for {file.filename}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        tmp_path.unlink(missing_ok=True)


@router.get("/errors")
def get_ingestion_errors(
    resolved: bool = False,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """Return quarantined error rows from the staging_error table."""
    errors = (
        db.query(StagingError)
        .filter(StagingError.resolved == resolved)
        .order_by(StagingError.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": e.id,
            "source_file": e.source_file,
            "source_type": e.source_type,
            "row_number": e.row_number,
            "error_type": e.error_type,
            "error_message": e.error_message,
            "created_at": e.created_at.isoformat(),
            "resolved": e.resolved,
        }
        for e in errors
    ]
