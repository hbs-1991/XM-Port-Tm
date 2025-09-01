"""
Credit management service for processing credits
"""
from typing import Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import text
import logging

from src.models.user import User

logger = logging.getLogger(__name__)


class CreditService:
    """Service for managing user credits"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def check_user_credits(self, user: User, estimated_credits: int = 1) -> Dict[str, Any]:
        """
        Check if user has sufficient credits for processing
        
        Returns:
            Dict containing:
            - has_sufficient_credits: bool
            - credits_remaining: int
            - credits_required: int
            - message: str
        """
        has_sufficient = user.credits_remaining >= estimated_credits
        
        return {
            'has_sufficient_credits': has_sufficient,
            'credits_remaining': user.credits_remaining,
            'credits_required': estimated_credits,
            'message': self._generate_credit_message(user, estimated_credits, has_sufficient)
        }
    
    def _generate_credit_message(self, user: User, required_credits: int, has_sufficient: bool) -> str:
        """Generate appropriate credit-related message for user"""
        if has_sufficient:
            return f"Processing will use {required_credits} credit(s). You have {user.credits_remaining} remaining."
        
        shortage = required_credits - user.credits_remaining
        base_message = f"Insufficient credits: You need {required_credits} credit(s) but only have {user.credits_remaining} remaining."
        
        if user.subscription_tier.value == 'FREE':
            return f"{base_message} Upgrade to a paid plan or purchase additional credits to continue processing."
        else:
            return f"{base_message} Please purchase {shortage} more credit(s) to process this file."
    
    def calculate_processing_credits(self, total_rows: int) -> int:
        """
        Calculate credits required based on file size and complexity
        
        Pricing model:
        - Base cost: 1 credit for files up to 100 rows
        - Additional: 1 credit per 100 rows or part thereof
        """
        if total_rows <= 0:
            return 1  # Minimum cost for validation
        
        # Base credit + additional credits for larger files
        base_credits = 1
        additional_credits = (total_rows - 1) // 100  # Integer division
        
        return base_credits + additional_credits
    
    def reserve_user_credits(self, user: User, credits_to_reserve: int) -> bool:
        """
        Reserve credits for processing (atomic operation with proper concurrency handling)
        
        Args:
            user: User object
            credits_to_reserve: Number of credits to reserve
            
        Returns:
            bool: True if credits were successfully reserved
        """
        try:
            # Use database-level atomic update to prevent race conditions
            # This updates only if credits are sufficient and returns affected rows
            result = self.db.execute(
                text("""
                    UPDATE users 
                    SET 
                        credits_remaining = credits_remaining - :credits_to_reserve,
                        credits_used_this_month = credits_used_this_month + :credits_to_reserve,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE 
                        id = :user_id 
                        AND credits_remaining >= :credits_to_reserve
                        AND is_active = true
                """),
                {
                    "user_id": user.id,
                    "credits_to_reserve": credits_to_reserve
                }
            )
            
            # Check if any rows were affected (credit reservation successful)
            rows_affected = result.rowcount
            
            if rows_affected == 0:
                # Either insufficient credits or user not found/inactive
                self.db.rollback()
                return False
            
            # Commit the transaction
            self.db.commit()
            
            # Refresh user object to reflect the changes
            self.db.refresh(user)
            
            return True
            
        except (IntegrityError, Exception) as e:
            # Handle database constraints or other errors
            self.db.rollback()
            logger.error(f"Credit reservation failed for user {user.id}: {str(e)}")
            return False
    
    def refund_user_credits(self, user: User, credits_to_refund: int) -> bool:
        """
        Refund credits if processing fails
        
        Args:
            user: User object  
            credits_to_refund: Number of credits to refund
            
        Returns:
            bool: True if credits were successfully refunded
        """
        try:
            # Refresh user data
            self.db.refresh(user)
            
            # Refund credits
            user.credits_remaining += credits_to_refund
            user.credits_used_this_month = max(0, user.credits_used_this_month - credits_to_refund)
            
            self.db.commit()
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Credit refund failed for user {user.id}: {str(e)}")
            return False