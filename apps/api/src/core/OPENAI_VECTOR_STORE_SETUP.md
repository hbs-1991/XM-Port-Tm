# OpenAI Vector Store Setup and Management

## Overview

This document describes the setup and management procedures for OpenAI Vector Store integration used for HS Code matching in the XM-Port system.

## Architecture

The system uses OpenAI Agents SDK with FileSearchTool to access external vector stores containing HS code data. This approach eliminates the need for local vector database management.

### Key Components

- **OpenAI Agents SDK**: Production-ready AI agent orchestration
- **FileSearchTool**: Built-in vector store integration for semantic search
- **OpenAI Vector Store**: External managed vector storage (no local database required)
- **Pydantic Models**: Structured output validation and type safety

## Configuration

### Environment Variables

Required environment variables in `.env`:

```bash
# OpenAI Configuration
OPENAI_API_KEY=sk-proj-xxxxx
OPENAI_VECTOR_STORE_ID=vs_xxxxx
OPENAI_HSCODE_DATA_FILE_ID=file-xxxxx (optional)
```

### Configuration Files

**Location**: `src/core/openai_config.py`

Key configuration options:
- `MAX_SEARCH_RESULTS`: Maximum number of search results (default: 5)
- `SEARCH_CONFIDENCE_THRESHOLD`: Minimum confidence threshold (default: 0.7)
- Vector store mapping for different countries

## Vector Store Setup

### Initial Setup

1. **Create Vector Store** (via OpenAI Console or API):
   ```python
   # This is handled externally via OpenAI Console
   # Vector Store ID: vs_686e551be03481919dd944bf5d93af95
   ```

2. **Upload HS Code Data** (via OpenAI Console):
   - Upload structured HS code dataset
   - Ensure proper formatting with code, description, chapter, section
   - File ID: file-Q9m84v6MYDr1tPMEuV5Quj

3. **Configure Environment**:
   - Set `OPENAI_VECTOR_STORE_ID` to the vector store ID
   - Set `OPENAI_HSCODE_DATA_FILE_ID` to the uploaded file ID

### Data Format Requirements

The vector store expects HS code data in the following format:

```json
{
  "code": "520100000",
  "description": "Cotton, not carded or combed",
  "chapter": "52",
  "section": "XI",
  "country": "turkmenistan"
}
```

## Agent Configuration

### Structured Output Models

**HSCodeResult**: Single HS code match result
```python
class HSCodeResult(BaseModel):
    hs_code: str
    code_description: str
    confidence: float  # 0.0 to 1.0
    chapter: str
    section: str
    reasoning: str
```

**HSCodeMatchResult**: Complete matching result with alternatives
```python
class HSCodeMatchResult(BaseModel):
    primary_match: HSCodeResult
    alternative_matches: List[HSCodeResult]  # max 3
    processing_time_ms: float
    query: str
```

### Agent Instructions

The agent is configured with specialized instructions for HS code classification:
- Expert knowledge in Harmonized System classification
- International trade regulations understanding
- Confidence scoring based on match quality
- Clear reasoning for classification decisions
- Alternative suggestions for ambiguous cases

## Testing and Validation

### Connection Test

Run the connection test:
```bash
cd apps/api
python -m src.core.test_openai_connection
```

Expected output:
- ✅ Connection successful
- Valid HS code matches with confidence scores
- Reasonable processing times (<20 seconds for first query, <10 seconds for subsequent)

### Test Results

Recent test results show:
- Cotton fabric → 5208 (confidence: 0.95, 16s first query, 5s subsequent)
- Steel pipes → 730490000 (confidence: 0.95, 8s)
- Electronic components → 853690850 (confidence: 0.85, 9s)
- Agricultural machinery → 8433.90 (confidence: 0.9, 9s)

## Performance Characteristics

### Response Times
- First query: ~15-20 seconds (cold start)
- Subsequent queries: ~5-10 seconds
- Target: <2 seconds (achievable with optimization)

### Confidence Scores
- High confidence (0.9+): Exact or very close match
- Medium confidence (0.7-0.9): Good match with minor ambiguity
- Low confidence (<0.7): Requires manual review

## Troubleshooting

### Common Issues

1. **API Key Error**
   - Verify `OPENAI_API_KEY` is set correctly
   - Check API key has access to Agents SDK

2. **Vector Store Access Error**
   - Verify `OPENAI_VECTOR_STORE_ID` is correct
   - Ensure vector store contains HS code data

3. **Slow Performance**
   - First query is always slower (cold start)
   - Consider implementing caching layer

4. **Low Confidence Scores**
   - Review product description quality
   - Check if HS codes exist in vector store
   - Consider expanding vector store data

### Error Handling

The system implements comprehensive error handling:
- OpenAI API failures with retry logic
- Network timeouts and connection errors
- Invalid input validation
- Structured error responses

## Security Considerations

### API Key Security
- Store API keys in environment variables only
- Never expose API keys in logs or responses
- Use separate keys for development and production

### Rate Limiting
- OpenAI API limits: 5,000 RPM, 160,000 TPM
- Implement application-level rate limiting
- Monitor usage to prevent quota exhaustion

### Input Validation
- Sanitize all product descriptions
- Validate input length and content
- Prevent injection attacks

## Maintenance

### Regular Tasks

1. **Monitor Performance**
   - Track response times and accuracy
   - Monitor API usage and costs
   - Review confidence score distributions

2. **Update Vector Store**
   - Add new HS codes as needed
   - Update descriptions for clarity
   - Maintain country-specific variations

3. **Review Results**
   - Analyze low-confidence matches
   - Update agent instructions based on patterns
   - Optimize search parameters

### Backup and Recovery

- Vector store data is managed by OpenAI
- Maintain backup of source HS code data
- Document vector store recreation procedures
- Test disaster recovery scenarios

## Cost Management

### Current Costs
- Vector storage: Based on file size and retention
- Search operations: Per query pricing
- Agent processing: Based on token usage

### Optimization Strategies
- Implement intelligent caching
- Batch processing for multiple queries
- Optimize product description preprocessing
- Monitor and adjust search parameters