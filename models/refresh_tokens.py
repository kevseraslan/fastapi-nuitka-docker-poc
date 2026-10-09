from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from .base import BaseModel

class RefreshTokens(BaseModel):
    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token = Column(String(500), nullable=False, unique=True)
    expires_at = Column(DateTime, nullable=False)
    is_revoked = Column(Boolean, nullable=False, default=False)

    user = relationship("Users", back_populates="refresh_tokens")

    def __repr__(self):
        return f"<RefreshTokens(id={self.id}, user_id={self.user_id}, token='{self.token[:20]}...')>"