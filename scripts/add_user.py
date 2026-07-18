#!/usr/bin/env python3
"""Add a new user to the database.

Usage:
    python scripts/add_user.py <username> <password> [--admin]
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from backend.db.models import get_session_local, UserRecord, hash_password


def add_user(username: str, password: str, is_admin: bool = False):
    """Add a new user to the database."""
    SessionLocal = get_session_local()
    db = SessionLocal()
    
    try:
        # Check if user exists
        existing = db.query(UserRecord).filter(UserRecord.username == username).first()
        
        if existing:
            print(f"❌ User '{username}' already exists")
            return False
        
        # Create user
        user = UserRecord(
            username=username,
            password_hash=hash_password(password),
            is_active=True,
            is_admin=is_admin,
        )
        db.add(user)
        db.commit()
        
        print(f"✅ User '{username}' created successfully")
        return True
    except Exception as e:
        db.rollback()
        print(f"❌ Failed to create user: {e}")
        return False
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python scripts/add_user.py <username> <password> [--admin]")
        sys.exit(1)
    
    username = sys.argv[1]
    password = sys.argv[2]
    is_admin = "--admin" in sys.argv
    
    add_user(username, password, is_admin)
