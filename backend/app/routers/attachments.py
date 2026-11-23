from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Response, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..models import Attachment, RevisionState, User
from ..schemas import AttachmentRead
from ..services.audit import record_audit
from ..services.revisions import lock_mutations
from .revisions import require_revision

UPLOAD_DIR = Path(__file__).resolve().parents[2] / "uploads"
MAX_SIZE = 20 * 1024 * 1024
MEDIA_TYPES = {".stl": "application/octet-stream", ".step": "application/octet-stream",
               ".stp": "application/octet-stream", ".pdf": "application/pdf",
               ".png": "image/png", ".jpg": "image/jpeg"}
router = APIRouter(tags=["Attachments"])


def require_attachment(db, attachment_id):
    attachment = db.get(Attachment, attachment_id)
    if attachment is None:
        raise HTTPException(404, "Attachment not found.")
    return attachment


def attachment_path(attachment):
    path = (UPLOAD_DIR / attachment.stored_path).resolve()
    if path.parent != UPLOAD_DIR.resolve():
        raise HTTPException(404, "Attachment file not found.")
    return path


def require_editable(revision):
    if revision.state != RevisionState.DRAFT:
        raise HTTPException(409, "Attachments can only be changed while the revision is DRAFT.")


@router.get("/revisions/{revision_id}/attachments", response_model=list[AttachmentRead])
def list_attachments(revision_id: int, db: Session = Depends(get_db)):
    require_revision(db, revision_id)
    return db.scalars(select(Attachment).where(Attachment.revision_id == revision_id)
                      .order_by(Attachment.uploaded_at.desc(), Attachment.id.desc())).all()


@router.post("/revisions/{revision_id}/attachments", response_model=AttachmentRead, status_code=201)
def upload_attachment(revision_id: int, file: UploadFile, actor: User = Depends(get_current_user),
                      db: Session = Depends(get_db)):
    filename = (file.filename or "").replace("\\", "/").rsplit("/", 1)[-1]
    suffix = Path(filename).suffix.lower()
    if suffix not in MEDIA_TYPES or len(filename) > 255 or any(ord(c) < 32 for c in filename):
        raise HTTPException(400, "Use an STL, STEP, STP, PDF, PNG or JPG file with a filename under 256 characters.")
    lock_mutations(db)
    revision = require_revision(db, revision_id)
    require_editable(revision)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    stored = f"{uuid4().hex}{suffix}"
    path = UPLOAD_DIR / stored
    try:
        size = 0
        with path.open("xb") as destination:
            while chunk := file.file.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_SIZE:
                    raise HTTPException(413, "Maximum attachment size is 20 MB.")
                destination.write(chunk)
        if not size:
            raise HTTPException(400, "The attachment is empty.")
        attachment = Attachment(revision_id=revision_id, filename=filename, stored_path=stored,
                                file_type=suffix, size=size, uploaded_by=actor.id)
        db.add(attachment)
        db.flush()
        record_audit(db, actor, "ATTACHMENT_UPLOADED", "REVISION", revision_id,
                     part_id=revision.part_id, attachment_id=attachment.id, filename=filename, size=size)
        db.commit()
        db.refresh(attachment)
        return attachment
    except Exception:
        db.rollback()
        path.unlink(missing_ok=True)
        raise
    finally:
        file.file.close()


@router.get("/attachments/{attachment_id}/download")
def download_attachment(attachment_id: int, db: Session = Depends(get_db)):
    attachment = require_attachment(db, attachment_id)
    path = attachment_path(attachment)
    if not path.is_file():
        raise HTTPException(404, "Attachment file not found. Restore the uploads directory or re-upload the file.")
    return FileResponse(path, filename=attachment.filename, media_type=MEDIA_TYPES[attachment.file_type],
                        headers={"X-Content-Type-Options": "nosniff"})


@router.delete("/attachments/{attachment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_attachment(attachment_id: int, actor: User = Depends(get_current_user), db: Session = Depends(get_db)):
    lock_mutations(db)
    attachment = require_attachment(db, attachment_id)
    revision = require_revision(db, attachment.revision_id)
    require_editable(revision)
    path = attachment_path(attachment)
    record_audit(db, actor, "ATTACHMENT_DELETED", "REVISION", revision.id,
                 part_id=revision.part_id, attachment_id=attachment.id, filename=attachment.filename)
    # Keep bytes until the transaction commits; an orphan is safer than a missing live file.
    db.delete(attachment)
    db.commit()
    path.unlink(missing_ok=True)
    return Response(status_code=204)
