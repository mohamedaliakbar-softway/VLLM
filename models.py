from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, index=True)  # Replit user ID (sub claim)
    email = Column(String, unique=True, nullable=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    profile_image_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

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
    platform_title = Column(String)
    platform_description = Column(Text)
    hashtags = Column(Text)
    cta = Column(Text)
    captions_srt = Column(Text)
    captions_alt = Column(Text)
    language = Column(String)
    thumbnail_copy = Column(Text)
    thumbnail_style = Column(Text)
    
    project = relationship("Project", back_populates="shorts")
    publications = relationship("Publication", back_populates="short", cascade="all, delete-orphan")

class Publication(Base):
    __tablename__ = "publications"
    
    id = Column(String, primary_key=True, index=True)
    short_id = Column(String, ForeignKey("shorts.id"), nullable=False)
    platform = Column(String, nullable=False)  # linkedin, instagram, x, youtube_shorts, tiktok
    status = Column(String, default="queued")  # queued, processing, published, failed
    error_message = Column(Text, nullable=True)
    external_post_id = Column(String, nullable=True)
    external_url = Column(String, nullable=True)
    payload = Column(Text, nullable=True)  # JSON blob of request sent
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    short = relationship("Short", back_populates="publications")


class AccountToken(Base):
    __tablename__ = "account_tokens"
    
    id = Column(String, primary_key=True, index=True)
    platform = Column(String, nullable=False)  # linkedin, instagram, x
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    user_id = Column(String, nullable=True)  # optional: future multi-user support
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
