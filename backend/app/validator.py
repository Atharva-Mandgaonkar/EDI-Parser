"""Validation functions for EDI data — NPI Luhn check, date logic, math verification."""

from datetime import datetime
from typing import Optional


def validate_npi(npi: str) -> Optional[dict]:
    """
    Validate a 10-digit NPI using the Luhn algorithm (mod 10 check).
    Prepends the standard '80840' prefix for the healthcare Luhn check.
    
    Returns an error dict if invalid, None if valid.
    """
    if not npi or not npi.strip():
        return None  # Empty NPI — skip
    
    npi = npi.strip()
    
    if not npi.isdigit():
        return {
            "field": "NPI",
            "message": f"Error: NPI '{npi}' contains non-numeric characters. NPIs must be exactly 10 digits.",
            "suggested_fix": {"value": npi.replace(" ", "").replace("-", "")} 
                if npi.replace(" ", "").replace("-", "").isdigit() else None,
        }
    
    if len(npi) != 10:
        return {
            "field": "NPI",
            "message": f"Error: NPI '{npi}' is {len(npi)} digits. NPIs must be exactly 10 digits.",
            "suggested_fix": None,
        }
    
    # Luhn check with '80840' prefix
    full = "80840" + npi
    digits = [int(d) for d in full]
    
    # Double every other digit from right (starting at second-to-last)
    total = 0
    for i, d in enumerate(reversed(digits)):
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    
    if total % 10 != 0:
        return {
            "field": "NPI",
            "message": f"Error: NPI '{npi}' failed Luhn checksum validation. The check digit is incorrect.",
            "suggested_fix": None,
        }
    
    return None


def validate_dates(date_of_birth: str, claim_date: str) -> Optional[dict]:
    """
    Validate that Date of Birth is chronologically before the Claim/Service Date.
    Dates expected in CCYYMMDD format (e.g., 19850115).
    
    Returns an error dict if invalid, None if valid.
    """
    if not date_of_birth or not claim_date:
        return None
    
    date_of_birth = date_of_birth.strip()
    claim_date = claim_date.strip()
    
    try:
        dob = datetime.strptime(date_of_birth, "%Y%m%d")
    except ValueError:
        return {
            "field": "Date of Birth",
            "message": f"Error: Date of Birth '{date_of_birth}' is not a valid date in CCYYMMDD format.",
            "suggested_fix": None,
        }
    
    try:
        cd = datetime.strptime(claim_date, "%Y%m%d")
    except ValueError:
        return {
            "field": "Claim Date",
            "message": f"Error: Claim Date '{claim_date}' is not a valid date in CCYYMMDD format.",
            "suggested_fix": None,
        }
    
    if dob >= cd:
        return {
            "field": "Date Logic",
            "message": f"Error: Patient Date of Birth ({dob.strftime('%m/%d/%Y')}) is not before the Claim Date ({cd.strftime('%m/%d/%Y')}). The patient's DOB must precede the service date.",
            "suggested_fix": None,
        }
    
    return None


def validate_date_format(date_str: str, field_name: str = "Date") -> Optional[dict]:
    """Validate that a date string is in valid CCYYMMDD format."""
    if not date_str or not date_str.strip():
        return None
    
    date_str = date_str.strip()
    
    if len(date_str) != 8 or not date_str.isdigit():
        return {
            "field": field_name,
            "message": f"Error: {field_name} '{date_str}' is not in valid CCYYMMDD format (expected 8 digits).",
            "suggested_fix": None,
        }
    
    try:
        datetime.strptime(date_str, "%Y%m%d")
    except ValueError:
        return {
            "field": field_name,
            "message": f"Error: {field_name} '{date_str}' is not a valid calendar date.",
            "suggested_fix": None,
        }
    
    return None


def validate_totals(total_charge: float, line_items: list) -> Optional[dict]:
    """
    Validate that the total charge equals the sum of line item charges.
    
    Returns an error dict if amounts don't match, None if valid.
    """
    if total_charge is None or not line_items:
        return None
    
    try:
        item_sum = sum(float(x) for x in line_items if x)
    except (ValueError, TypeError):
        return {
            "field": "Charge Total",
            "message": "Error: Could not calculate sum of line item charges due to non-numeric values.",
            "suggested_fix": None,
        }
    
    # Allow small floating-point tolerance
    if abs(total_charge - item_sum) > 0.01:
        return {
            "field": "Charge Total",
            "message": f"Error: Total charge (${total_charge:.2f}) does not equal the sum of line items (${item_sum:.2f}). Difference: ${abs(total_charge - item_sum):.2f}.",
            "suggested_fix": {"value": str(item_sum)},
        }
    
    return None


