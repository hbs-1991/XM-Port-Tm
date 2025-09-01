"""
User profile and statistics API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status
from uuid import UUID
from pydantic import BaseModel
from typing import Optional

from src.core.auth import get_current_user
from src.models.user import User
from src.services.user_analytics import user_analytics_service


router = APIRouter(prefix="/users", tags=["users"])


class ProfileUpdateRequest(BaseModel):
    """Request model for profile updates"""
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    companyName: Optional[str] = None
    country: Optional[str] = None


class UserProfileResponse(BaseModel):
    """Response model for user profile"""
    id: str
    email: str
    firstName: str
    lastName: str
    companyName: Optional[str]
    country: str
    subscriptionTier: str
    creditsRemaining: int
    creditsUsedThisMonth: int
    isActive: bool
    createdAt: str
    lastLoginAt: Optional[str]


class CreditBalanceResponse(BaseModel):
    """Response model for credit balance"""
    remaining: int
    total: int
    usedThisMonth: int
    percentageUsed: float
    subscriptionTier: str


class ProcessingStatsResponse(BaseModel):
    """Response model for processing statistics"""
    total_jobs: int
    completed_jobs: int
    failed_jobs: int
    success_rate: float
    total_products: int
    successful_matches: int
    average_confidence: float


class MonthlyUsageResponse(BaseModel):
    """Response model for monthly usage"""
    creditsUsed: int
    jobsCompleted: int
    filesProcessed: int
    averageProcessingTime: int
    month: str
    year: int


class UserStatisticsResponse(BaseModel):
    """Response model for comprehensive user statistics"""
    totalJobs: int
    successRate: float
    averageConfidence: float
    monthlyUsage: MonthlyUsageResponse
    creditBalance: CreditBalanceResponse
    processingStats: ProcessingStatsResponse


@router.get("/profile", response_model=UserProfileResponse)
async def get_user_profile(current_user: User = Depends(get_current_user)):
    """
    Get current user profile information.
    
    Returns:
        User profile data
    """
    try:
        profile = await user_analytics_service.get_user_profile(current_user.id)
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User profile not found"
            )
        return profile
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching user profile: {str(e)}"
        )


@router.put("/profile", response_model=UserProfileResponse)
async def update_user_profile(
    profile_update: ProfileUpdateRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Update current user profile information.
    
    Args:
        profile_update: Profile update data
        
    Returns:
        Updated user profile data
    """
    try:
        # Convert to dict and remove None values
        update_data = {k: v for k, v in profile_update.model_dump().items() if v is not None}
        
        updated_profile = await user_analytics_service.update_user_profile(
            current_user.id, 
            update_data
        )
        
        if not updated_profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
            
        return updated_profile
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating user profile: {str(e)}"
        )


@router.get("/statistics", response_model=UserStatisticsResponse)
async def get_user_statistics(current_user: User = Depends(get_current_user)):
    """
    Get comprehensive user statistics for dashboard display.
    
    Returns:
        User statistics including processing stats, credit balance, and monthly usage
    """
    try:
        statistics = await user_analytics_service.get_user_statistics(current_user.id)
        return statistics
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching user statistics: {str(e)}"
        )