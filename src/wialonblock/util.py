# Helper function to escape characters for Markdown (Legacy)
def escape_markdown_legacy(text: str) -> str:
    """Escapes special characters for Telegram's Markdown (Legacy) parse_mode."""
    # Escape _ and *
    # These are the most common offenders in legacy Markdown
    text = text.replace('_', '\\_')
    text = text.replace('*', '\\*')
    # For links, you might also need to escape [ ] ( ) if they appear in text literally
    text = text.replace('[', '\\[')
    text = text.replace(']', '\\]')
    text = text.replace('(', '\\(')
    text = text.replace(')', '\\)')
    # For inline code, escape `
    text = text.replace('`', '\\`')
    return text