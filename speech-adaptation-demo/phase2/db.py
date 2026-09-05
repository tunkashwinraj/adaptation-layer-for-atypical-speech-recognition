import os
from datetime import datetime

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    create_engine,
    Index,
)
from sqlalchemy.orm import declarative_base, sessionmaker


BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PROFILES_DIR = os.path.join(BASE_DIR, "profiles")
DB_PATH = os.path.join(PROFILES_DIR, "user_profiles.db")

os.makedirs(PROFILES_DIR, exist_ok=True)

engine = create_engine(f"sqlite:///{DB_PATH}", future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


class Profile(Base):
    __tablename__ = "profiles"
    user_id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    profile_data = Column(JSON, nullable=False)


class Correction(Base):
    __tablename__ = "corrections"
    id = Column(Integer, primary_key=True)
    user_id = Column(String, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    audio_path = Column(Text)
    asr_baseline = Column(Text)
    asr_personalized = Column(Text)
    user_correction = Column(Text)
    context = Column(Text)


class Vocabulary(Base):
    __tablename__ = "vocabulary"
    user_id = Column(String, primary_key=True)
    word = Column(String, primary_key=True)
    boost_value = Column(Float, default=1.5)
    frequency = Column(Integer, default=1)
    last_used = Column(DateTime, default=datetime.utcnow)


class PronunciationPattern(Base):
    __tablename__ = "pronunciation_patterns"
    user_id = Column(String, primary_key=True)
    standard_form = Column(String, primary_key=True)
    user_variant = Column(String, primary_key=True)
    confidence = Column(Float, default=0.5)
    occurrence_count = Column(Integer, default=1)


class Session(Base):
    __tablename__ = "sessions"
    session_id = Column(String, primary_key=True)
    user_id = Column(String, index=True)
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime)
    total_utterances = Column(Integer, default=0)
    correction_count = Column(Integer, default=0)
    metrics = Column(JSON, default={})


class ModelPerformance(Base):
    __tablename__ = "model_performance"
    id = Column(Integer, primary_key=True)
    user_id = Column(String, index=True)
    model_name = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)
    wer = Column(Float)
    semscore = Column(Float)
    latency_ms = Column(Float)
    cost_usd = Column(Float)
    meta = Column(JSON, default={})


class InteractionEvent(Base):
    """
    Tracks adaptive interaction state over time for a given session.
    Used in Phase 3 to analyze frustration dynamics and mode transitions.
    """

    __tablename__ = "interaction_events"

    id = Column(Integer, primary_key=True)
    session_id = Column(String, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    frustration_score = Column(Float)
    interaction_mode = Column(String)
    signals = Column(JSON, default={})
    user_response = Column(Text)


class StudyTaskAttempt(Base):
    """
    Minimal schema for Phase 3 simple user study interface.
    Stores per-task attempts for later CSV export.
    """

    __tablename__ = "study_task_attempts"

    id = Column(Integer, primary_key=True)
    participant_id = Column(String, index=True)
    task_number = Column(Integer)
    task_name = Column(String)
    audio_path = Column(Text)
    baseline_output = Column(Text)
    personalized_output = Column(Text)
    repaired_output = Column(Text)
    user_correction = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_participant_task", "participant_id", "task_number"),
    )


def init_db():
    Base.metadata.create_all(bind=engine)


def get_session():
    return SessionLocal()
