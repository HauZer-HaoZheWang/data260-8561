"""Create deterministic HW7 role accounts after running migrate_hw7."""
from passlib.context import CryptContext
from sqlalchemy.exc import IntegrityError

from database import SessionLocal
from models import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
USERS = [("reader8561", "reader8561@example.edu", "reader"), ("writer8561", "writer8561@example.edu", "writer"), ("moderator8561", "moderator8561@example.edu", "moderator")]


def seed():
    db = SessionLocal()
    try:
        for username, email, role in USERS:
            if db.query(User).filter(User.username == username).first(): continue
            db.add(User(name=username, username=username, email=email, role=role, password_hash=pwd_context.hash("Password8561!")))
        try: db.commit()
        except IntegrityError: db.rollback()
    finally: db.close()
    print("HW7 role users ready; password=Password8561!")


if __name__ == "__main__": seed()
