"""
EDI Parser — Shreds raw EDI text and maps segments to human-readable names using HIPAA schemas.
"""

import json
import os
from pathlib import Path
from .sniffer import detect_delimiters
from .validator import validate_segment


# Cache loaded schemas
_schemas = {}
SCHEMA_DIR = Path(__file__).parent.parent / "schemas"


def load_schema(edi_type: str) -> dict:
    """Load and cache HIPAA schema for a given EDI type."""
    if edi_type in _schemas:
        return _schemas[edi_type]
    
    schema_path = SCHEMA_DIR / f"schema_{edi_type}.json"
    if not schema_path.exists():
        return {}
    
    with open(schema_path, "r", encoding="utf-8") as f:
        schema = json.load(f)
    
    _schemas[edi_type] = schema
    return schema


def shred(raw: str, segment_terminator: str = "~", element_separator: str = "*") -> list:
    """
    Split raw EDI text into a list of segments.
    Each segment is a list of elements (strings).
    
    Example:
        "NM1*85*1*DOE*JOHN~" -> [["NM1", "85", "1", "DOE", "JOHN"]]
    """
    segments = []
    lines = raw.split(segment_terminator)
    
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        elements = stripped.split(element_separator)
        if elements and elements[0]:
            segments.append(elements)
    
    return segments


def map_segment(segment_id: str, elements: list, schema: dict) -> dict:
    """
    Map a single segment's raw elements to a dictionary with human-readable names.
    
    Args:
        segment_id: e.g., "NM1"
        elements: list of element values (excluding the segment ID)
        schema: loaded HIPAA schema dict
    
    Returns:
        Dict mapping English names to values
    """
    segment_def = schema.get("segments", {}).get(segment_id, {})
    element_defs = segment_def.get("elements", {})
    
    result = {}
    
    for i, value in enumerate(elements):
        pos = str(i + 1).zfill(2)
        field_def = element_defs.get(pos, f"{segment_id}{pos}")
        
        # Handle new dictionary-style field definitions
        if isinstance(field_def, dict):
            field_name = field_def.get("name", f"{segment_id}{pos}")
        else:
            field_name = field_def
        
        if value:  # Only include non-empty elements
            # Parse composite sub-elements (separated by ':')
            if ':' in value:
                result[field_name] = parse_composite(value, segment_id, pos)
            else:
                result[field_name] = value
    
    return result


def parse_composite(value: str, segment_id: str, position: str) -> dict:
    """
    Parse composite sub-elements separated by ':'.
    E.g., 'HC:99213' -> {"Code Qualifier": "HC", "Procedure Code": "99213"}
    E.g., 'ABK:J06.9' -> {"Code List Qualifier": "ABK", "Diagnosis Code": "J06.9"}
    """
    parts = value.split(':')
    
    # Known composite field mappings
    composite_maps = {
        # SV1/SV2/SV3/SVC element 01 — Procedure Identifier
        ("SV1", "01"): ["Code Qualifier", "Procedure Code", "Modifier 1", "Modifier 2", "Modifier 3", "Modifier 4", "Description", "Product/Service ID"],
        ("SV2", "02"): ["Code Qualifier", "Procedure Code", "Modifier 1", "Modifier 2", "Modifier 3", "Modifier 4"],
        ("SV3", "01"): ["Code Qualifier", "Procedure Code", "Modifier 1", "Modifier 2", "Modifier 3", "Modifier 4"],
        ("SVC", "01"): ["Code Qualifier", "Procedure Code", "Modifier 1", "Modifier 2", "Modifier 3", "Modifier 4"],
        ("SVC", "06"): ["Code Qualifier", "Procedure Code", "Modifier 1", "Modifier 2", "Modifier 3", "Modifier 4"],
        # HI — Diagnosis Code
        ("HI", "01"): ["Code List Qualifier", "Diagnosis Code"],
        ("HI", "02"): ["Code List Qualifier", "Diagnosis Code"],
        ("HI", "03"): ["Code List Qualifier", "Diagnosis Code"],
        ("HI", "04"): ["Code List Qualifier", "Diagnosis Code"],
        ("HI", "05"): ["Code List Qualifier", "Diagnosis Code"],
        ("HI", "06"): ["Code List Qualifier", "Diagnosis Code"],
        ("HI", "07"): ["Code List Qualifier", "Diagnosis Code"],
        ("HI", "08"): ["Code List Qualifier", "Diagnosis Code"],
        ("HI", "09"): ["Code List Qualifier", "Diagnosis Code"],
        ("HI", "10"): ["Code List Qualifier", "Diagnosis Code"],
        ("HI", "11"): ["Code List Qualifier", "Diagnosis Code"],
        ("HI", "12"): ["Code List Qualifier", "Diagnosis Code"],
        # CLM element 05 — Health Care Service Location
        ("CLM", "05"): ["Place of Service Code", "Facility Code Qualifier", "Claim Frequency Code"],
        # SVD element 03 — Procedure Identifier
        ("SVD", "03"): ["Code Qualifier", "Procedure Code", "Modifier 1", "Modifier 2", "Modifier 3", "Modifier 4"],
    }
    
    key = (segment_id, position)
    if key in composite_maps:
        labels = composite_maps[key]
        result = {}
        for i, part in enumerate(parts):
            if part and i < len(labels):
                result[labels[i]] = part
        return result
    
    # Fallback: return as raw string if no mapping found
    return value


