"""
OpenAI Agents SDK configuration for HS Code matching
"""
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field
from .config import settings
import logging
import asyncio

# OpenAI Agents SDK imports
from agents import Agent, FileSearchTool, Runner, set_default_openai_key
from agents.agent import StopAtTools


logger = logging.getLogger(__name__)

# Configure OpenAI API key for agents
if settings.OPENAI_API_KEY:
    set_default_openai_key(settings.OPENAI_API_KEY)


class HSCodeResult(BaseModel):
    """Structured output model for HS code matching results"""
    hs_code: str = Field(..., description="The primary 9-digit HS code identifier")
    code_description: str = Field(..., description="Official description of the HS code")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score between 0 and 1")
    chapter: str = Field(..., description="HS chapter classification")
    section: str = Field(..., description="HS section classification")
    reasoning: str = Field(..., description="Brief explanation for why this code matches")


class HSCodeMatchResult(BaseModel):
    """Complete HS code matching result with alternatives"""
    primary_match: HSCodeResult
    alternative_matches: List[HSCodeResult] = Field(default_factory=list, max_items=3)
    processing_time_ms: float = Field(..., description="Processing time in milliseconds")
    query: str = Field(..., description="Original product description query")


# Enhanced structured output models for HS code matching
class HSCodeAlternative(BaseModel):
    """Alternative HS code option with confidence score"""
    hs_code: str = Field(..., description="Alternative 9-digit HS code identifier")
    code_description: str = Field(..., description="Official description of the alternative HS code")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score for this alternative")
    reasoning: str = Field(..., description="Brief explanation for this alternative classification")


