import uuid
import datetime
from app.database import Base, HAS_SQLALCHEMY

if HAS_SQLALCHEMY:
    from sqlalchemy import Column, String, Integer, DateTime, Text, JSON

    class UserModel(Base):
        __tablename__ = "users"

        id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
        username = Column(String, unique=True, index=True, nullable=False)
        email = Column(String, unique=True, index=True, nullable=False)
        hashed_password = Column(String, nullable=False)
        created_at = Column(DateTime, default=datetime.datetime.utcnow)

    class JobModel(Base):
        __tablename__ = "jobs"

        job_id = Column(String, primary_key=True, default=lambda: uuid.uuid4().hex[:12])
        pipeline = Column(String, nullable=False)  # "static_posts" or "faceless_video"
        status = Column(String, default="queued")  # queued, running, done, failed
        stage = Column(String, default="initialized")
        progress = Column(Integer, default=0)
        created_at = Column(DateTime, default=datetime.datetime.utcnow)
        updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
        error = Column(Text, nullable=True)
        script_data = Column(JSON, nullable=True)
        output_urls = Column(JSON, nullable=True)
else:
    UserModel = None
    JobModel = None
