import uuid
from datetime import datetime
from sqlalchemy import Column, UUID, DateTime, Boolean, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import declared_attr

Base = declarative_base()

class BaseModel(Base):
    """Base model class with common fields"""
    
    __abstract__ = True
    

