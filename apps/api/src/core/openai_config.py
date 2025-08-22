"""
OpenAI Agents SDK configuration for HS Code matching
"""
from typing import Dict, List
from agents import Agent, FileSearchTool
from pydantic import BaseModel, Field
from .config import settings


class HSCodeResult(BaseModel):
    """Structured output model for HS code matching results"""
    hs_code: str = Field(..., description="The primary HS code identifier")
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

Your role is to:
1. Analyze product descriptions and match them to the most appropriate HS codes
2. Provide confidence scores based on how well the product matches the HS code criteria
3. Explain your reasoning clearly and concisely
4. Suggest alternative HS codes when there's ambiguity
5. Consider the specific country's HS code variations when applicable

Always prioritize accuracy over speed, and provide detailed reasoning for your classification decisions."""

    # FileSearchTool Configuration  
    MAX_SEARCH_RESULTS = 3
    SEARCH_CONFIDENCE_THRESHOLD = 0.7
    
    @classmethod
    def create_agent(cls, country: str = "default") -> Agent:
        """Create configured OpenAI Agent for HS code matching"""
        
        # Get vector store configuration
        vector_store_config = cls.get_vector_store_config()
        
        # Get vector store IDs for specified country
        vector_store_ids = vector_store_config.get(
            country.lower(), 
            vector_store_config["default"]
        )
        
        # Configure FileSearchTool
        file_search_tool = FileSearchTool(
            max_num_results=cls.MAX_SEARCH_RESULTS,
            vector_store_ids=vector_store_ids,
        )
        
        # Create and return configured agent
        agent = Agent(
            name=cls.AGENT_NAME,
            instructions=cls.AGENT_INSTRUCTIONS,
            tools=[file_search_tool],
            output_type=HSCodeResult,  # Structured output
        )
        
        return agent
    
    @classmethod
    def get_available_countries(cls) -> List[str]:
        """Get list of available countries for HS code matching"""
        return list(cls.get_vector_store_config().keys())


# Validate OpenAI API key is configured
if not settings.OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY must be configured for HS code matching")