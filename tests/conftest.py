"""Pytest configuration and shared fixtures."""

import os
import pytest
import tempfile
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.db.models import Base, UserRecord, hash_password


# Test credentials
TEST_USERNAME = "testuser"
TEST_PASSWORD = "testpassword123"


@pytest.fixture
def temp_dir():
    """Provide a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def project_dir(temp_dir):
    """Provide a project directory structure for tests."""
    project_path = temp_dir / "test_project"
    project_path.mkdir(parents=True)
    (project_path / "characters").mkdir()
    (project_path / "clips").mkdir()
    (project_path / "output").mkdir()
    return project_path


@pytest.fixture(scope="function")
def test_db():
    """Create a test database with a test user."""
    # Create in-memory SQLite database
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    # Create test user
    test_user = UserRecord(
        username=TEST_USERNAME,
        password_hash=hash_password(TEST_PASSWORD),
        email="test@example.com",
        is_active=True,
        is_admin=False
    )
    session.add(test_user)
    session.commit()
    
    yield session
    
    session.close()
