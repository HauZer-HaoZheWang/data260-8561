from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    email = Column(String(255), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)


class SessionToken(Base):
    __tablename__ = "sessions"

    id = Column(String(255), primary_key=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )
    expires_at = Column(DateTime, nullable=False)


class Trial(Base):
    __tablename__ = "trials"

    id = Column(Integer, primary_key=True, autoincrement=True)
    brief_title = Column(
        "briefTitle",
        String(500),
        nullable=False,
    )
    sponsor = Column(String(255), nullable=False)

    details = relationship(
        "TrialDetail",
        back_populates="trial",
        cascade="all, delete-orphan",
    )


class TrialDetail(Base):
    __tablename__ = "trial_details"

    id = Column(Integer, primary_key=True, autoincrement=True)
    trial_id = Column(
        Integer,
        ForeignKey("trials.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    detail = Column(String(500), nullable=False)

    trial = relationship(
        "Trial",
        back_populates="details",
    )
