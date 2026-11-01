"""Observed retail barcodes, never a catalog identity or proof of ownership."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

BarcodeFormat = Literal['UPC_A', 'UPC_E', 'EAN_8', 'EAN_13']
LENGTHS = {'UPC_A': 12, 'UPC_E': 8, 'EAN_8': 8, 'EAN_13': 13}


class BarcodeReading(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    value: str = Field(min_length=8, max_length=13, pattern=r'^[0-9]+$')
    format: BarcodeFormat
    supplement: str | None = Field(default=None, pattern=r'^(?:[0-9]{2}|[0-9]{5})$')

    @model_validator(mode='after')
    def matching_length(self):
        if len(self.value) != LENGTHS[self.format]:
            raise ValueError('Barcode length does not match its format')
        return self


def barcode_variants(reading):
    """Only UPC-A and its zero-prefixed EAN-13 are equivalent."""
    values = {reading.value}
    if reading.format == 'UPC_A': values.add('0'+reading.value)
    if reading.format == 'EAN_13' and reading.value.startswith('0'): values.add(reading.value[1:])
    return values


# The same bounded shape is enforced for direct SQL writers. Unknown is {}, not
# a zero-filled identifier. Null supplements are omitted in persisted readings.
BARCODE_CHECK = """jsonb_typeof(barcode) = 'object' AND (barcode = '{}'::jsonb OR (
    barcode - 'value' - 'format' - 'supplement' = '{}'::jsonb
    AND barcode ?& ARRAY['value','format']
    AND jsonb_typeof(barcode->'value') = 'string'
    AND jsonb_typeof(barcode->'format') = 'string'
    AND barcode->>'value' ~ '^[0-9]+$'
    AND CASE barcode->>'format'
        WHEN 'UPC_A' THEN char_length(barcode->>'value') = 12
        WHEN 'UPC_E' THEN char_length(barcode->>'value') = 8
        WHEN 'EAN_8' THEN char_length(barcode->>'value') = 8
        WHEN 'EAN_13' THEN char_length(barcode->>'value') = 13
        ELSE false END
    AND (NOT barcode ? 'supplement' OR (
        jsonb_typeof(barcode->'supplement') = 'string'
        AND barcode->>'supplement' ~ '^([0-9]{2}|[0-9]{5})$'))))"""
