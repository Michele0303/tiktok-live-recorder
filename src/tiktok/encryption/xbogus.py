"""
Implements MD5 hashing, RC4 encryption, and
custom base64 encoding for X-Bogus signature generation
"""

import hashlib
from typing import Union


# ── Constants ──────────────────────────────────────────
STANDARD_B64_ALPHABET = (
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
)
CUSTOM_B64_ALPHABET = "Dkdpgh4ZKsQB80/Mfvw36XI1R25-WUAlEi7NLboqYTOPuzmFjJnryx9HVGcaStCe"

# Create translation map for custom base64
ENC_TRANS = {
    STANDARD_B64_ALPHABET[i]: CUSTOM_B64_ALPHABET[i]
    for i in range(len(STANDARD_B64_ALPHABET))
}


# ── Helper functions ────────────────────────────────────
def custom_b64_encode(data: bytes) -> str:
    """Encode bytes using custom base64 alphabet"""
    import base64

    # Standard base64 encoding
    b64_str = base64.b64encode(data).decode("ascii")

    # Translate to custom alphabet
    result = ""
    for char in b64_str:
        result += ENC_TRANS.get(char, char)  # '=' and newlines pass through

    return result


def md5_hash(data: Union[str, bytes]) -> bytes:
    """Create MD5 hash of data"""
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.md5(data).digest()


def rc4_encrypt(key: bytes, plaintext: bytes) -> bytes:
    """RC4 encryption implementation"""
    # Key-scheduling algorithm (KSA)
    s = list(range(256))
    j = 0

    for i in range(256):
        j = (j + s[i] + key[i % len(key)]) % 256
        s[i], s[j] = s[j], s[i]

    # Pseudo-random generation algorithm (PRGA)
    result = bytearray()
    i = j = 0

    for byte in plaintext:
        i = (i + 1) % 256
        j = (j + s[i]) % 256
        s[i], s[j] = s[j], s[i]
        k = s[(s[i] + s[j]) % 256]
        result.append(byte ^ k)

    return bytes(result)


def xor_key(data: bytes) -> int:
    """Calculate XOR of all bytes in data"""
    result = 0
    for byte in data:
        result ^= byte
    return result


# ── Main encryption function ────────────────────────────
def sign_xbogus(params: str, post_data: str, user_agent: str, timestamp: int) -> str:
    """
    Generate X-Bogus signature

    Args:
        params: Query string parameters
        post_data: POST request body data
        user_agent: Browser user agent string
        timestamp: Unix timestamp in seconds (unsigned 32-bit)

    Returns:
        Custom base64 encoded signature string
    """
    # Keys and constants
    ua_key = bytes([0x00, 0x01, 0x0E])
    list_key = bytes([0xFF])
    fixed_val = 0x4A41279F  # 3845494467

    # Double MD5 hashes
    md5_params = md5_hash(md5_hash(params.encode("utf-8")))
    md5_post = md5_hash(md5_hash(post_data.encode("utf-8")))

    # User Agent processing: UA → RC4 → Base64 → MD5
    ua_rc4 = rc4_encrypt(ua_key, user_agent.encode("utf-8"))
    ua_b64 = custom_b64_encode(ua_rc4)
    md5_ua = md5_hash(ua_b64.encode("ascii"))

    # Build buffer exactly like JavaScript version
    buffer = bytearray()
    buffer.extend([0x40])  # Literal 64
    buffer.extend(ua_key)  # 3 bytes
    buffer.extend(md5_params[14:16])  # 2 bytes
    buffer.extend(md5_post[14:16])  # 2 bytes
    buffer.extend(md5_ua[14:16])  # 2 bytes
    buffer.extend((timestamp & 0xFFFFFFFF).to_bytes(4, "big"))  # 4 bytes, big-endian
    buffer.extend(fixed_val.to_bytes(4, "big"))  # 4 bytes, big-endian

    # Calculate and append checksum
    checksum = xor_key(buffer)
    buffer.extend([checksum])

    # Final wrapper
    final_data = bytearray()
    final_data.extend([0x02])  # Prefix byte
    final_data.extend(list_key)  # 1 byte
    final_data.extend(rc4_encrypt(list_key, buffer))  # RC4 encrypted buffer

    return custom_b64_encode(bytes(final_data))


# Export main function
__all__ = ["sign_xbogus"]
