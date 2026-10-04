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


class Sponsor(Base):
    __tablename__ = "sponsors"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    contact_name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, unique=True)
    created_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    trials = relationship(
        "Trial",
        back_populates="sponsor_entity",
        passive_deletes=True,
    )


class Trial(Base):
    __tablename__ = "trials"

    id = Column(Integer, primary_key=True, autoincrement=True)
    brief_title = Column(
        "briefTitle",
        String(500),
        nullable=False,
    )
    nct_code = Column(String(11), nullable=False, unique=True)
    participant_count = Column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    sponsor_id = Column(
        Integer,
        ForeignKey("sponsors.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    created_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    sponsor_entity = relationship(
        "Sponsor",
        back_populates="trials",
    )

    details = relationship(
        "TrialDetail",
        back_populates="trial",
        cascade="all, delete-orphan",
    )

    @property
    def sponsor(self):
        """Keep the sponsor name in API output for UI compatibility."""
        return self.sponsor_entity.name


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
