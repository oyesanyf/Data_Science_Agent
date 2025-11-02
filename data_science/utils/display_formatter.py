"""
Display formatter utility for ensuring all tool outputs have proper __display__ fields.
This ensures the LLM can extract and show formatted output in the UI.
"""
from typing import Dict, Any

def add_display_fields(result: Dict[str, Any], formatted_message: str) -> Dict[str, Any]:
    """
    Add standardized display fields to a tool result dictionary.
    
    The LLM checks these fields in priority order:
    1. __display__ (HIGHEST PRIORITY)
    2. text, message, ui_text, content
    3. _formatted_output (fallback)
    
    Args:
        result: The existing result dictionary from a tool
        formatted_message: The pre-formatted message to display to users
    
    Returns:
        Updated result dictionary with all display fields
    
    Example:
        result = {"status": "success", "data": {...}}
        formatted = "✅ Operation complete: 100 rows processed"
        result = add_display_fields(result, formatted)
        # Now result has __display__, text, message, etc.
    """
    display_fields = {
        "__display__": formatted_message,  # HIGHEST PRIORITY - LLM checks this first
        "text": formatted_message,
        "message": formatted_message,
        "ui_text": formatted_message,
        "content": formatted_message,
        "display": formatted_message,
        "_formatted_output": formatted_message,
    }
    
    # Update result with display fields (doesn't overwrite existing data fields)
    result.update(display_fields)
    
    return result


def format_success_message(title: str, details: list = None, emoji: str = "✅") -> str:
    """
    Create a standardized success message with optional details.
    
    Args:
        title: Main success message
        details: Optional list of detail lines
        emoji: Emoji prefix (default: ✅)
    
    Returns:
        Formatted message string
    
    Example:
        msg = format_success_message(
            "Data Cleaned",
            ["100 rows processed", "5 columns cleaned", "No missing values"]
        )
    """
    parts = [f"{emoji} **{title}**"]
    if details:
        parts.append("")  # Empty line
        for detail in details:
            parts.append(f"  • {detail}")
    return "\n".join(parts)


def format_error_message(error: str, suggestions: list = None) -> str:
    """
    Create a standardized error message with optional suggestions.
    
    Args:
        error: Error description
        suggestions: Optional list of suggestions to fix the error
    
    Returns:
        Formatted error message string
    """
    parts = [f"❌ **Error:** {error}"]
    if suggestions:
        parts.append("\n**Suggestions:**")
        for i, suggestion in enumerate(suggestions, 1):
            parts.append(f"{i}. {suggestion}")
    return "\n".join(parts)


def format_data_summary(rows: int, columns: int, details: dict = None) -> str:
    """
    Create a standardized data summary message.
    
    Args:
        rows: Number of rows
        columns: Number of columns
        details: Optional dict with additional details (e.g., numeric_features, categorical_features)
    
    Returns:
        Formatted data summary string
    """
    parts = [
        f"📊 **Data Summary**",
        f"",
        f"**Shape:** {rows:,} rows × {columns} columns",
    ]
    
    if details:
        if "numeric_features" in details:
            parts.append(f"**Numeric Features:** {details['numeric_features']}")
        if "categorical_features" in details:
            parts.append(f"**Categorical Features:** {details['categorical_features']}")
        if "missing_values" in details:
            parts.append(f"**Missing Values:** {details['missing_values']}")
        if "memory_mb" in details:
            parts.append(f"**Memory:** ~{details['memory_mb']:.1f} MB")
    
    return "\n".join(parts)


def format_artifact_list(artifacts: list, artifact_type: str = "artifact") -> str:
    """
    Create a formatted list of artifacts.
    
    Args:
        artifacts: List of artifact names or dicts with metadata
        artifact_type: Type of artifacts (e.g., "plot", "report", "model")
    
    Returns:
        Formatted artifact list string
    """
    if not artifacts:
        return f"⚠️ No {artifact_type}s generated."
    
    parts = [f"📁 **{artifact_type.title()}s Generated:**", ""]
    
    for i, artifact in enumerate(artifacts, 1):
        if isinstance(artifact, dict):
            name = artifact.get("filename") or artifact.get("name") or str(artifact.get("path", "unknown"))
            version = artifact.get("version")
            if version:
                parts.append(f"{i}. **{name}** (v{version})")
            else:
                parts.append(f"{i}. **{name}**")
        else:
            parts.append(f"{i}. **{artifact}**")
    
    parts.append(f"\n✅ **Total:** {len(artifacts)} {artifact_type}{'s' if len(artifacts) > 1 else ''}")
    parts.append(f"💡 **View:** Check the Artifacts panel (right side) to access them!")
    
    return "\n".join(parts)

