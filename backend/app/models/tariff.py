from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Union, Any
from datetime import date

class TariffHeader(BaseModel):
    """Model representing the header information of a CP Tariff document."""
    item_number: str = Field(..., description="Tariff item number")
    revision: str = Field(..., description="Revision number")
    issue_date: str = Field(..., description="Date the tariff was issued")
    effective_date: str = Field(..., description="Date the tariff becomes effective")
    expiration_date: str = Field(..., description="Date the tariff expires")
    cprs_number: Optional[str] = Field(None, description="CPRS reference number")
    change_description: Optional[str] = Field(None, description="Description of changes in this revision")

class CommodityInfo(BaseModel):
    """Model representing the commodity information."""
    commodity_name: str = Field(..., description="Name of the commodity")
    stcc_code: str = Field(..., description="Standard Transportation Commodity Code")

class RouteInfo(BaseModel):
    """Model representing route information."""
    route_code: str = Field(..., description="Route code")
    route_description: str = Field(..., description="Description of the route")

class RateInfo(BaseModel):
    """Model representing rate information for a specific origin-destination pair."""
    origin: str = Field(..., description="Origin location")
    destination: str = Field(..., description="Destination location")
    rate_values: Dict[str, Union[str, float]] = Field(..., description="Rate values for different equipment types")
    route: str = Field(..., description="Route code")
    additional_provisions: Optional[str] = Field(None, description="Additional provisions or notes")

class TariffNotes(BaseModel):
    """Model representing additional notes and information."""
    equipment_notes: Optional[List[str]] = Field(None, description="Notes about equipment")
    routing_notes: Optional[List[str]] = Field(None, description="Notes about routing")
    rate_notes: Optional[List[str]] = Field(None, description="Notes about rates")
    provision_notes: Optional[List[str]] = Field(None, description="Notes about provisions")
    general_notes: Optional[List[str]] = Field(None, description="General notes")

class ExtractedTableData(BaseModel):
    """Model representing the extracted table data."""
    headers: List[str] = Field(..., description="Table headers")
    rows: List[Dict[str, Any]] = Field(..., description="Table rows")
    raw_data: List[List[str]] = Field(..., description="Raw table data as a 2D array")

class TariffDocument(BaseModel):
    """Model representing the complete tariff document information."""
    header: TariffHeader = Field(..., description="Tariff header information")
    commodities: List[CommodityInfo] = Field(..., description="List of commodities covered")
    origin_info: Optional[str] = Field(None, description="Origin information")
    destination_info: Optional[str] = Field(None, description="Destination information")
    currency: str = Field(..., description="Currency used for rates (USD or CAD)")
    table_data: ExtractedTableData = Field(..., description="Extracted table data")
    notes: TariffNotes = Field(..., description="Additional notes and information")
    raw_text: str = Field(..., description="Raw OCR text")