class OpenAIAgentConfig:
    """OpenAI Agents SDK configuration for HS Code matching"""
    
    # Vector Store Configuration
    @classmethod
    def get_vector_store_config(cls) -> Dict[str, List[str]]:
        """Get vector store configuration from settings"""
        return {
            # Country-specific HS code vector stores
            "turkmenistan": [settings.OPENAI_VECTOR_STORE_ID],
            "default": [settings.OPENAI_VECTOR_STORE_ID],  # Default fallback
        }
    
    # Agent Configuration
    AGENT_NAME = "HS Code Classification Expert"
    AGENT_INSTRUCTIONS = """You are an expert in Harmonized System (HS) code classification with deep knowledge of international trade regulations.

Your task is to analyze product descriptions and classify them with appropriate HS codes.

Instructions:
1. Use the FileSearchTool to find relevant HS code information from the vector store
2. Analyze the product description carefully considering:
   - Material composition and construction
   - Intended use and function
   - Manufacturing process
   - Industry classification standards
3. Provide the most appropriate primary HS code with high confidence
4. Include up to 3 alternative classifications if applicable
5. Always explain your reasoning clearly and concisely
6. Consider country-specific variations when applicable

Return your response in the exact JSON structure requested with:
- Primary HS code with confidence score and reasoning
- Alternative codes with their respective confidence scores
- Processing time and original query information

Prioritize accuracy over speed, and provide detailed reasoning for your classification decisions."""

    # FileSearchTool Configuration - Optimized for HS code retrieval
    MAX_SEARCH_RESULTS = 10  # More results for comprehensive HS code matching
    SEARCH_CONFIDENCE_THRESHOLD = 0.7
    
    # Model Configuration
    MODEL_NAME = "gpt-4.1"  # Use more capable model for complex HS code analysis
    MODEL_TEMPERATURE = 0.1  # Low temperature for consistent classifications
    
    @classmethod
    async def create_agent(cls, country: str = "default") -> Agent:
        """Create configured OpenAI Agent for HS code matching"""
        
        # Get vector store configuration
        vector_store_config = cls.get_vector_store_config()
        
        # Get vector store IDs for specified country
        vector_store_ids = vector_store_config.get(
            country.lower(), 
            vector_store_config["default"]
        )
        
        # Validate vector store IDs
        if not vector_store_ids or not any(vector_store_ids):
            logger.warning(f"No vector store configured for country: {country}")
            vector_store_ids = vector_store_config["default"]
        
        # Configure FileSearchTool with performance optimizations
        file_search_tool = FileSearchTool(
            max_num_results=cls.MAX_SEARCH_RESULTS,
            vector_store_ids=vector_store_ids,
        )
        
        # Import ModelSettings for proper configuration
        from agents import ModelSettings
        
        # Create and return configured agent with structured output
        agent = Agent(
            name=cls.AGENT_NAME,
            instructions=cls.AGENT_INSTRUCTIONS,
            model=cls.MODEL_NAME,
            tools=[file_search_tool],
            output_type=HSCodeMatchResult,  # Use enhanced structured output            
            model_settings=ModelSettings(
                temperature=cls.MODEL_TEMPERATURE,
                max_tokens=1500,  # Sufficient tokens for detailed analysis
                )
        )
        
        return agent
    
    @classmethod
    def get_available_countries(cls) -> List[str]:
        """Get list of available countries for HS code matching"""
        return list(cls.get_vector_store_config().keys())
    
    @classmethod
    async def match_hs_code(cls, product_description: str, country: str = "default") -> HSCodeMatchResult:
        """
        High-level method to match HS code for a product description
        
        Args:
            product_description: Product description to classify
            country: Country-specific classification context
            
        Returns:
            HSCodeMatchResult with primary and alternative matches
        """
        import time
        
        start_time = time.time()
        
        try:
            # Create agent for specific country
            agent = await cls.create_agent(country)
            
            # Prepare enhanced query with context
            enhanced_query = f"""Find the most appropriate HS code for this product: "{product_description}"
            
Also provide up to 3 alternative HS codes with confidence scores if there are other potentially suitable classifications.

Provide detailed reasoning for your classification decision."""
            
            # Run agent with the query using timeout and retry logic
            try:
                result = await asyncio.wait_for(
                    Runner.run(agent, enhanced_query),
                    timeout=30.0  # 30 second timeout
                )
                
                # Calculate processing time
                processing_time_ms = (time.time() - start_time) * 1000
                
                # Extract structured result
                if hasattr(result, 'final_output'):
                    final_output = result.final_output
                    
                    # Handle different output types
                    if isinstance(final_output, HSCodeMatchResult):
                        # Perfect case - structured output worked
                        final_output.processing_time_ms = processing_time_ms
                        final_output.query = product_description
                        logger.info(f"Structured output received: {final_output.primary_match.hs_code}")
                        return final_output
                    elif isinstance(final_output, HSCodeResult):
                        # Single result - wrap in match result
                        return HSCodeMatchResult(
                            primary_match=final_output,
                            alternative_matches=[],
                            processing_time_ms=processing_time_ms,
                            query=product_description
                        )
                    else:
                        # Try to parse text response
                        logger.warning(f"Unexpected output type: {type(final_output)}, attempting text parsing")
                        return cls._parse_text_response(str(final_output), product_description, processing_time_ms)
                else:
                    logger.warning("No final_output in agent result")
                    return cls._create_fallback_result(product_description, processing_time_ms)
                    
            except asyncio.TimeoutError:
                processing_time_ms = (time.time() - start_time) * 1000
                logger.error(f"Agent execution timed out after 30 seconds")
                return cls._create_error_result(product_description, processing_time_ms, "Request timed out")
            except Exception as agent_error:
                processing_time_ms = (time.time() - start_time) * 1000
                logger.error(f"Agent execution failed: {str(agent_error)}")
                return cls._create_error_result(product_description, processing_time_ms, f"Agent error: {str(agent_error)}")
                
        except Exception as e:
            processing_time_ms = (time.time() - start_time) * 1000
            logger.error(f"Error in HS code matching: {str(e)}")
            return cls._create_error_result(product_description, processing_time_ms, str(e))
    
    @classmethod
    def _create_fallback_result(cls, query: str, processing_time_ms: float) -> HSCodeMatchResult:
        """Create fallback result when agent response is unexpected"""
        return HSCodeMatchResult(
            primary_match=HSCodeResult(
                hs_code="999999999",
                code_description="General merchandise - classification pending",
                confidence=0.3,
                chapter="99",
                section="XXI",
                reasoning="Agent response format was unexpected, manual classification required"
            ),
            alternative_matches=[],
            processing_time_ms=processing_time_ms,
            query=query
        )
    
    @classmethod
    def _parse_text_response(cls, text_response: str, query: str, processing_time_ms: float) -> HSCodeMatchResult:
        """Parse text response when structured output fails"""
        import re
        
        try:
            # Try to extract HS code from text using regex
            hs_code_pattern = r'(\d{4}\.\d{2}\.\d{2})'
            hs_match = re.search(hs_code_pattern, text_response)
            
            if hs_match:
                hs_code = hs_match.group(1)
                
                # Extract confidence if mentioned
                confidence_pattern = r'confidence[:\s]*(\d+(?:\.\d+)?)'
                confidence_match = re.search(confidence_pattern, text_response.lower())
                confidence = float(confidence_match.group(1)) if confidence_match else 0.7
                
                # If confidence is > 1, assume it's a percentage
                if confidence > 1:
                    confidence = confidence / 100
                
                # Try to extract description
                description = f"Classification extracted from text response"
                if "description" in text_response.lower():
                    desc_pattern = r'description[:\s]*([^\.]+)'
                    desc_match = re.search(desc_pattern, text_response.lower())
                    if desc_match:
                        description = desc_match.group(1).strip()
                
                # Extract chapter from HS code
                chapter = hs_code[:2]
                
                return HSCodeMatchResult(
                    primary_match=HSCodeResult(
                        hs_code=hs_code,
                        code_description=description,
                        confidence=confidence,
                        chapter=chapter,
                        section="Unknown",
                        reasoning="Extracted from text response"
                    ),
                    alternative_matches=[],
                    processing_time_ms=processing_time_ms,
                    query=query
                )
            else:
                logger.warning("No HS code pattern found in text response")
                return cls._create_fallback_result(query, processing_time_ms)
                
        except Exception as parse_error:
            logger.error(f"Failed to parse text response: {str(parse_error)}")
            return cls._create_fallback_result(query, processing_time_ms)
    
    @classmethod
    def _create_error_result(cls, query: str, processing_time_ms: float, error_msg: str) -> HSCodeMatchResult:
        """Create error result when matching fails"""
        return HSCodeMatchResult(
            primary_match=HSCodeResult(
                hs_code="000000000",
                code_description="Error in classification process",
                confidence=0.0,
                chapter="00",
                section="ERROR",
                reasoning=f"Classification failed: {error_msg}"
            ),
            alternative_matches=[],
            processing_time_ms=processing_time_ms,
            query=query
        )


# Validate OpenAI API key is configured
if not settings.OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY must be configured for HS code matching")