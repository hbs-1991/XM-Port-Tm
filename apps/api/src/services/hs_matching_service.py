"""
HS Code Matching Service using OpenAI Agents SDK

This service provides intelligent HS code matching for product descriptions
using OpenAI's Vector Store and semantic search capabilities.
"""

import asyncio
import time
import logging
from typing import List, Optional, Dict, Any
from decimal import Decimal

from agents import Runner
from pydantic import BaseModel, Field

from ..core.openai_config import OpenAIAgentConfig, HSCodeResult, HSCodeMatchResult
from ..schemas.processing import ProductData


# Configure logging
logger = logging.getLogger(__name__)


class HSCodeMatchRequest(BaseModel):
    """Request schema for HS code matching"""
    product_description: str = Field(..., min_length=5, max_length=500, description="Product description to match")
    country: str = Field(default="default", description="Country code for specific HS code variations")
    include_alternatives: bool = Field(default=True, description="Whether to include alternative matches")
    confidence_threshold: float = Field(default=0.7, ge=0.0, le=1.0, description="Minimum confidence threshold")


class HSCodeBatchMatchRequest(BaseModel):
    """Request schema for batch HS code matching"""
    products: List[HSCodeMatchRequest] = Field(..., min_items=1, max_items=100, description="List of products to match")
    country: str = Field(default="default", description="Default country code for all products")


