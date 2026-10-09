from sqlalchemy import Column, String, Integer, Boolean
from sqlalchemy.orm import relationship
from .base import BaseModel


class Users(BaseModel):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)

    # Relationships
    # A user can have multiple refresh tokens.
    # This implies that the 'refresh_tokens' table has a foreign key column (e.g., user_id)
    # referencing the 'id' of the users table.
    refresh_tokens = relationship("RefreshTokens", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}')>"