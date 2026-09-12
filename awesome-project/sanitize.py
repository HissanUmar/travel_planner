"""
sanitize.py — strips phone numbers from chat messages sent between mechanic and dealer.

Allows through:
  - Shop names (text, not filtered)
  - Bank account numbers (digits-only or with dashes, 10-18 digits — typical IBAN/account lengths)
  - Bank names and general numeric references

Blocks:
  - Pakistani mobile numbers: 03xxxxxxxxx (11 digits starting with 03)
  - Pakistani numbers with country code: +92xxxxxxxxxx, 92xxxxxxxxxx
  - International numbers: +1/+44/etc followed by 7-12 digits
  - WhatsApp-style shares of phone numbers embedded in text
"""

import re
import logging

logger = logging.getLogger(__name__)

# ── Phone number patterns to strip ──────────────────────────────────────────

_PHONE_PATTERNS = [
    # Pakistani mobile: 03xx-xxxxxxx or 03xxxxxxxxx (with optional separators)
    re.compile(r'\b0?3\d{2}[\s\-]?\d{7}\b'),
    # With +92 or 92 country code: +923xxxxxxxxx or 923xxxxxxxxx
    re.compile(r'(\+92|0092|92)[\s\-]?3\d{2}[\s\-]?\d{7}\b'),
    # Generic international: +[country_code][7-12 digits] — e.g. +1 234 567 8901
    re.compile(r'\+\d{1,3}[\s\-]?\(?\d{1,4}\)?[\s\-]?\d{3,5}[\s\-]?\d{4,6}\b'),
    # Landline Pakistan: 042-xxxxxxx, 021-xxxxxxxx
    re.compile(r'\b0\d{2,3}[\s\-]\d{6,8}\b'),
]

_PLACEHOLDER = "[phone number removed]"

def sanitize_message(text: str) -> str:
    """
    Removes phone numbers from an outbound message.
    Returns the sanitized string and logs if anything was stripped.
    """
    if not text:
        return text

    sanitized = text
    for pattern in _PHONE_PATTERNS:
        sanitized = pattern.sub(_PLACEHOLDER, sanitized)

    if sanitized != text:
        logger.warning(f"Phone number stripped from outbound message. Original length: {len(text)}, sanitized length: {len(sanitized)}")

    return sanitized