import re

def validate_structure(segment_id: str, elements: dict, schema_def: dict) -> list:
    """Validate segment against schema metadata (required, length, patterns)."""
    errors = []
    
    # 1. Mandatory Field Check
    for pos, meta in schema_def.get("elements", {}).items():
        if isinstance(meta, dict) and meta.get("required"):
            field_name = meta["name"]
            value = elements.get(field_name) or elements.get(f"{segment_id}{pos}")
            
            if not value or not str(value).strip():
                errors.append({
                    "field": field_name,
                    "message": f"Critical Error: Missing mandatory HIPAA field '{field_name}' ({segment_id}{pos}).",
                    "suggested_fix": None
                })
                continue
            
            # 2. Length Checks
            val_str = str(value).strip()
            fixed_len = meta.get("len")
            min_len = meta.get("min_len")
            max_len = meta.get("max_len")
            
            if fixed_len and len(val_str) != fixed_len:
                errors.append({
                    "field": field_name,
                    "message": f"Error: '{field_name}' must be exactly {fixed_len} characters (found {len(val_str)}).",
                    "suggested_fix": None
                })
            elif min_len and len(val_str) < min_len:
                errors.append({
                    "field": field_name,
                    "message": f"Error: '{field_name}' is too short (min {min_len} chars).",
                    "suggested_fix": None
                })
            elif max_len and len(val_str) > max_len:
                errors.append({
                    "field": field_name,
                    "message": f"Error: '{field_name}' is too long (max {max_len} chars).",
                    "suggested_fix": None
                })
                
            # 3. Pattern Checks (Regex)
            pattern = meta.get("pattern")
            if pattern and not re.match(pattern, val_str):
                errors.append({
                    "field": field_name,
                    "message": f"Error: '{field_name}' value '{val_str}' does not match required HIPAA format.",
                    "suggested_fix": None
                })
                
    return errors


def validate_segment(segment_id: str, elements: dict, schema: dict, context: dict = None) -> list:
    """
    Run all applicable validators on a segment and return a list of error objects.
    """
    errors = []
    context = context or {}
    
    # Get segment definition from schema
    segment_def = schema.get("segments", {}).get(segment_id, {})
    
    # 1. Structural Validation (based on new schema metadata)
    struct_errors = validate_structure(segment_id, elements, segment_def)
    errors.extend(struct_errors)
    
    # 2. Code Set Validation (Check against available qualifiers)
    # This logic checks if a qualifier value exists in the schema's lookup table
    for pos, meta in segment_def.get("elements", {}).items():
        if isinstance(meta, dict) and "qualifier_codes" in segment_def:
            field_name = meta["name"]
            if "Qualifier" in field_name:
                val = elements.get(field_name)
                allowed = segment_def["qualifier_codes"]
                if val and val not in allowed:
                    errors.append({
                        "field": field_name,
                        "message": f"Error: Value '{val}' is not a valid standard HIPAA qualifier for {field_name}.",
                        "suggested_fix": None
                    })

    # 3. NPI validation
    if segment_id == "NM1":
        npi_value = elements.get("Identification Code") or elements.get("NM109")
        id_code_qualifier = elements.get("Identification Code Qualifier") or elements.get("NM108")
        
        if id_code_qualifier == "XX" and npi_value:
            err = validate_npi(npi_value)
            if err:
                errors.append(err)
    
    # 4. Date validation (DTP segment)
    if segment_id == "DTP":
        date_value = elements.get("Date Time Period") or elements.get("DTP03")
        qualifier = elements.get("Date/Time Qualifier") or elements.get("DTP01")
        
        if date_value:
            err = validate_date_format(date_value, f"Date (qualifier {qualifier})")
            if err:
                errors.append(err)
            
            # If we have DOB in context, compare
            if qualifier in ("472", "232"):  # Service Date
                dob = context.get("patient_dob")
                if dob:
                    err = validate_dates(dob, date_value)
                    if err:
                        errors.append(err)
    
    # 5. Claim total validation (CLM segment)
    if segment_id == "CLM":
        total = elements.get("Total Claim Charge Amount") or elements.get("CLM02")
        line_charges = context.get("line_charges", [])
        
        if total and line_charges:
            try:
                err = validate_totals(float(total), line_charges)
                if err:
                    errors.append(err)
            except ValueError:
                errors.append({
                    "field": "Total Claim Charge Amount",
                    "message": f"Error: Total charge '{total}' is not a valid number.",
                    "suggested_fix": None,
                })
    
    return errors
