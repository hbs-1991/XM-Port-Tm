from pydantic import BaseModel

class HSCodeMatchingOutputFormat(BaseModel):
    product_description: str
    matched_hs_code: str
    confidence_score: float
    code_description: str
    chapter: str
    section: str
    processing_time_ms: float
    quantity: float
    unit_of_measure: str
    origin_country: str