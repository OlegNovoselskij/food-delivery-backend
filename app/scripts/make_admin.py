import sys

from app.database import SessionLocal
from app.repository import user_repository


def main(email: str) -> None:
    db = SessionLocal()
    try:
        user = user_repository.get_by_email(db, email.lower())
        if user is None:
            print(f"User {email} not found. Register first, then run this again.")
            sys.exit(1)
        user.role = "admin"
        db.commit()
        print(f"{email} is now admin")
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python -m app.scripts.make_admin <email>")
        sys.exit(1)
    main(sys.argv[1])