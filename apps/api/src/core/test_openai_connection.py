"""
Test script for OpenAI Vector Store connection
"""
import asyncio
import time
import os
from typing import Optional
from agents import Runner
from .openai_config import OpenAIAgentConfig, HSCodeResult
from .config import settings

# Set OpenAI API key for agents
os.environ["OPENAI_API_KEY"] = settings.OPENAI_API_KEY


async def test_openai_connection(product_description: str = "Cotton fabric") -> Optional[HSCodeResult]:
    """Test connection to OpenAI Vector Store with sample query"""
    
    print(f"Testing OpenAI Vector Store connection...")
    print(f"Using API key: {settings.OPENAI_API_KEY[:10]}...")
    print(f"Product description: {product_description}")
    
    try:
        # Create agent
        agent = OpenAIAgentConfig.create_agent(country="turkmenistan")
        print(f"Agent created: {agent.name}")
        
        # Record start time
        start_time = time.time()
        
        # Execute query
        query = f"Find the most appropriate HS code for this product: {product_description}"
        print(f"Executing query: {query}")
        
        result = await Runner.run(agent, query)
        
        # Calculate processing time
        processing_time = (time.time() - start_time) * 1000
        print(f"Processing time: {processing_time:.2f}ms")
        
        # Parse result
        if result and result.final_output:
            hs_result = result.final_output
            print(f"✅ Connection successful!")
            print(f"Primary match: {hs_result.hs_code} - {hs_result.code_description}")
            print(f"Confidence: {hs_result.confidence}")
            print(f"Reasoning: {hs_result.reasoning}")
            return hs_result
        else:
            print("❌ No result returned from OpenAI Vector Store")
            return None
            
    except Exception as e:
        print(f"❌ Connection failed: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        return None


async def test_multiple_queries():
    """Test multiple product descriptions"""
    test_products = [
        "Cotton fabric",
        "Steel pipes",
        "Electronic components",
        "Agricultural machinery",
    ]
    
    print(f"\n=== Testing Multiple Queries ===")
    for i, product in enumerate(test_products, 1):
        print(f"\n--- Test {i}/{len(test_products)} ---")
        result = await test_openai_connection(product)
        if result:
            print(f"✅ Success: {result.hs_code}")
        else:
            print(f"❌ Failed")


if __name__ == "__main__":
    # Test single query
    result = asyncio.run(test_openai_connection())
    
    # Test multiple queries if first one succeeds
    if result:
        asyncio.run(test_multiple_queries())