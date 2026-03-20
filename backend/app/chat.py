"""AI Chat integration using Google Gemini for EDI explanation."""

import os
import json
from typing import Optional


def get_explanation(question: str, context: Optional[dict] = None) -> str:
    """
    Send a contextual question to Google Gemini and return an explanation.
    
    Falls back to a helpful message if GEMINI_API_KEY is not set.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    
    if not api_key:
        return _fallback_response(question, context)
    
    try:
        import google.generativeai as genai
        
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.5-flash")
        
        # Build contextual prompt
        prompt = _build_prompt(question, context)
        
        response = model.generate_content(prompt)
        return response.text
        
    except ImportError:
        return "The Google Generative AI package is not installed. Run: pip install google-generativeai"
    except Exception as e:
        return f"AI Error: {str(e)}. Please check your GEMINI_API_KEY environment variable."


def _build_prompt(question: str, context: Optional[dict] = None) -> str:
    """Build a contextual prompt combining the user question with EDI data context."""
    
    system_context = """You are an expert EDI (Electronic Data Interchange) and HIPAA healthcare data analyst.
You help users understand EDI files (837 Professional Claims, 835 Remittance Advice, 834 Enrollment).
You explain segment codes, validation errors, HIPAA rules, and healthcare billing concepts in plain English.
Keep your answers concise, clear, and actionable. Use bullet points when listing multiple items.
If discussing an error, explain WHY it happened and HOW to fix it."""

    prompt_parts = [system_context, f"\n\nUser Question: {question}"]
    
    if context:
        # Include relevant parsed data context
        stats = context.get("stats", {})
        parsed = context.get("parsed", {})
        
        prompt_parts.append(f"\n\nEDI File Context:")
        prompt_parts.append(f"- File Type: {stats.get('edi_type', 'Unknown')}")
        prompt_parts.append(f"- Total Segments: {stats.get('total_segments', 0)}")
        prompt_parts.append(f"- Errors Found: {stats.get('error_count', 0)}")
        
        # Include a summary of the parsed data (truncated to avoid token limits)
        context_str = json.dumps(parsed, indent=2, default=str)
        if len(context_str) > 4000:
            context_str = context_str[:4000] + "\n... (truncated)"
        
        prompt_parts.append(f"\n\nParsed Data:\n```json\n{context_str}\n```")
    
    return "\n".join(prompt_parts)


def _fallback_response(question: str, context: Optional[dict] = None) -> str:
    """Provide a helpful response when no AI API key is configured."""
    
    question_lower = question.lower()
    
    # Common EDI questions with built-in answers
    if "npi" in question_lower:
        return ("**NPI (National Provider Identifier)** is a unique 10-digit number "
                "assigned to healthcare providers by CMS. It's validated using the Luhn algorithm "
                "with a '80840' prefix. If an NPI fails checksum validation, the check digit "
                "(last digit) is likely incorrect. You can verify NPIs at https://npiregistry.cms.hhs.gov/")
    
    if "837" in question_lower:
        return ("**837 (Health Care Claim)** is used to submit healthcare claims electronically. "
                "The 837P is for Professional claims, 837I for Institutional, and 837D for Dental. "
                "Key segments include: CLM (claim info), NM1 (names/NPIs), SV1 (service lines), "
                "DTP (dates), and HI (diagnosis codes).")
    
    if "835" in question_lower:
        return ("**835 (Health Care Claim Payment/Advice)** is the electronic remittance advice (ERA). "
                "It tells providers how claims were paid or denied. Key segments: BPR (payment info), "
                "CLP (claim payment), SVC (service line payment), CAS (adjustments), and NM1 (party names).")
    
    if "834" in question_lower:
        return ("**834 (Benefit Enrollment and Maintenance)** is used for enrolling or updating "
                "member benefits. Key segments: INS (member detail), NM1 (names), DMG (demographics), "
                "HD (health coverage), and DTP (effective dates).")
    
    if "clm" in question_lower or "claim" in question_lower:
        return ("**CLM (Claim Information)** segment contains: CLM01 = Patient Account Number, "
                "CLM02 = Total Claim Charge Amount, CLM05 = Place of Service. "
                "The total charge (CLM02) should equal the sum of all SV1 line item charges.")
    
    if "error" in question_lower or "fix" in question_lower:
        errors_info = ""
        if context and context.get("stats", {}).get("error_count", 0) > 0:
            errors_info = (f"\n\nYour file has {context['stats']['error_count']} error(s). "
                          "Check the tree view for red-highlighted segments with error details.")
        return (f"Common EDI errors include: invalid NPIs (Luhn check failure), "
                f"date logic errors (DOB after service date), charge amount mismatches, "
                f"and missing required fields.{errors_info}")
    
    # Generic fallback
    response = ("I'm the EDI Assistant! I can help explain EDI segments, HIPAA rules, "
                "and validation errors. To enable AI-powered responses, set the "
                "`GEMINI_API_KEY` environment variable.\n\n"
                "**Try asking about:**\n"
                "- What is an NPI?\n"
                "- Explain the 837 file format\n"
                "- What does the CLM segment mean?\n"
                "- How do I fix validation errors?")
    
    if context and context.get("stats"):
        stats = context["stats"]
        response += (f"\n\n**Your file:** Type {stats.get('edi_type', '?')}, "
                    f"{stats.get('total_segments', 0)} segments, "
                    f"{stats.get('error_count', 0)} errors")
    
    return response
