#!/usr/bin/env python3
"""
Database seeding script for XM-Port
"""
import sys
import os
import uuid
from decimal import Decimal
from datetime import datetime
import numpy as np

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'apps', 'api', 'src'))

from models.base import SessionLocal, engine
from models import (
    User, HSCode, ProcessingJob, ProductMatch, BillingTransaction,
    UserRole, SubscriptionTier, ProcessingStatus, 
    BillingTransactionType, BillingTransactionStatus
)
from passlib.context import CryptContext

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def create_sample_embedding():
    """Create a sample 1536-dimension embedding for testing"""
    return np.random.random(1536).tolist()

def seed_users(db):
    """Seed initial users with different roles and subscription tiers"""
    users = [
        {
            "email": "admin@xm-port.com",
            "hashed_password": hash_password("admin123"),
            "role": UserRole.ADMIN,
            "subscription_tier": SubscriptionTier.ENTERPRISE,
            "credits_remaining": 1000,
            "credits_used_this_month": 50,
            "company": "XM-Port Inc",
            "country": "USA",
            "is_active": True
        },
        {
            "email": "project@xm-port.com", 
            "hashed_password": hash_password("project123"),
            "role": UserRole.PROJECT_OWNER,
            "subscription_tier": SubscriptionTier.PREMIUM,
            "credits_remaining": 500,
            "credits_used_this_month": 25,
            "company": "Project Management Corp",
            "country": "CAN",
            "is_active": True
        },
        {
            "email": "test@example.com",
            "hashed_password": hash_password("password123"),
            "role": UserRole.USER,
            "subscription_tier": SubscriptionTier.FREE,
            "credits_remaining": 2,
            "credits_used_this_month": 3,
            "company": "Test Company",
            "country": "GBR",
            "is_active": True
        },
        {
            "email": "premium@example.com",
            "hashed_password": hash_password("premium123"),
            "role": UserRole.USER,
            "subscription_tier": SubscriptionTier.BASIC,
            "credits_remaining": 50,
            "credits_used_this_month": 15,
            "company": "Premium Corp",
            "country": "DEU",
            "is_active": True
        }
    ]
    
    for user_data in users:
        user = User(**user_data)
        db.add(user)
    
    print("✅ Seeded users with different roles and subscription tiers")

def seed_hs_codes(db):
    """Seed sample HS codes with proper embeddings for testing"""
    sample_codes = [
        {
            "code": "0101100000",
            "description": "Live horses - Pure-bred breeding animals",
            "chapter": "01",
            "section": "01",
            "country": "USA",
            "is_active": True
        },
        {
            "code": "0101900000", 
            "description": "Live horses - Other",
            "chapter": "01",
            "section": "01",
            "country": "USA",
            "is_active": True
        },
        {
            "code": "8471300100",
            "description": "Portable automatic data processing machines weighing not more than 10 kg",
            "chapter": "84",
            "section": "16",
            "country": "USA",
            "is_active": True
        },
        {
            "code": "8471410100",
            "description": "Data processing machines - comprising CPU and input/output units",
            "chapter": "84",
            "section": "16",
            "country": "USA",
            "is_active": True
        },
        {
            "code": "9403100000",
            "description": "Metal furniture of a kind used in offices",
            "chapter": "94",
            "section": "20",
            "country": "USA",
            "is_active": True
        },
        {
            "code": "0101100000",
            "description": "Live horses - Pure-bred breeding animals (EU)",
            "chapter": "01",
            "section": "01",
            "country": "EUR",
            "is_active": True
        }
    ]
    
    for code_data in sample_codes:
        # Create sample embedding for testing
        code_data["embedding"] = create_sample_embedding()
        hs_code = HSCode(**code_data)
        db.add(hs_code)
    
    print("✅ Seeded HS codes with proper embeddings")

