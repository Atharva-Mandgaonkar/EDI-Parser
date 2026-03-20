"""EDI type sniffer — detects 837, 835, or 834 from raw EDI text."""


def detect_edi_type(raw: str) -> str:
    """
    Scan the raw EDI text for the ST (Transaction Set Header) segment
    and return the transaction set identifier: '837', '835', or '834'.
    
    Returns 'unknown' if no matching ST segment is found.
    """
    # Determine segment terminator (usually ~)
    terminator = "~"
    
    lines = raw.split(terminator)
    
    for line in lines:
        stripped = line.strip()
        elements = stripped.split("*")
        
        if elements[0].upper() == "ST" and len(elements) >= 2:
            code = elements[1].strip()
            if code in ("837", "835", "834"):
                return code
            # Sometimes the full code is like 837 with qualifier
            if code.startswith("837"):
                return "837"
            if code.startswith("835"):
                return "835"
            if code.startswith("834"):
                return "834"
    
    return "unknown"


def detect_delimiters(raw: str) -> dict:
    """
    Detect the segment terminator and element separator from the ISA segment.
    ISA is always exactly 106 characters and the last char is the segment terminator.
    Element separator is the 4th character (ISA*...).
    Sub-element separator is char 105 (position 104, zero-indexed).
    """
    defaults = {
        "element_separator": "*",
        "segment_terminator": "~",
        "sub_element_separator": ":",
    }
    
    # Find ISA segment
    isa_pos = raw.upper().find("ISA")
    if isa_pos == -1:
        return defaults
    
    # Element separator is the character right after ISA
    if len(raw) > isa_pos + 3:
        defaults["element_separator"] = raw[isa_pos + 3]
    
    # ISA segment is exactly 106 chars; the last is the segment terminator
    if len(raw) >= isa_pos + 106:
        defaults["segment_terminator"] = raw[isa_pos + 105]
        defaults["sub_element_separator"] = raw[isa_pos + 104]
    
    return defaults
