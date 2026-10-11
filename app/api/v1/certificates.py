from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependency import get_current_user
from app.models.user import User
from app.schemas.certificate import CertificateOut, CertificateVerifyOut
from app.services import certificate_service

router = APIRouter(tags=["certificates"])


@router.get("/certificates/mine", response_model=list[CertificateOut])
def my_certificates(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return certificate_service.list_mine(db, user)


@router.get("/certificates/verify/{number}", response_model=CertificateVerifyOut)
def verify_certificate(number: str, db: Session = Depends(get_db)):
    return certificate_service.verify(db, number)


@router.get("/certificates/{certificate_id}/pdf", response_class=Response)
def certificate_pdf(certificate_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    pdf, filename = certificate_service.render_pdf(db, certificate_id, user)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
