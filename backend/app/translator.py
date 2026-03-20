"""Plain English Translator for Parsed EDI Data."""

def translate_to_english(data: dict, indent: int = 0) -> str:
    """Recursively convert nested EDI dictionary structure to plain English markdown."""
    lines = []
    
    if isinstance(data, dict):
        for key, value in data.items():
            if key == "_errors":
                continue
            
            # Simple strings
            if not isinstance(value, (dict, list)):
                lines.append(f"{'  ' * indent}- **{key}:** {value}")
            
            # Nested dictionaries
            elif isinstance(value, dict):
                lines.append(f"{'  ' * indent}- **{key}**")
                lines.append(translate_to_english(value, indent + 1))
                
            # Lists of items
            elif isinstance(value, list):
                lines.append(f"{'  ' * indent}- **{key}** ({len(value)} items):")
                for i, item in enumerate(value):
                    lines.append(f"{'  ' * (indent + 1)}*Item {i + 1}*")
                    if isinstance(item, (dict, list)):
                        lines.append(translate_to_english(item, indent + 2))
                    else:
                        lines.append(f"{'  ' * (indent + 2)}- {item}")
                        
    elif isinstance(data, list):
        for i, item in enumerate(data):
            lines.append(f"{'  ' * indent}*Item {i + 1}*")
            if isinstance(item, (dict, list)):
                lines.append(translate_to_english(item, indent + 1))
            else:
                lines.append(f"{'  ' * (indent + 1)}- {item}")
                
    return "\n".join(lines)


def generate_english_summary(parsed_data: dict, stats: dict) -> str:
    """Entry point to convert parsed output into a complete English file."""
    summary = []
    edi_type = stats.get('edi_type', 'Unknown')
    total = stats.get('total_segments', 0)
    errors = stats.get('error_count', 0)
    
    summary.append(f"# English Summary: EDI {edi_type} Document")
    summary.append(f"This document contains **{total} segments** with **{errors} validation errors**.")
    summary.append("## Details\n")
    
    summary.append(translate_to_english(parsed_data, 0))
    
    return "\n".join(summary)
