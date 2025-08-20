#!/usr/bin/env python3
"""
Database seeding script for XM-Port
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'apps', 'api', 'src'))

from models.base import SessionLocal, engine
from models import User, HSCode, UserRole
from passlib.context import CryptContext

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def seed_users(db):
    """Seed initial users"""
    # Create admin user
    admin_user = User(
        email="admin@xm-port.com",
        name="Admin User",
        hashed_password=hash_password("admin123"),
        role=UserRole.ADMIN,
        credits=1000,
        is_active=True
    )
    
    # Create test user
    test_user = User(
        email="test@example.com",
        name="Test User",
        hashed_password=hash_password("password123"),
        role=UserRole.USER,
        credits=100,
        is_active=True
    )
    
    db.add(admin_user)
    db.add(test_user)
    print("✅ Seeded users")

def seed_hs_codes(db):
    """Seed sample HS codes"""
    sample_codes = [
        {
            "code": "0101.10.00",
            "description": "Live horses - Pure-bred breeding animals",
            "category": "Live Animals"
        },
        {
            "code": "0101.90.00", 
            "description": "Live horses - Other",
            "category": "Live Animals"
        },
        {
            "code": "8471.30.01",
            "description": "Portable automatic data processing machines weighing not more than 10 kg",
            "category": "Electronic Equipment"
        },
        {
            "code": "8471.41.01",
            "description": "Data processing machines - comprising CPU and input/output units",
            "category": "Electronic Equipment"
        },
        {
            "code": "9403.10.00",
            "description": "Metal furniture of a kind used in offices",
            "category": "Furniture"
        }
    ]
    
    for code_data in sample_codes:
        hs_code = HSCode(
            code=code_data["code"],
            description=code_data["description"],
            category=code_data["category"]
        )
        db.add(hs_code)
    
    print("✅ Seeded HS codes")

def main():
    """Main seeding function"""
    print("🌱 Starting database seeding...")
    
    # Create tables
    from models.base import Base
    Base.metadata.create_all(bind=engine)
    print("✅ Created database tables")
    
    # Create session
    db = SessionLocal()
    
    try:
        # Check if data already exists
        if db.query(User).first():
            print("⚠️  Database already seeded, skipping...")
            return
        
        # Seed data
        seed_users(db)
        seed_hs_codes(db)
        
        # Commit changes
        db.commit()
        print("🎉 Database seeding completed successfully!")
        
    except Exception as e:
        print(f"❌ Error seeding database: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    main()