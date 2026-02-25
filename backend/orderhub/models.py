"""OrderHub Pydantic Models."""
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from datetime import datetime, timezone
import uuid


class OrderConsolidated(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    order_date: str
    sku: str
    master_sku: str = "UNMAPPED"
    style_code: str = ""
    color_code: str = ""
    size_code: str = ""
    qty: int = 1
    amount: float = 0.0
    state: str = ""
    platform: str
    account: str = ""
    file_id: str = ""
    user_id: str = ""
    row_hash: str = ""
    created_at: str = ""


class MasterSKU(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    sku: str
    master_sku: str
    product_name: Optional[str] = None
    category: Optional[str] = None
    created_at: str = ""


class UnmappedSKU(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    sku: str
    platform: str
    first_seen_at: str = ""
    last_seen_at: str = ""
    total_qty: int = 0
    total_revenue: float = 0.0
    file_name: str = ""
    status: str = "UNMAPPED"
    mapped_master_sku: Optional[str] = None
    suggested_master_sku: Optional[str] = None
    suggestion_confidence: Optional[float] = None


class UploadedFile(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    filename: str
    original_filename: str
    platform: str
    account: Optional[str] = None
    status: str = "pending"
    rows_processed: int = 0
    rows_inserted: int = 0
    duplicates_skipped: int = 0
    errors: List[str] = []
    created_at: str = ""
    completed_at: Optional[str] = None


DEFAULT_PLATFORMS = [
    {"name": "Meesho", "code": "meesho"},
    {"name": "Amazon", "code": "amazon"},
    {"name": "Flipkart", "code": "flipkart"},
    {"name": "Myntra", "code": "myntra"},
    {"name": "Ajio", "code": "ajio"},
    {"name": "Amazon Flex", "code": "amazon_flex"},
    {"name": "Base Orders", "code": "base"}
]