def build_structured_data(segments: list, schema: dict, edi_type: str) -> dict:
    """
    Build a nested, structured dictionary from parsed segments.
    Groups segments into logical sections based on the EDI hierarchy.
    
    Returns:
        {
            "parsed": { ... nested data ... },
            "stats": { "edi_type": ..., "total_segments": ..., "error_count": ..., "valid_count": ... }
        }
    """
    result = {}
    errors_total = 0
    validation_context = {}
    
    # Tracking state for hierarchical grouping
    current_section = "Interchange"
    current_claim = None
    current_provider = None
    current_subscriber = None
    claim_counter = 0
    service_counter = 0
    line_charges = []
    
    # Entity code lookup for NM1
    entity_names = schema.get("segments", {}).get("NM1", {}).get("entity_codes", {})
    
    for seg in segments:
        seg_id = seg[0].upper().strip()
        elements = seg[1:] if len(seg) > 1 else []
        
        # Map elements to human-readable names
        mapped = map_segment(seg_id, elements, schema)
        
        # 1. Structural/HIPAA Validation (Generic for ALL segments)
        segment_errors = validate_segment(seg_id, mapped, schema, validation_context)
        if segment_errors:
            if "_errors" not in mapped:
                mapped["_errors"] = []
            mapped["_errors"].extend(segment_errors)
            errors_total += len(segment_errors)

        # 2. Build section hierarchy
        if seg_id == "ISA":

            result["Interchange Header"] = mapped
            current_section = "Interchange"
            
        elif seg_id == "GS":
            result["Functional Group Header"] = mapped
            current_section = "Functional Group"
            
        elif seg_id == "ST":
            result["Transaction Set Header"] = mapped
            current_section = "Transaction"
            
        elif seg_id in ("BHT", "BGN"):
            seg_name = schema.get("segments", {}).get(seg_id, {}).get("name", seg_id)
            result[seg_name] = mapped
            
        elif seg_id == "HL":
            level_code = elements[2] if len(elements) > 2 else ""
            if level_code == "20":
                current_section = "Billing Provider"
                current_provider = {}
                result.setdefault("Billing Provider", {})
            elif level_code == "22":
                current_section = "Subscriber"
                current_subscriber = {}
                claim_counter = 0
                result.setdefault("Subscribers", [])
            elif level_code == "23":
                current_section = "Patient"
                
        elif seg_id == "NM1":
            entity_code = elements[0] if elements else ""
            entity_name = entity_names.get(entity_code, f"Entity {entity_code}")
            section_name = f"{entity_name} Name"
            
            # Check for NPI in context
            nm1_data = mapped.copy()
            
            if current_section == "Billing Provider":
                result.setdefault("Billing Provider", {})[section_name] = nm1_data
            elif current_section in ("Subscriber", "Patient"):
                if current_subscriber is not None:
                    current_subscriber[section_name] = nm1_data
            else:
                result[section_name] = nm1_data
                
        elif seg_id == "N3":
            addr_data = mapped
            if current_section == "Billing Provider":
                result.setdefault("Billing Provider", {})["Address"] = addr_data
            elif current_subscriber is not None:
                current_subscriber["Address"] = addr_data
            else:
                result["Address"] = addr_data
                
        elif seg_id == "N4":
            city_data = mapped
            if current_section == "Billing Provider":
                result.setdefault("Billing Provider", {})["City/State/ZIP"] = city_data
            elif current_subscriber is not None:
                current_subscriber["City/State/ZIP"] = city_data
            else:
                result["City/State/ZIP"] = city_data
                
        elif seg_id == "DMG":
            dmg_data = mapped.copy()
            # Extract DOB for validation context
            dob = elements[1] if len(elements) > 1 else None
            if dob:
                validation_context["patient_dob"] = dob
            
            if current_subscriber is not None:
                current_subscriber["Demographics"] = dmg_data
            else:
                result["Demographics"] = dmg_data
                
        elif seg_id == "SBR":
            sbr_data = mapped.copy()
            if current_subscriber is not None:
                current_subscriber["Subscriber Information"] = sbr_data
            else:
                result["Subscriber Information"] = sbr_data
                
        elif seg_id == "CLM":
            claim_counter += 1
            service_counter = 0
            line_charges = []
            clm_data = mapped.copy()
            
            current_claim = {
                "Claim Information": clm_data,
                "Services": []
            }
            
            if current_subscriber is not None:
                current_subscriber.setdefault("Claims", []).append(current_claim)
            else:
                result.setdefault("Claims", []).append(current_claim)
                
        elif seg_id == "DTP":
            dtp_data = mapped.copy()
            qualifier_codes = schema.get("segments", {}).get("DTP", {}).get("qualifier_codes", {})
            qualifier = elements[0] if elements else ""
            qualifier_name = qualifier_codes.get(qualifier, f"Date Qualifier {qualifier}")
            
            date_entry = {qualifier_name: dtp_data}
            
            if current_claim is not None:
                current_claim.setdefault("Dates", {}).update(date_entry)
            elif current_subscriber is not None:
                current_subscriber.setdefault("Dates", {}).update(date_entry)
            else:
                result.setdefault("Dates", {}).update(date_entry)
                
        elif seg_id == "HI":
            hi_data = mapped
            if current_claim is not None:
                current_claim["Diagnosis Codes"] = hi_data
            else:
                result["Diagnosis Codes"] = hi_data
                
        elif seg_id == "SV1":
            service_counter += 1
            svc_data = mapped.copy()
            
            # Track line charges for CLM total validation
            charge = elements[1] if len(elements) > 1 else None
            if charge:
                line_charges.append(charge)
            
            if current_claim is not None:
                current_claim["Services"].append({f"Service Line {service_counter}": svc_data})

        elif seg_id in ("SV2", "SV3"):
            service_counter += 1
            svc_data = mapped.copy()
            seg_name = schema.get("segments", {}).get(seg_id, {}).get("name", seg_id)
            if current_claim is not None:
                current_claim["Services"].append({f"{seg_name} {service_counter}": svc_data})
                
        elif seg_id == "SVC":
            # 835 service payment info
            svc_data = mapped.copy()
            if current_claim is not None:
                current_claim.setdefault("Service Payments", []).append(svc_data)
            else:
                result.setdefault("Service Payments", []).append(svc_data)
                
        elif seg_id == "CLP":
            # 835 claim payment
            clp_data = mapped.copy()
            status_codes = schema.get("segments", {}).get("CLP", {}).get("status_codes", {})
            status = elements[1] if len(elements) > 1 else ""
            if status in status_codes:
                clp_data["Claim Status Description"] = status_codes[status]
            
            current_claim = {"Claim Payment Information": clp_data}
            result.setdefault("Claims", []).append(current_claim)
            
        elif seg_id == "CAS":
            cas_data = mapped.copy()
            group_codes = schema.get("segments", {}).get("CAS", {}).get("group_codes", {})
            group = elements[0] if elements else ""
            if group in group_codes:
                cas_data["Adjustment Group Description"] = group_codes[group]
            
            if current_claim is not None:
                current_claim.setdefault("Adjustments", []).append(cas_data)
            else:
                result.setdefault("Adjustments", []).append(cas_data)
                
        elif seg_id == "BPR":
            result["Financial Information"] = mapped
            
        elif seg_id == "TRN":
            result["Trace Number"] = mapped
            
        elif seg_id == "INS":
            ins_data = mapped.copy()
            if current_subscriber is not None:
                current_subscriber["Member Detail"] = ins_data
            else:
                result.setdefault("Members", []).append({"Member Detail": ins_data})
                
        elif seg_id == "HD":
            hd_data = mapped.copy()
            maint_codes = schema.get("segments", {}).get("HD", {}).get("maintenance_codes", {})
            maint = elements[0] if elements else ""
            if maint in maint_codes:
                hd_data["Maintenance Type Description"] = maint_codes[maint]
            
            if current_subscriber is not None:
                current_subscriber.setdefault("Health Coverage", []).append(hd_data)
            else:
                result.setdefault("Health Coverage", []).append(hd_data)
                
        elif seg_id == "REF":
            ref_data = mapped.copy()
            qualifier_codes = schema.get("segments", {}).get("REF", {}).get("qualifier_codes", {})
            qualifier = elements[0] if elements else ""
            qualifier_name = qualifier_codes.get(qualifier, f"Reference {qualifier}")
            
            ref_entry = {qualifier_name: ref_data}
            
            if current_claim is not None:
                current_claim.setdefault("References", {}).update(ref_entry)
            elif current_subscriber is not None:
                current_subscriber.setdefault("References", {}).update(ref_entry)
            elif current_section == "Billing Provider":
                result.setdefault("Billing Provider", {}).setdefault("References", {}).update(ref_entry)
            else:
                result.setdefault("References", {}).update(ref_entry)
                
        elif seg_id == "PER":
            per_data = mapped
            if current_section == "Billing Provider":
                result.setdefault("Billing Provider", {})["Contact Information"] = per_data
            else:
                result.setdefault("Contact Information", []).append(per_data) if isinstance(result.get("Contact Information"), list) else result.update({"Contact Information": per_data})
                
        elif seg_id == "AMT":
            amt_data = mapped
            # Resolve qualifier code description
            amt_qualifiers = schema.get("segments", {}).get("AMT", {}).get("qualifier_codes", {})
            q_code = elements[0] if elements else ""
            if q_code in amt_qualifiers:
                amt_data["Amount Type"] = amt_qualifiers[q_code]
            if current_claim is not None:
                current_claim.setdefault("Monetary Amounts", []).append(amt_data)
            else:
                result.setdefault("Monetary Amounts", []).append(amt_data)

        elif seg_id == "LQ":
            lq_data = mapped.copy()
            lq_quals = schema.get("segments", {}).get("LQ", {}).get("qualifier_codes", {})
            q = elements[0] if elements else ""
            if q in lq_quals:
                lq_data["Remark Type"] = lq_quals[q]
            if current_claim is not None:
                current_claim.setdefault("Remark Codes", []).append(lq_data)
            else:
                result.setdefault("Remark Codes", []).append(lq_data)

        elif seg_id == "LX":
            # Transaction Set Line Number — used as a grouping marker
            result.setdefault("Line Items", []).append({"Line Number": mapped})

        elif seg_id == "MIA":
            if current_claim is not None:
                current_claim["Inpatient Adjudication"] = mapped
            else:
                result["Inpatient Adjudication"] = mapped

        elif seg_id == "MOA":
            if current_claim is not None:
                current_claim["Outpatient Adjudication"] = mapped
            else:
                result["Outpatient Adjudication"] = mapped

        elif seg_id == "RDM":
            result["Remittance Delivery Method"] = mapped

        elif seg_id in ("TS3", "TS2"):
            seg_name = schema.get("segments", {}).get(seg_id, {}).get("name", seg_id)
            result[seg_name] = mapped

        elif seg_id == "CR1":
            if current_claim is not None:
                current_claim["Ambulance Transport Information"] = mapped
            else:
                result["Ambulance Transport Information"] = mapped

        elif seg_id == "CRC":
            crc_data = mapped.copy()
            cat_codes = schema.get("segments", {}).get("CRC", {}).get("category_codes", {})
            cat = elements[0] if elements else ""
            if cat in cat_codes:
                crc_data["Category Description"] = cat_codes[cat]
            if current_claim is not None:
                current_claim.setdefault("Conditions", []).append(crc_data)
            else:
                result.setdefault("Conditions", []).append(crc_data)

        elif seg_id == "PWK":
            pwk_data = mapped.copy()
            report_codes = schema.get("segments", {}).get("PWK", {}).get("report_type_codes", {})
            rpt = elements[0] if elements else ""
            if rpt in report_codes:
                pwk_data["Report Type Description"] = report_codes[rpt]
            if current_claim is not None:
                current_claim.setdefault("Supplemental Information", []).append(pwk_data)
            else:
                result.setdefault("Supplemental Information", []).append(pwk_data)

        elif seg_id == "CN1":
            cn1_data = mapped.copy()
            contract_codes = schema.get("segments", {}).get("CN1", {}).get("contract_type_codes", {})
            ct = elements[0] if elements else ""
            if ct in contract_codes:
                cn1_data["Contract Type Description"] = contract_codes[ct]
            if current_claim is not None:
                current_claim["Contract Information"] = cn1_data
            else:
                result["Contract Information"] = cn1_data

        elif seg_id == "OI":
            if current_claim is not None:
                current_claim["Other Insurance Coverage"] = mapped
            else:
                result["Other Insurance Coverage"] = mapped

        elif seg_id == "SVD":
            svd_data = mapped.copy()
            if current_claim is not None:
                current_claim.setdefault("Line Adjudications", []).append(svd_data)
            else:
                result.setdefault("Line Adjudications", []).append(svd_data)

        elif seg_id == "DTM":
            dtm_data = mapped.copy()
            dtm_quals = schema.get("segments", {}).get("DTM", {}).get("qualifier_codes", {})
            q = elements[0] if elements else ""
            q_name = dtm_quals.get(q, f"Date Reference {q}")
            if current_claim is not None:
                current_claim.setdefault("Dates", {})[q_name] = dtm_data
            else:
                result.setdefault("Dates", {})[q_name] = dtm_data

        elif seg_id == "EC":
            if current_subscriber is not None:
                current_subscriber["Employment Class"] = mapped
            else:
                result["Employment Class"] = mapped

        elif seg_id == "ICM":
            icm_data = mapped.copy()
            freq_codes = schema.get("segments", {}).get("ICM", {}).get("frequency_codes", {})
            freq = elements[0] if elements else ""
            if freq in freq_codes:
                icm_data["Frequency Description"] = freq_codes[freq]
            if current_subscriber is not None:
                current_subscriber["Individual Income"] = icm_data
            else:
                result["Individual Income"] = icm_data

        elif seg_id == "LUI":
            if current_subscriber is not None:
                current_subscriber.setdefault("Languages", []).append(mapped)
            else:
                result.setdefault("Languages", []).append(mapped)

        elif seg_id == "DSB":
            dsb_data = mapped.copy()
            type_codes = schema.get("segments", {}).get("DSB", {}).get("disability_type_codes", {})
            dt = elements[0] if elements else ""
            if dt in type_codes:
                dsb_data["Disability Type Description"] = type_codes[dt]
            if current_subscriber is not None:
                current_subscriber["Disability Information"] = dsb_data
            else:
                result["Disability Information"] = dsb_data

        elif seg_id == "COB":
            if current_subscriber is not None:
                current_subscriber.setdefault("Coordination of Benefits", []).append(mapped)
            else:
                result.setdefault("Coordination of Benefits", []).append(mapped)
                
        elif seg_id == "PLB":
            result.setdefault("Provider Adjustments", []).append(mapped)
            
        elif seg_id == "SE":
            result["Transaction Set Trailer"] = mapped
            
            # Validate CLM totals if we have line charges
            if current_claim and line_charges:
                clm_info = current_claim.get("Claim Information", {})
                total = clm_info.get("Total Claim Charge Amount")
                if total:
                    validation_context["line_charges"] = line_charges
                    clm_errors = validate_segment("CLM", clm_info, schema, validation_context)
                    if clm_errors:
                        clm_info.setdefault("_errors", []).extend(clm_errors)
                        errors_total += len(clm_errors)
            
            # Flush subscriber
            if current_subscriber:
                result.setdefault("Subscribers", []).append(current_subscriber)
                current_subscriber = None
                
        elif seg_id == "GE":
            result["Functional Group Trailer"] = mapped
            
        elif seg_id == "IEA":
            result["Interchange Trailer"] = mapped
            
        else:
            # Unknown or less common segments — still include them
            seg_name = schema.get("segments", {}).get(seg_id, {}).get("name", seg_id)
            if seg_name in result:
                if not isinstance(result[seg_name], list):
                    result[seg_name] = [result[seg_name]]
                result[seg_name].append(mapped)
            else:
                result[seg_name] = mapped
    
    # Flush any remaining subscriber
    if current_subscriber:
        result.setdefault("Subscribers", []).append(current_subscriber)
    
    total_segments = len(segments)
    valid_count = total_segments - errors_total
    
    stats = {
        "edi_type": edi_type,
        "total_segments": total_segments,
        "error_count": errors_total,
        "valid_count": max(0, valid_count),
    }
    
    return {"parsed": result, "stats": stats}


def parse_edi(raw: str, edi_type: str) -> dict:
    """
    Main entry point: parse raw EDI text into structured, validated JSON.
    
    Args:
        raw: the raw EDI file content as a string
        edi_type: '837', '835', or '834'
    
    Returns:
        {
            "parsed": { ... structured data ... },
            "stats": { ... summary stats ... }
        }
    """
    # Detect actual delimiters from ISA
    delimiters = detect_delimiters(raw)
    
    # Load the appropriate schema
    schema = load_schema(edi_type)
    
    # Shred the raw text into segments
    segments = shred(
        raw,
        segment_terminator=delimiters["segment_terminator"],
        element_separator=delimiters["element_separator"],
    )
    
    if not segments:
        return {
            "parsed": {"error": "No segments found in the file"},
            "stats": {"edi_type": edi_type, "total_segments": 0, "error_count": 1, "valid_count": 0},
        }
    
    # Build structured data with validation
    return build_structured_data(segments, schema, edi_type)
