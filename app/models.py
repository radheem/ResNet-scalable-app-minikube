from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import Mapped, mapped_column

db = SQLAlchemy()

class ClassificationRequest(db.Model):
    __tablename__ = 'classification_requests'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    status: Mapped[str] = mapped_column(nullable=False)
    label: Mapped[str] = mapped_column(nullable=True)  # Make label nullable
    confidence: Mapped[float] = mapped_column(nullable=True)  # Add confidence column
    createdAt: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    updated: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
