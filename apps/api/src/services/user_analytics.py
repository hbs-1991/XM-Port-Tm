"""
User analytics service for dashboard statistics
"""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select, func, and_, extract
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.models.user import User
from src.models.processing_job import ProcessingJob, ProcessingStatus


class UserAnalyticsService:
    """Service for calculating user analytics and statistics"""

    async def get_user_statistics(self, user_id: UUID) -> dict:
        """
        Get comprehensive user statistics for dashboard display.
        
        Args:
            user_id: User ID to get statistics for
            
        Returns:
            Dictionary containing user statistics
        """
        async with get_db() as session:
            user = await session.get(User, user_id)
            if not user:
                raise ValueError("User not found")
            
            # Get current month/year
            now = datetime.now(timezone.utc)
            current_month = now.month
            current_year = now.year
            
            # Calculate processing statistics
            processing_stats = await self._calculate_processing_stats(session, user_id)
            
            # Calculate monthly usage
            monthly_usage = await self._calculate_monthly_usage(
                session, user_id, current_month, current_year
            )
            
            # Calculate credit balance info
            credit_balance = self._calculate_credit_balance(user)
            
            return {
                "totalJobs": processing_stats["total_jobs"],
                "successRate": processing_stats["success_rate"],
                "averageConfidence": processing_stats["average_confidence"],
                "monthlyUsage": monthly_usage,
                "creditBalance": credit_balance,
                "processingStats": {
                    "totalJobs": processing_stats["total_jobs"],
                    "completedJobs": processing_stats["completed_jobs"],
                    "failedJobs": processing_stats["failed_jobs"],
                    "successRate": processing_stats["success_rate"],
                    "averageConfidence": processing_stats["average_confidence"],
                    "totalProducts": processing_stats["total_products"],
                    "successfulMatches": processing_stats["successful_matches"]
                }
            }

    async def _calculate_processing_stats(self, session: AsyncSession, user_id: UUID) -> dict:
        """Calculate overall processing statistics for a user."""
        
        # Total jobs
        total_jobs_query = select(func.count(ProcessingJob.id)).where(
            ProcessingJob.user_id == user_id
        )
        total_jobs_result = await session.execute(total_jobs_query)
        total_jobs = total_jobs_result.scalar() or 0
        
        # Completed jobs
        completed_jobs_query = select(func.count(ProcessingJob.id)).where(
            and_(
                ProcessingJob.user_id == user_id,
                ProcessingJob.status.in_([
                    ProcessingStatus.COMPLETED, 
                    ProcessingStatus.COMPLETED_WITH_ERRORS
                ])
            )
        )
        completed_jobs_result = await session.execute(completed_jobs_query)
        completed_jobs = completed_jobs_result.scalar() or 0
        
        # Failed jobs
        failed_jobs_query = select(func.count(ProcessingJob.id)).where(
            and_(
                ProcessingJob.user_id == user_id,
                ProcessingJob.status == ProcessingStatus.FAILED
            )
        )
        failed_jobs_result = await session.execute(failed_jobs_query)
        failed_jobs = failed_jobs_result.scalar() or 0
        
        # Total products and successful matches
        products_query = select(
            func.coalesce(func.sum(ProcessingJob.total_products), 0),
            func.coalesce(func.sum(ProcessingJob.successful_matches), 0)
        ).where(
            and_(
                ProcessingJob.user_id == user_id,
                ProcessingJob.status.in_([
                    ProcessingStatus.COMPLETED, 
                    ProcessingStatus.COMPLETED_WITH_ERRORS
                ])
            )
        )
        products_result = await session.execute(products_query)
        products_row = products_result.first()
        total_products = products_row[0] if products_row else 0
        successful_matches = products_row[1] if products_row else 0
        
        # Average confidence
        confidence_query = select(
            func.avg(ProcessingJob.average_confidence)
        ).where(
            and_(
                ProcessingJob.user_id == user_id,
                ProcessingJob.status.in_([
                    ProcessingStatus.COMPLETED, 
                    ProcessingStatus.COMPLETED_WITH_ERRORS
                ]),
                ProcessingJob.average_confidence.is_not(None)
            )
        )
        confidence_result = await session.execute(confidence_query)
        average_confidence = confidence_result.scalar()
        average_confidence = float(average_confidence) * 100 if average_confidence else 0.0
        
        # Calculate success rate
        success_rate = (completed_jobs / total_jobs * 100) if total_jobs > 0 else 0.0
        
        return {
            "total_jobs": total_jobs,
            "completed_jobs": completed_jobs,
            "failed_jobs": failed_jobs,
            "success_rate": success_rate,
            "total_products": total_products,
            "successful_matches": successful_matches,
            "average_confidence": average_confidence
        }

    async def _calculate_monthly_usage(
        self, 
        session: AsyncSession, 
        user_id: UUID, 
        month: int, 
        year: int
    ) -> dict:
        """Calculate monthly usage statistics."""
        
        # Credits used this month
        credits_query = select(
            func.coalesce(func.sum(ProcessingJob.credits_used), 0)
        ).where(
            and_(
                ProcessingJob.user_id == user_id,
                extract('month', ProcessingJob.created_at) == month,
                extract('year', ProcessingJob.created_at) == year
            )
        )
        credits_result = await session.execute(credits_query)
        credits_used = credits_result.scalar() or 0
        
        # Jobs completed this month
        jobs_query = select(func.count(ProcessingJob.id)).where(
            and_(
                ProcessingJob.user_id == user_id,
                extract('month', ProcessingJob.created_at) == month,
                extract('year', ProcessingJob.created_at) == year,
                ProcessingJob.status.in_([
                    ProcessingStatus.COMPLETED, 
                    ProcessingStatus.COMPLETED_WITH_ERRORS
                ])
            )
        )
        jobs_result = await session.execute(jobs_query)
        jobs_completed = jobs_result.scalar() or 0
        
        # Files processed (same as jobs for now)
        files_processed = jobs_completed
        
        # Average processing time this month
        processing_time_query = select(
            func.avg(ProcessingJob.processing_time_ms)
        ).where(
            and_(
                ProcessingJob.user_id == user_id,
                extract('month', ProcessingJob.created_at) == month,
                extract('year', ProcessingJob.created_at) == year,
                ProcessingJob.processing_time_ms.is_not(None)
            )
        )
        processing_time_result = await session.execute(processing_time_query)
        average_processing_time = processing_time_result.scalar() or 0
        
        # Get month name
        month_names = [
            "", "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December"
        ]
        month_name = month_names[month] if 1 <= month <= 12 else "Unknown"
        
        return {
            "creditsUsed": credits_used,
            "jobsCompleted": jobs_completed,
            "filesProcessed": files_processed,
            "averageProcessingTime": int(average_processing_time) if average_processing_time else 0,
            "month": month_name,
            "year": year
        }

    def _calculate_credit_balance(self, user: User) -> dict:
        """Calculate credit balance information."""
        total_credits = user.credits_remaining + user.credits_used_this_month
        percentage_used = (user.credits_used_this_month / total_credits * 100) if total_credits > 0 else 0
        
        return {
            "remaining": user.credits_remaining,
            "total": total_credits,
            "usedThisMonth": user.credits_used_this_month,
            "percentageUsed": percentage_used,
            "subscriptionTier": user.subscription_tier.value
        }

    async def get_user_profile(self, user_id: UUID) -> Optional[dict]:
        """
        Get user profile information.
        
        Args:
            user_id: User ID to get profile for
            
        Returns:
            User profile dictionary or None if not found
        """
        async with get_db() as session:
            user = await session.get(User, user_id)
            if not user:
                return None
            
            return {
                "id": str(user.id),
                "email": user.email,
                "firstName": user.first_name,
                "lastName": user.last_name,
                "companyName": user.company_name,
                "country": user.country,
                "subscriptionTier": user.subscription_tier.value,
                "creditsRemaining": user.credits_remaining,
                "creditsUsedThisMonth": user.credits_used_this_month,
                "isActive": user.is_active,
                "createdAt": user.created_at.isoformat(),
                "lastLoginAt": user.last_login_at.isoformat() if user.last_login_at else None
            }

    async def update_user_profile(
        self, 
        user_id: UUID, 
        profile_data: dict
    ) -> Optional[dict]:
        """
        Update user profile information.
        
        Args:
            user_id: User ID to update
            profile_data: Dictionary containing profile updates
            
        Returns:
            Updated user profile dictionary or None if user not found
        """
        async with get_db() as session:
            user = await session.get(User, user_id)
            if not user:
                return None
            
            # Update allowed fields
            allowed_fields = ['first_name', 'last_name', 'company_name', 'country']
            field_mapping = {
                'firstName': 'first_name',
                'lastName': 'last_name', 
                'companyName': 'company_name',
                'country': 'country'
            }
            
            for key, value in profile_data.items():
                if key in field_mapping and field_mapping[key] in allowed_fields:
                    setattr(user, field_mapping[key], value)
            
            await session.commit()
            await session.refresh(user)
            
            return await self.get_user_profile(user_id)


# Create service instance
user_analytics_service = UserAnalyticsService()