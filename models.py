from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class Project(Base):
    __tablename__ = "projects"
    
    id = Column(String, primary_key=True, index=True)
    youtube_url = Column(String, nullable=False)
    video_id = Column(String, nullable=False, index=True)
    video_title = Column(String)
    video_duration = Column(Integer)
    status = Column(String, default="processing")  # processing, completed, failed
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    shorts = relationship("Short", back_populates="project", cascade="all, delete-orphan")

class Short(Base):
    __tablename__ = "shorts"
    
    id = Column(String, primary_key=True, index=True)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    filename = Column(String, nullable=False)
    title = Column(String)
    start_time = Column(Float, nullable=False)
    end_time = Column(Float, nullable=False)
    duration_seconds = Column(Float, nullable=False)
    engagement_score = Column(Float)
    marketing_effectiveness = Column(String)
    suggested_cta = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    project = relationship("Project", back_populates="shorts")
