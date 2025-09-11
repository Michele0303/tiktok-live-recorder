"""
Implements ChaCha20 encryption and custom base64 encoding for
X-Gnarly signature generation
"""

import hashlib
import random
import time
from typing import List, Optional


# ── Constants ──────────────────────────────────────────
aa = [
    0xFFFFFFFF,
    138,
    1498001188,
    211147047,
    253,
    None,
    203,
    288,
    9,
    1196819126,
    3212677781,
    135,
    263,
    193,
    58,
    18,
    244,
    2931180889,
    240,
    173,
    268,
    2157053261,
    261,
    175,
    14,
    5,
    171,
    270,
    156,
    258,
    13,
    15,
    3732962506,
    185,
    169,
    2,
    6,
    132,
    162,
    200,
    3,
    160,
    217618912,
    62,
    2517678443,
    44,
    164,
    4,
    96,
    183,
    2903579748,
    3863347763,
    119,
    181,
    10,
    190,
    8,
    2654435769,
    259,
    104,
    230,
    128,
    2633865432,
    225,
    1,
    257,
    143,
    179,
    16,
    600974999,
    185100057,
    32,
    188,
    53,
    2718276124,
    177,
    196,
    4294967296,
    147,
    117,
    17,
    49,
    7,
    28,
    12,
    266,
    216,
    11,
    0,
    45,
    166,
    247,
    1451689750,
]

Ot = [aa[9], aa[69], aa[51], aa[92]]  # Constants prepended to ChaCha key
MASK32 = 0xFFFFFFFF


# ── PRNG State Initialization ──────────────────────────
def init_prng_state() -> List[int]:
    """Initialize PRNG state matching JavaScript implementation"""
    now_ms = int(time.time() * 1000)
    return [
        aa[44],
        aa[74],
        aa[10],
        aa[62],
        aa[42],
        aa[17],
        aa[2],
        aa[21],
        aa[3],
        aa[70],
        aa[50],
        aa[32],
        aa[0] & now_ms,
        random.randint(0, aa[77] - 1),
        random.randint(0, aa[77] - 1),
        random.randint(0, aa[77] - 1),
    ]


# Global PRNG state
kt = init_prng_state()
St = aa[88]  # Position pointer (starts at 0)


# ── Bit manipulation helpers ───────────────────────────
def u32(x: int) -> int:
    """Ensure unsigned 32-bit integer"""
    return x & MASK32


def rotl(x: int, n: int) -> int:
    """32-bit left rotation"""
    x = u32(x)
    return u32((x << n) | (x >> (32 - n)))


# ── ChaCha Core Functions ──────────────────────────────
def quarter_round(st: List[int], a: int, b: int, c: int, d: int) -> None:
    """ChaCha quarter round"""
    st[a] = u32(st[a] + st[b])
    st[d] = rotl(st[d] ^ st[a], 16)
    st[c] = u32(st[c] + st[d])
    st[b] = rotl(st[b] ^ st[c], 12)
    st[a] = u32(st[a] + st[b])
    st[d] = rotl(st[d] ^ st[a], 8)
    st[c] = u32(st[c] + st[d])
    st[b] = rotl(st[b] ^ st[c], 7)


def chacha_block(state: List[int], rounds: int) -> List[int]:
    """Generate ChaCha block"""
    w = state.copy()  # Working copy

    for r in range(0, rounds, 2):
        # Column rounds
        quarter_round(w, 0, 4, 8, 12)
        quarter_round(w, 1, 5, 9, 13)
        quarter_round(w, 2, 6, 10, 14)
        quarter_round(w, 3, 7, 11, 15)

        if r + 1 >= rounds:
            break

        # Diagonal rounds
        quarter_round(w, 0, 5, 10, 15)
        quarter_round(w, 1, 6, 11, 12)
        quarter_round(w, 2, 7, 12, 13)
        quarter_round(w, 3, 4, 13, 14)

    for i in range(16):
        w[i] = u32(w[i] + state[i])

    return w


def bump_counter(st: List[int]) -> None:
    """Increment ChaCha counter"""
    st[12] = u32(st[12] + 1)


# ── JavaScript-faithful PRNG ───────────────────────────
def rand() -> float:
    """Random number generator matching JavaScript implementation"""
    global St, kt

    e = chacha_block(kt, 8)  # 8 double-rounds
    t = e[St]
    r = (e[St + 8] & 0xFFFFFFF0) >> 11

    if St == 7:
        bump_counter(kt)
        St = 0
    else:
        St += 1

    return (t + 4294967296 * r) / (2**53)


# ── Utility Functions ──────────────────────────────────
def num_to_bytes(val: int) -> List[int]:
    """Convert number to bytes array"""
    if val < 255 * 255:
        return [(val >> 8) & 0xFF, val & 0xFF]
    else:
        return [(val >> 24) & 0xFF, (val >> 16) & 0xFF, (val >> 8) & 0xFF, val & 0xFF]


def be_int_from_str(s: str) -> int:
    """Convert string to big-endian integer"""
    data = s.encode("utf-8")[:4]
    acc = 0
    for byte in data:
        acc = (acc << 8) | byte
    return acc & 0xFFFFFFFF