def seed_processing_jobs(db):
    """Seed sample processing jobs in various states"""
    # Get sample users
    users = db.query(User).all()
    if not users:
        print("⚠️ No users found, skipping processing jobs")
        return
    
    jobs = [
        {
            "user_id": users[0].id,
            "status": ProcessingStatus.COMPLETED,
            "input_file_name": "sample_products.xlsx",
            "input_file_url": "https://s3.example.com/files/sample_products.xlsx",
            "input_file_size": 1024000,
            "output_xml_url": "https://s3.example.com/outputs/result.xml",
            "credits_used": 5,
            "processing_time_ms": 15000,
            "total_products": 10,
            "successful_matches": 8,
            "average_confidence": Decimal("0.85"),
            "country_schema": "USA",
            "started_at": datetime.now(),
            "completed_at": datetime.now()
        },
        {
            "user_id": users[1].id,
            "status": ProcessingStatus.PROCESSING,
            "input_file_name": "import_manifest.csv",
            "input_file_url": "https://s3.example.com/files/import_manifest.csv",
            "input_file_size": 2048000,
            "credits_used": 3,
            "total_products": 15,
            "successful_matches": 0,
            "country_schema": "CAN",
            "started_at": datetime.now()
        },
        {
            "user_id": users[2].id,
            "status": ProcessingStatus.FAILED,
            "input_file_name": "invalid_format.txt",
            "input_file_url": "https://s3.example.com/files/invalid_format.txt",
            "input_file_size": 512000,
            "credits_used": 1,
            "total_products": 0,
            "successful_matches": 0,
            "country_schema": "GBR",
            "error_message": "Invalid file format: Expected Excel or CSV file",
            "started_at": datetime.now(),
            "completed_at": datetime.now()
        }
    ]
    
    for job_data in jobs:
        job = ProcessingJob(**job_data)
        db.add(job)
    
    print("✅ Seeded processing jobs in various states")

def seed_product_matches(db):
    """Seed sample product matches with confidence scores"""
    # Get completed job
    completed_job = db.query(ProcessingJob).filter(ProcessingJob.status == ProcessingStatus.COMPLETED).first()
    if not completed_job:
        print("⚠️ No completed jobs found, skipping product matches")
        return
    
    matches = [
        {
            "job_id": completed_job.id,
            "product_description": "Apple MacBook Pro 16-inch laptop computer",
            "quantity": Decimal("2.000"),
            "unit_of_measure": "pieces",
            "value": Decimal("5000.00"),
            "origin_country": "CHN",
            "matched_hs_code": "8471300100",
            "confidence_score": Decimal("0.92"),
            "alternative_hs_codes": ["8471410100", "8471490000"],
            "requires_manual_review": False,
            "user_confirmed": True
        },
        {
            "job_id": completed_job.id,
            "product_description": "Office desk - metal frame with wooden top",
            "quantity": Decimal("5.000"),
            "unit_of_measure": "pieces", 
            "value": Decimal("1500.00"),
            "origin_country": "MEX",
            "matched_hs_code": "9403100000",
            "confidence_score": Decimal("0.78"),
            "alternative_hs_codes": ["9403200000"],
            "requires_manual_review": True,
            "user_confirmed": False
        }
    ]
    
    for match_data in matches:
        match = ProductMatch(**match_data)
        db.add(match)
    
    print("✅ Seeded product matches with confidence scores")

def seed_billing_transactions(db):
    """Seed sample billing transactions for testing"""
    users = db.query(User).all()
    if not users:
        print("⚠️ No users found, skipping billing transactions")
        return
    
    transactions = [
        {
            "user_id": users[0].id,
            "type": BillingTransactionType.CREDIT_PURCHASE,
            "amount": Decimal("50.00"),
            "currency": "USD",
            "credits_granted": 100,
            "payment_provider": "stripe",
            "payment_id": "pi_1234567890",
            "status": BillingTransactionStatus.COMPLETED
        },
        {
            "user_id": users[1].id,
            "type": BillingTransactionType.SUBSCRIPTION,
            "amount": Decimal("29.99"),
            "currency": "USD",
            "credits_granted": 500,
            "payment_provider": "stripe",
            "payment_id": "sub_0987654321",
            "status": BillingTransactionStatus.COMPLETED
        },
        {
            "user_id": users[2].id,
            "type": BillingTransactionType.CREDIT_PURCHASE,
            "amount": Decimal("10.00"),
            "currency": "USD",
            "credits_granted": 20,
            "payment_provider": "paypal",
            "payment_id": "PAYID-123456",
            "status": BillingTransactionStatus.PENDING
        }
    ]
    
    for transaction_data in transactions:
        transaction = BillingTransaction(**transaction_data)
        db.add(transaction)
    
    print("✅ Seeded billing transactions for testing")

def main():
    """Main seeding function"""
    print("🌱 Starting database seeding...")
    
    # Create session
    db = SessionLocal()
    
    try:
        # Check if data already exists
        if db.query(User).first():
            print("⚠️  Database already seeded, skipping...")
            return
        
        # Seed data in order to maintain referential integrity
        seed_users(db)
        seed_hs_codes(db)
        db.commit()  # Commit users and hs_codes first
        
        seed_processing_jobs(db)
        db.commit()  # Commit jobs before matches
        
        seed_product_matches(db)
        seed_billing_transactions(db)
        
        # Final commit
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