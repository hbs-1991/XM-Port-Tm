"""Repository for user data access."""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.user import User
from src.core.database import get_db


class UserRepository:
    """Repository for user database operations."""
    
    async def get_by_email(self, email: str) -> Optional[User]:
        """
        Get a user by email address.
        
        Args:
            email: Email address to search for
            
        Returns:
            User object if found, None otherwise
        """
        async with get_db() as session:
            result = await session.execute(
                select(User).where(User.email == email)
            )
            return result.scalar_one_or_none()
    
    async def get_by_id(self, user_id: UUID) -> Optional[User]:
        """
        Get a user by ID.
        
        Args:
            user_id: UUID of the user
            
        Returns:
            User object if found, None otherwise
        """
        async with get_db() as session:
            result = await session.execute(
                select(User).where(User.id == user_id)
            )
            return result.scalar_one_or_none()
    
    async def create(self, user: User) -> User:
        """
        Create a new user in the database.
        
        Args:
            user: User object to create
            
        Returns:
            Created user object with ID
        """
        async with get_db() as session:
            session.add(user)
            await session.commit()  # Explicit commit for write operation
            await session.refresh(user)
            return user
    
    async def update(self, user: User) -> User:
        """
        Update an existing user in the database.
        
        Args:
            user: User object with updated values
            
        Returns:
            Updated user object
        """
        async with get_db() as session:
            await session.merge(user)
            await session.commit()
            await session.refresh(user)
            return user
    
    async def update_last_login(self, user_id: UUID) -> None:
        """
        Update user's last login timestamp.
        
        Args:
            user_id: UUID of the user
        """
        async with get_db() as session:
            user = await session.get(User, user_id)
            if user:
                user.last_login_at = datetime.now(timezone.utc)
                await session.commit()
    
    async def delete(self, user_id: UUID) -> bool:
        """
        Delete a user from the database.
        
        Args:
            user_id: UUID of the user to delete
            
        Returns:
            True if user was deleted, False if user was not found
        """
        async with get_db() as session:
            user = await session.get(User, user_id)
            if user:
                await session.delete(user)
                await session.commit()
                return True
            return False