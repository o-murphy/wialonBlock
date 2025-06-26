# Helper function to escape characters for Markdown (Legacy)
def escape_markdown_legacy(text: str) -> str:
    """Escapes special characters for Telegram's Markdown (Legacy) parse_mode."""
    # Define the special characters that need to be escaped
    # and their corresponding escaped versions.
    # Note: In Legacy Markdown, the backslash '\' itself is not typically
    # listed as a character that needs escaping if it appears literally,
    # unlike MarkdownV2. So, no special handling for '\' first is required.
    special_chars = ['_', '*', '[', ']', '(', ')', '`']

    for char in special_chars:
        # Replace each special character with its escaped version (preceded by a backslash)
        text = text.replace(char, '\\' + char)

    return text


def escape_markdown_v2(text: str) -> str:
    """Escapes special characters for Telegram's MarkdownV2 parse_mode.

    According to Telegram Bot API documentation for MarkdownV2, the following
    characters must be escaped with a preceding backslash:
    '_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!', '\'

    The backslash character '\' itself must be escaped first to avoid double-escaping
    other characters in the string that were already preceded by a backslash.
    """
    # Escape the backslash character itself first. This is crucial
    # to prevent incorrect escaping of other special characters that might
    # already be preceded by a backslash in the original text.
    text = text.replace('\\', '\\\\')

    # List of other special characters in MarkdownV2 that need to be escaped.
    # The order of replacement for these characters generally doesn't matter
    # as they are all single-character replacements.
    special_chars = [
        '_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|',
        '{', '}', '.', '!'
    ]

    for char in special_chars:
        text = text.replace(char, '\\' + char)

    return text