# ── Message Encryption (ChaCha) ────────────────────────
def encrypt_chacha(key_words: List[int], rounds: int, data: bytearray) -> None:
    """Encrypt data using ChaCha stream cipher"""
    # Pack to 32-bit words, little-endian
    n_full = len(data) // 4
    leftover = len(data) % 4
    words = [0] * ((len(data) + 3) // 4)

    for i in range(n_full):
        j = 4 * i
        words[i] = (
            data[j] | (data[j + 1] << 8) | (data[j + 2] << 16) | (data[j + 3] << 24)
        )

    if leftover:
        v = 0
        base = 4 * n_full
        for c in range(leftover):
            v |= data[base + c] << (8 * c)
        words[n_full] = v

    # XOR with ChaCha stream
    o = 0
    state = key_words.copy()

    while o + 16 < len(words):
        stream = chacha_block(state, rounds)
        bump_counter(state)
        for k in range(16):
            words[o + k] ^= stream[k]
        o += 16

    # Handle remaining words
    remain = len(words) - o
    stream = chacha_block(state, rounds)
    for k in range(remain):
        words[o + k] ^= stream[k]

    # Flatten back to bytes
    for i in range(n_full):
        w = words[i]
        j = 4 * i
        data[j] = w & 0xFF
        data[j + 1] = (w >> 8) & 0xFF
        data[j + 2] = (w >> 16) & 0xFF
        data[j + 3] = (w >> 24) & 0xFF

    if leftover:
        w = words[n_full]
        base = 4 * n_full
        for c in range(leftover):
            data[base + c] = (w >> (8 * c)) & 0xFF


# ── Ab22 Helper Function ───────────────────────────────
def Ab22(key_12_words: List[int], rounds: int, s: str) -> str:
    """ChaCha encryption helper: prepend Ot, encrypt, return string"""
    state = Ot + key_12_words  # 16-word state
    data = bytearray(ord(ch) for ch in s)
    encrypt_chacha(state, rounds, data)
    return "".join(chr(b) for b in data)


# ── Main Encryption Function ───────────────────────────
def sign_xgnarly(
    query_string: str,
    body: str,
    user_agent: str,
    envcode: int = 0,
    version: str = "5.1.1",
    timestamp_ms: Optional[int] = None,
) -> str:
    """
    Generate X-Gnarly signature

    Args:
        query_string: URL query string parameters
        body: Request body data
        user_agent: Browser user agent string
        envcode: Environment code (default 0)
        version: Version string (default "5.1.1")
        timestamp_ms: Timestamp in milliseconds (default current time)

    Returns:
        Custom base64 encoded signature string
    """
    if timestamp_ms is None:
        timestamp_ms = int(time.time() * 1000)

    # Build the object map with insertion order intact
    obj = {}
    obj[1] = 1
    obj[2] = envcode
    obj[3] = hashlib.md5(query_string.encode("utf-8")).hexdigest()
    obj[4] = hashlib.md5(body.encode("utf-8")).hexdigest()
    obj[5] = hashlib.md5(user_agent.encode("utf-8")).hexdigest()
    obj[6] = timestamp_ms // 1000
    obj[7] = 1508145731
    obj[8] = (timestamp_ms * 1000) % 2147483648
    obj[9] = version

    if version == "5.1.1":
        obj[10] = "1.0.0.314"
        obj[11] = 1
        v12 = 0
        for i in range(1, 12):
            v = obj[i]
            to_xor = v if isinstance(v, int) else be_int_from_str(str(v))
            v12 ^= to_xor
        obj[12] = v12 & 0xFFFFFFFF
    elif version != "5.1.0":
        raise ValueError(f"Unsupported version: {version}")

    # Compute v0 after obj[12] (Python order)
    v0 = 0
    for i in range(1, len(obj) + 1):
        v = obj[i]
        if isinstance(v, int):
            v0 ^= v
    obj[0] = v0 & 0xFFFFFFFF

    # Serialize payload
    payload = []
    payload.append(len(obj))  # Count byte

    for k in sorted(obj.keys()):
        v = obj[k]
        payload.append(k)

        if isinstance(v, int):
            val_bytes = num_to_bytes(v)
        else:
            val_bytes = list(str(v).encode("utf-8"))

        payload.extend(num_to_bytes(len(val_bytes)))
        payload.extend(val_bytes)

    base_str = "".join(chr(b) for b in payload)

    # Generate 12 random key words
    key_words = []
    key_bytes = []
    round_accum = 0

    for _ in range(12):
        rnd = rand()
        word = int(rnd * 4294967296) & 0xFFFFFFFF  # 2^32 * rnd
        key_words.append(word)
        round_accum = (round_accum + (word & 15)) & 15

        # Little-endian bytes
        key_bytes.extend(
            [word & 0xFF, (word >> 8) & 0xFF, (word >> 16) & 0xFF, (word >> 24) & 0xFF]
        )

    rounds = round_accum + 5

    # Encrypt base_str
    enc = Ab22(key_words, rounds, base_str)

    # Splice key_bytes into enc at computed insert_pos
    insert_pos = 0
    for b in key_bytes:
        insert_pos = (insert_pos + b) % (len(enc) + 1)
    for ch in enc:
        insert_pos = (insert_pos + ord(ch)) % (len(enc) + 1)

    key_bytes_str = "".join(chr(b) for b in key_bytes)
    final_str = (
        chr(((1 << 6) ^ (1 << 3) ^ 3) & 0xFF)  # Constant 'K'
        + enc[:insert_pos]
        + key_bytes_str
        + enc[insert_pos:]
    )

    # Custom alphabet Base64
    alphabet = "u09tbS3UvgDEe6r-ZVMXzLpsAohTn7mdINQlW412GqBjfYiyk8JORCF5/xKHwacP="
    result = []

    full_len = (len(final_str) // 3) * 3
    for i in range(0, full_len, 3):
        block = (
            (ord(final_str[i]) << 16)
            | (ord(final_str[i + 1]) << 8)
            | ord(final_str[i + 2])
        )

        result.extend(
            [
                alphabet[(block >> 18) & 63],
                alphabet[(block >> 12) & 63],
                alphabet[(block >> 6) & 63],
                alphabet[block & 63],
            ]
        )

    return "".join(result)


# Export main function
__all__ = ["sign_xgnarly"]
