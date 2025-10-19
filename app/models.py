from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, UniqueConstraint, CheckConstraint
from sqlalchemy.orm import relationship
from datetime import datetime

from .database import Base

class Team(Base):
    __tablename__ = "teams"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    pass_hash = Column(String, nullable=False)
    originals = relationship("Original", back_populates="team")
    attempts = relationship("Attempt", back_populates="team")

class Original(Base):
    __tablename__ = "originals"
    id = Column(Integer, primary_key=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    filepath = Column(String, nullable=False)
    note = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    team = relationship("Team", back_populates="originals")
    attempts = relationship("Attempt", back_populates="original")

class Attempt(Base):
    __tablename__ = "attempts"
    id = Column(Integer, primary_key=True)
    original_id = Column(Integer, ForeignKey("originals.id"), nullable=False)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    filepath = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    original = relationship("Original", back_populates="attempts")
    team = relationship("Team", back_populates="attempts")
    judgment = relationship("Judgment", back_populates="attempt", uselist=False)

class Judgment(Base):
    __tablename__ = "judgments"
    id = Column(Integer, primary_key=True)
    attempt_id = Column(Integer, ForeignKey("attempts.id"), nullable=False, unique=True)
    verdict = Column(String, CheckConstraint("verdict IN ('match','no-match')"), nullable=False)
    comment = Column(Text)
    juror = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    attempt = relationship("Attempt", back_populates="judgment")

class Setting(Base):
    __tablename__ = "settings"
    key = Column(String, primary_key=True)
    value = Column(String, nullable=False)
