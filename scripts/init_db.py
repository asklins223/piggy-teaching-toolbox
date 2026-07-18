#!/usr/bin/env python3
"""Database initialization script.

Usage:
    python scripts/init_db.py

This script will create the database, all tables, and default admin user.
Run this once before starting the application for the first time.
"""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pymysql
from dotenv import load_dotenv

# Load .env file
load_dotenv()

from backend.db.models import (
    init_db, get_db_config, Base, get_engine,
    get_session_local, UserRecord, VoiceRecord, CharacterRecord,
    ProjectRecord, SceneRecord, ProjectCharacterRecord, hash_password
)


def create_database_if_not_exists():
    """Create database if it doesn't exist."""
    config = get_db_config()
    
    # Connect without database to create it
    connection = pymysql.connect(
        host=config.host,
        port=config.port,
        user=config.user,
        password=config.password,
        charset='utf8mb4'
    )
    
    try:
        with connection.cursor() as cursor:
            # Check if database exists
            cursor.execute(f"SHOW DATABASES LIKE '{config.database}'")
            exists = cursor.fetchone()
            
            if not exists:
                cursor.execute(
                    f"CREATE DATABASE `{config.database}` "
                    f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                )
                print(f"✅ Database '{config.database}' created")
                return True
            else:
                print(f"ℹ️  Database '{config.database}' already exists")
                return False
    finally:
        connection.close()


def create_default_admin():
    """Create default admin user from .env settings."""
    admin_username = os.getenv("ADMIN_USERNAME", "admin")
    admin_password = os.getenv("ADMIN_PASSWORD", "video123")
    admin_email = os.getenv("ADMIN_EMAIL", "")
    
    SessionLocal = get_session_local()
    db = SessionLocal()
    
    try:
        # Check if admin exists
        existing = db.query(UserRecord).filter(UserRecord.username == admin_username).first()
        
        if existing:
            print(f"ℹ️  Admin user '{admin_username}' already exists")
            return False
        
        # Create admin user
        admin = UserRecord(
            username=admin_username,
            password_hash=hash_password(admin_password),
            email=admin_email or None,
            is_active=True,
            is_admin=True,
        )
        db.add(admin)
        db.commit()
        
        print(f"✅ Admin user '{admin_username}' created")
        return True
    except Exception as e:
        db.rollback()
        print(f"⚠️  Failed to create admin user: {e}")
        return False
    finally:
        db.close()


def main():
    """Initialize database and tables."""
    config = get_db_config()
    
    print("=" * 50)
    print("Database Initialization")
    print("=" * 50)
    print(f"Host: {config.host}:{config.port}")
    print(f"Database: {config.database}")
    print(f"User: {config.user}")
    print(f"Admin: {os.getenv('ADMIN_USERNAME', 'admin')}")
    print("=" * 50)
    
    # Auto-confirm if running in Docker or with --yes flag
    auto_confirm = os.getenv("AUTO_CONFIRM", "").lower() in ("1", "true", "yes") or "--yes" in sys.argv
    
    if not auto_confirm:
        confirm = input("\nProceed with database/table creation? [y/N]: ").strip().lower()
        if confirm != 'y':
            print("Aborted.")
            return
    else:
        print("\n[Auto-confirm enabled]")
    
    try:
        # 1. Create database if not exists
        print("\n[1/3] Checking database...")
        create_database_if_not_exists()
        
        # 2. Create tables
        print("\n[2/3] Creating tables...")
        init_db()
        
        # List created tables
        tables = Base.metadata.tables.keys()
        print("✅ Tables created/verified:")
        for table in tables:
            print(f"   - {table}")
        
        # 3. Create default admin user
        print("\n[3/3] Creating default admin user...")
        create_default_admin()
        
        print("\n🎉 Database initialization complete!")
        
    except pymysql.err.OperationalError as e:
        print(f"\n❌ Connection Error: {e}")
        print("\nMake sure:")
        print("  1. MySQL server is running")
        print("  2. .env file has correct DB_HOST, DB_PORT, DB_USER, DB_PASSWORD")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