class HSCodeMatchingService:
    """Service for matching product descriptions to HS codes using OpenAI Agents SDK"""
    
    # Configuration constants
    MAX_RETRY_ATTEMPTS = 3
    RETRY_DELAY_SECONDS = 1.0
    BATCH_SIZE_LIMIT = 50
    TIMEOUT_SECONDS = 30
    
    # Confidence thresholds
    HIGH_CONFIDENCE_THRESHOLD = 0.95
    MEDIUM_CONFIDENCE_THRESHOLD = 0.8
    LOW_CONFIDENCE_THRESHOLD = 0.5
    
    def __init__(self):
        """Initialize the HS Code Matching Service"""
        self.agent_config = OpenAIAgentConfig()
        self._agents_cache: Dict[str, Any] = {}
        logger.info("HSCodeMatchingService initialized")
    
    def _get_or_create_agent(self, country: str = "default"):
        """Get or create an agent for the specified country with caching"""
        if country not in self._agents_cache:
            self._agents_cache[country] = self.agent_config.create_agent(country)
            logger.info(f"Created new agent for country: {country}")
        return self._agents_cache[country]
    
    async def match_single_product(
        self, 
        product_description: str, 
        country: str = "default",
        include_alternatives: bool = True,
        confidence_threshold: float = 0.7
    ) -> HSCodeMatchResult:
        """
        Match a single product description to HS codes
        
        Args:
            product_description: Description of the product to match
            country: Country code for specific HS code variations
            include_alternatives: Whether to include alternative matches
            confidence_threshold: Minimum confidence threshold for matches
            
        Returns:
            HSCodeMatchResult: Matching result with primary and alternative matches
            
        Raises:
            ValueError: If product description is invalid
            ConnectionError: If OpenAI API is unavailable
            TimeoutError: If matching takes too long
        """
        start_time = time.time()
        
        # Validate input
        if not product_description or len(product_description.strip()) < 5:
            raise ValueError("Product description must be at least 5 characters long")
        
        # Clean and prepare the description
        cleaned_description = self._clean_product_description(product_description)
        
        # Get or create agent for country
        agent = self._get_or_create_agent(country)
        
        # Build search query with context
        search_query = self._build_search_query(cleaned_description, include_alternatives)
        
        try:
            # Execute matching with retry logic
            primary_result = await self._execute_with_retry(agent, search_query)
            
            # Calculate processing time
            processing_time = (time.time() - start_time) * 1000  # Convert to milliseconds
            
            # Process and validate results
            processed_result = self._process_matching_result(
                primary_result, 
                cleaned_description, 
                processing_time,
                confidence_threshold,
                include_alternatives
            )
            
            logger.info(f"Successfully matched HS code for product: {product_description[:50]}... "
                       f"(Primary: {processed_result.primary_match.hs_code}, "
                       f"Confidence: {processed_result.primary_match.confidence:.3f}, "
                       f"Time: {processing_time:.0f}ms)")
            
            return processed_result
            
        except Exception as e:
            logger.error(f"Failed to match HS code for product: {product_description[:50]}... Error: {str(e)}")
            raise
    
    async def match_batch_products(
        self,
        requests: List[HSCodeMatchRequest],
        max_concurrent: int = 5
    ) -> List[HSCodeMatchResult]:
        """
        Match multiple products to HS codes concurrently
        
        Args:
            requests: List of HS code match requests
            max_concurrent: Maximum number of concurrent API calls
            
        Returns:
            List[HSCodeMatchResult]: List of matching results
            
        Raises:
            ValueError: If batch size exceeds limits
        """
        if len(requests) > self.BATCH_SIZE_LIMIT:
            raise ValueError(f"Batch size {len(requests)} exceeds limit of {self.BATCH_SIZE_LIMIT}")
        
        logger.info(f"Starting batch matching for {len(requests)} products")
        
        # Create semaphore to limit concurrent requests
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def match_with_semaphore(request: HSCodeMatchRequest) -> HSCodeMatchResult:
            async with semaphore:
                return await self.match_single_product(
                    product_description=request.product_description,
                    country=request.country,
                    include_alternatives=request.include_alternatives,
                    confidence_threshold=request.confidence_threshold
                )
        
        # Execute all matches concurrently
        try:
            results = await asyncio.gather(
                *[match_with_semaphore(req) for req in requests],
                return_exceptions=True
            )
            
            # Process results and handle exceptions
            processed_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Failed to match product at index {i}: {str(result)}")
                    # Create error result
                    error_result = self._create_error_result(
                        requests[i].product_description,
                        str(result)
                    )
                    processed_results.append(error_result)
                else:
                    processed_results.append(result)
            
            logger.info(f"Completed batch matching: {len(processed_results)} results")
            return processed_results
            
        except Exception as e:
            logger.error(f"Batch matching failed: {str(e)}")
            raise
    
    async def _execute_with_retry(self, agent, query: str) -> HSCodeResult:
        """Execute agent query with retry logic and timeout"""
        last_exception = None
        
        for attempt in range(self.MAX_RETRY_ATTEMPTS):
            try:
                # Execute with timeout
                result = await asyncio.wait_for(
                    Runner.run(agent, query),
                    timeout=self.TIMEOUT_SECONDS
                )
                
                if result and hasattr(result, 'final_output'):
                    return result.final_output
                else:
                    raise ValueError("Invalid response format from OpenAI Agent")
                    
            except asyncio.TimeoutError as e:
                last_exception = e
                logger.warning(f"Timeout on attempt {attempt + 1}/{self.MAX_RETRY_ATTEMPTS}")
                if attempt < self.MAX_RETRY_ATTEMPTS - 1:
                    await asyncio.sleep(self.RETRY_DELAY_SECONDS * (attempt + 1))
                    
            except Exception as e:
                last_exception = e
                logger.warning(f"Error on attempt {attempt + 1}/{self.MAX_RETRY_ATTEMPTS}: {str(e)}")
                if attempt < self.MAX_RETRY_ATTEMPTS - 1:
                    await asyncio.sleep(self.RETRY_DELAY_SECONDS * (attempt + 1))
        
        # All retries failed
        if isinstance(last_exception, asyncio.TimeoutError):
            raise TimeoutError(f"HS code matching timed out after {self.MAX_RETRY_ATTEMPTS} attempts")
        else:
            raise ConnectionError(f"Failed to connect to OpenAI API: {str(last_exception)}")
    
    def _clean_product_description(self, description: str) -> str:
        """Clean and normalize product description for better matching"""
        # Remove extra whitespace and normalize
        cleaned = " ".join(description.strip().split())
        
        # Remove common noise words that don't help with classification
        noise_words = ["various", "assorted", "mixed", "different", "type", "kind"]
        words = cleaned.split()
        filtered_words = [word for word in words if word.lower() not in noise_words]
        
        return " ".join(filtered_words)
    
    def _build_search_query(self, description: str, include_alternatives: bool) -> str:
        """Build optimized search query for the agent"""
        base_query = f"Find the most appropriate HS code for this product: {description}"
        
        if include_alternatives:
            base_query += "\n\nAlso provide up to 3 alternative HS codes with confidence scores if there are other potentially suitable classifications."
        
        base_query += "\n\nProvide detailed reasoning for your classification decision."
        
        return base_query
    
    def _process_matching_result(
        self,
        primary_result: HSCodeResult,
        original_query: str,
        processing_time: float,
        confidence_threshold: float,
        include_alternatives: bool
    ) -> HSCodeMatchResult:
        """Process and validate the matching result from OpenAI Agent"""
        
        # Validate primary result confidence
        if primary_result.confidence < confidence_threshold:
            logger.warning(f"Primary match confidence {primary_result.confidence:.3f} "
                          f"below threshold {confidence_threshold}")
        
        # For now, we'll work with single result from structured output
        # Alternative matches would need to be handled differently with current SDK
        alternatives = []
        
        # Create result object
        result = HSCodeMatchResult(
            primary_match=primary_result,
            alternative_matches=alternatives,
            processing_time_ms=processing_time,
            query=original_query
        )
        
        return result
    
    def _create_error_result(self, product_description: str, error_message: str) -> HSCodeMatchResult:
        """Create an error result for failed matches"""
        error_result = HSCodeResult(
            hs_code="ERROR",
            code_description="Failed to match HS code",
            confidence=0.0,
            chapter="ERROR",
            section="ERROR",
            reasoning=f"Error occurred during matching: {error_message}"
        )
        
        return HSCodeMatchResult(
            primary_match=error_result,
            alternative_matches=[],
            processing_time_ms=0.0,
            query=product_description
        )
    
    def get_confidence_level_description(self, confidence: float) -> str:
        """Get human-readable confidence level description"""
        if confidence >= self.HIGH_CONFIDENCE_THRESHOLD:
            return "High"
        elif confidence >= self.MEDIUM_CONFIDENCE_THRESHOLD:
            return "Medium"
        elif confidence >= self.LOW_CONFIDENCE_THRESHOLD:
            return "Low"
        else:
            return "Very Low"
    
    def should_require_manual_review(self, confidence: float) -> bool:
        """Determine if match requires manual review based on confidence"""
        return confidence < self.MEDIUM_CONFIDENCE_THRESHOLD
    
    async def get_service_health(self) -> Dict[str, Any]:
        """Get service health status and configuration"""
        try:
            # Test connection with simple query
            test_agent = self._get_or_create_agent("default")
            start_time = time.time()
            
            await asyncio.wait_for(
                Runner.run(test_agent, "Test connection - find HS code for 'apple'"),
                timeout=10.0
            )
            
            response_time = (time.time() - start_time) * 1000
            
            return {
                "status": "healthy",
                "response_time_ms": round(response_time, 2),
                "available_countries": self.agent_config.get_available_countries(),
                "cache_size": len(self._agents_cache),
                "configuration": {
                    "max_retry_attempts": self.MAX_RETRY_ATTEMPTS,
                    "timeout_seconds": self.TIMEOUT_SECONDS,
                    "batch_size_limit": self.BATCH_SIZE_LIMIT,
                    "confidence_thresholds": {
                        "high": self.HIGH_CONFIDENCE_THRESHOLD,
                        "medium": self.MEDIUM_CONFIDENCE_THRESHOLD,
                        "low": self.LOW_CONFIDENCE_THRESHOLD
                    }
                }
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "available_countries": self.agent_config.get_available_countries(),
                "cache_size": len(self._agents_cache)
            }


# Create singleton instance
hs_matching_service = HSCodeMatchingService()