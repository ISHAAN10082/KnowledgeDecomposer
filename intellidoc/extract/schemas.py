from pydantic import BaseModel, validator, Field
from typing import List, Optional
from decimal import Decimal, InvalidOperation

class LineItem(BaseModel):
    description: str = Field(..., description="The description of the line item.")
    quantity: float = Field(..., description="The quantity of the line item.")
    unit_price: Decimal = Field(..., description="The unit price of the line item.")
    total: Decimal = Field(..., description="The total price for the line item.")

    @validator('total')
    def validate_line_total(cls, v, values):
        """Validates that quantity * unit_price is close to the total."""
        if 'quantity' in values and 'unit_price' in values:
            try:
                quantity = float(values['quantity'])
                unit_price = Decimal(values['unit_price'])
                expected_total = Decimal(quantity) * unit_price
                if not isinstance(v, Decimal):
                    v = Decimal(v)
                # Allow for small rounding differences
                if abs(v - expected_total) > 0.02: # Increased tolerance
                    raise ValueError(f'Line item total {v} does not match quantity * unit_price {expected_total}')
            except (InvalidOperation, TypeError):
                raise ValueError("Invalid type for quantity or unit_price")
        return v

class Invoice(BaseModel):
    vendor_name: str = Field(..., description="The name of the vendor or company issuing the invoice.")
    invoice_number: Optional[str] = Field(None, description="The unique identifier for the invoice.")
    line_items: List[LineItem] = Field(..., description="A list of all line items on the invoice.")
    total_amount: Decimal = Field(..., description="The final total amount of the invoice.")

    @validator('total_amount')
    def validate_total_amount(cls, v, values):
        """Validates that the sum of line item totals matches the invoice total."""
        if 'line_items' in values and values['line_items']:
            try:
                calculated_total = sum(item.total for item in values['line_items'])
                if not isinstance(v, Decimal):
                    v = Decimal(v)
                # Allow for small rounding differences, common with taxes
                if abs(v - calculated_total) > 0.02: # Increased tolerance
                    raise ValueError(f'Total amount {v} does not match the sum of line items {calculated_total}')
            except (InvalidOperation, TypeError):
                raise ValueError("Invalid data in line_items for calculation")
        return v 