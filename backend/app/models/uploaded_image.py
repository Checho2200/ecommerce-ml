"""
Imagenes subidas desde el panel de administracion.

Se guardan en la base de datos y no en disco porque el plan gratuito de Render
usa un sistema de archivos efimero: cada redespliegue o cada arranque tras la
suspension por inactividad borraba las imagenes que el administrador habia
subido, dejando los productos sin foto.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class UploadedImage(Base):
    __tablename__ = "uploaded_images"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    data: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    def __repr__(self) -> str:
        return f"<UploadedImage {self.id[:8]} ({self.content_type})>"
