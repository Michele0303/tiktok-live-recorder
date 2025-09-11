"""
Implements ChaCha20 encryption, LZW compression, and custom base64 encoding
"""

import random
import time
from typing import List, Tuple, Optional


# ── Constants ────────────────────────────────────────────
MASK32 = 0xFFFFFFFF

# Tables copied verbatim from JavaScript
aa = [
    73,
    110,
    149,
    151,
    103,
    107,
    13,
    5,
    4294967296,
    154,
    2718276124,
    211147047,
    2931180889,
    142,
    185100057,
    17,
    37,
    7,
    3212677781,
    217618912,
    16,
    79,
    4294967295,
    4,
    120,
    175,
    133,
    2,
    None,
    600974999,
    200,
    188,
    14,
    36,
    3,
    124,
    156,  # None represents the regex pattern
    2633865432,
    163,
    1451689750,
    3863347763,
    8,
    2157053261,
    112,
    28,
    138,
    288,
    258,
    3732962506,
    172,
    101,
    1,
    116,
    83,
    203,
    11,
    1196819126,
    1498001188,
    15,
    122,
    118,
    77,
    159,
    136,
    2903579748,
    147,
    92,
    12,
    193,
    6,
    18,
    10,
    114,
    32,
    9,
    0,
    131,
    128,
    42,
    2517678443,
]

# Initialize ChaCha state
me = [
    aa[79],
    aa[10],
    aa[18],
    aa[37],
    aa[19],
    aa[12],
    aa[57],
    aa[42],
    aa[11],
    aa[14],
    aa[64],
    aa[48],
    aa[22] & int(time.time() * 1000),
    random.randint(0, aa[8] - 1),
    random.randint(0, aa[8] - 1),
    random.randint(0, aa[8] - 1),
]

ge = [aa[56], aa[29], aa[40], aa[39]]
ye = aa[75]


# ── Bit helpers ──────────────────────────────────────────
def u32(x: int) -> int:
    """Ensure unsigned 32-bit integer"""
    return x & MASK32


def rotl32(x: int, n: int) -> int:
    """32-bit left rotation"""
    x = u32(x)
    return u32((x << n) | (x >> (32 - n)))


# ── ChaCha core ──────────────────────────────────────────
def quarter_round(s: List[int], a: int, b: int, c: int, d: int) -> None:
    """ChaCha quarter round"""
    s[a] = u32(s[a] + s[b])
    s[d] = rotl32(s[d] ^ s[a], 16)
    s[c] = u32(s[c] + s[d])
    s[b] = rotl32(s[b] ^ s[c], 12)
    s[a] = u32(s[a] + s[b])
    s[d] = rotl32(s[d] ^ s[a], 8)
    s[c] = u32(s[c] + s[d])
    s[b] = rotl32(s[b] ^ s[c], 7)


def chacha_block(st: List[int], rounds: int) -> List[int]:
    """Generate ChaCha block"""
    x = st.copy()

    for r in range(0, rounds, 2):
        # Column rounds
        quarter_round(x, 0, 4, 8, 12)
        quarter_round(x, 1, 5, 9, 13)
        quarter_round(x, 2, 6, 10, 14)
        quarter_round(x, 3, 7, 11, 15)

        if r + 1 >= rounds:
            break

        # Diagonal rounds
        quarter_round(x, 0, 5, 10, 15)
        quarter_round(x, 1, 6, 11, 12)
        quarter_round(x, 2, 7, 12, 13)
        quarter_round(x, 3, 4, 13, 14)

    for i in range(16):
        x[i] = u32(x[i] + st[i])

    return x


def bump_counter(s: List[int]) -> None:
    """Increment ChaCha counter"""
    s[12] = u32(s[12] + 1)


# ── PRNG identical to JavaScript _rand() ─────────────────
def _rand() -> float:
    """Random number generator matching JavaScript implementation"""
    global ye, me

    rf = [4294965248, 0, 4294967296, 2, 8, 11, 53, 7]
    blk = chacha_block(me, rf[4])
    t = blk[ye]
    r = (rf[0] & blk[ye + rf[4]]) >> rf[5]

    if ye == rf[7]:
        bump_counter(me)
        ye = 0
    else:
        ye += 1

    return (t + rf[2] * r) / (2 ** rf[6])


# ── LZW compression/decompression ────────────────────────
def lzw_encode(data: bytes) -> bytes:
    """LZW compression"""
    # Initialize dictionary with single characters
    dictionary = {bytes([i]): i for i in range(256)}
    next_code = 256
    width = 8
    bucket = 0
    filled = 0
    result = []

    def flush(code: int) -> None:
        nonlocal bucket, filled
        bucket |= code << filled
        filled += width
        while filled >= 8:
            result.append(bucket & 0xFF)
            bucket >>= 8
            filled -= 8

    w = b""
    for byte in data:
        c = bytes([byte])
        wc = w + c
        if wc in dictionary:
            w = wc
        else:
            flush(dictionary[w])
            dictionary[wc] = next_code
            next_code += 1
            if next_code > (1 << width):
                width += 1
            w = c

    if w:
        flush(dictionary[w])

    if filled > 0:
        result.append(bucket & 0xFF)

    return bytes(result)


def lzw_decode(data: bytes) -> bytes:
    """LZW decompression"""
    # Initialize dictionary
    dictionary = {i: bytes([i]) for i in range(256)}
    next_code = 256
    width = 8
    bucket = 0
    filled = 0
    idx = 0

    def read_code() -> Optional[int]:
        nonlocal bucket, filled, idx
        while filled < width and idx < len(data):
            bucket |= data[idx] << filled
            idx += 1
            filled += 8

        if filled < width:
            return None

        code = bucket & ((1 << width) - 1)
        bucket >>= width
        filled -= width
        return code

    first_code = read_code()
    if first_code is None:
        return b""

    w = dictionary[first_code]
    result = bytearray(w)

    while True:
        if next_code == (1 << width):
            width += 1

        k = read_code()
        if k is None:
            break

        if k in dictionary:
            entry = dictionary[k]
        elif k == next_code:
            entry = w + bytes([w[0]])
        else:
            raise ValueError("Corrupt LZW stream")

        result.extend(entry)
        dictionary[next_code] = w + bytes([entry[0]])
        next_code += 1
        w = entry

    return bytes(result)


# ── ChaCha XOR helper ─────────────────────────────────────
def xor_chacha(key_words: List[int], rounds: int, data: bytearray) -> None:
    """XOR data with ChaCha stream"""
    # Pack bytes into 32-bit words (little-endian)
    words = [0] * ((len(data) + 3) // 4)
    for i in range(len(data)):
        words[i // 4] |= data[i] << ((i & 3) * 8)

    st = key_words.copy()
    off = 0

    while off + 16 < len(words):
        ks = chacha_block(st, rounds)
        bump_counter(st)
        for j in range(16):
            words[off + j] ^= ks[j]
        off += 16

    # Handle remaining words
    ks_tail = chacha_block(st, rounds)
    for j in range(off, len(words)):
        words[j] ^= ks_tail[j - off]

    # Unpack words back to bytes
    for i in range(len(data)):
        data[i] = (words[i // 4] >> ((i & 3) * 8)) & 0xFF


# ── Wrapper function ──────────────────────────────────────
def gg6(key: List[int], rounds: int, txt: str) -> str:
    """ChaCha encryption wrapper"""
    st = ge + key
    buf = bytearray(txt.encode("latin1"))
    xor_chacha(st, rounds, buf)
    return buf.decode("latin1")


# ── Key generation ────────────────────────────────────────
def make_key() -> Tuple[List[int], bytes, int]:
    """Generate encryption key"""
    key = []
    key_bytes = []
    acc = 0

    for _ in range(12):
        num = u32(int(_rand() * (2**32)))
        key.append(num)
        acc = (acc + (num & 15)) & 15

        # Convert to little-endian bytes
        key_bytes.extend(
            [num & 0xFF, (num >> 8) & 0xFF, (num >> 16) & 0xFF, (num >> 24) & 0xFF]
        )

    return key, bytes(key_bytes), acc + 5


# ── Custom Base64 ─────────────────────────────────────────
CS = "Dkdpgh4ZKsQB80/Mfvw36XI1R25+WUAlEi7NLboqYTOPuzmFjJnryx9HVGcaStCe="
PAD = CS[64]
INV = {c: i for i, c in enumerate(CS)}


def b64_encode(data: str) -> str:
    """Custom base64 encoding"""
    result = []
    i = 0

    while i + 2 < len(data):
        v = (ord(data[i]) << 16) | (ord(data[i + 1]) << 8) | ord(data[i + 2])
        result.extend(
            [CS[(v >> 18) & 63], CS[(v >> 12) & 63], CS[(v >> 6) & 63], CS[v & 63]]
        )
        i += 3

    rem = len(data) - i
    if rem == 1:
        v = ord(data[i]) << 16
        result.extend([CS[(v >> 18) & 63], CS[(v >> 12) & 63], PAD, PAD])
    elif rem == 2:
        v = (ord(data[i]) << 16) | (ord(data[i + 1]) << 8)
        result.extend([CS[(v >> 18) & 63], CS[(v >> 12) & 63], CS[(v >> 6) & 63], PAD])

    return "".join(result)


def b64_decode(data: str) -> str:
    """Custom base64 decoding"""
    result = []

    for i in range(0, len(data), 4):
        a = INV[data[i]]
        b = INV[data[i + 1]]
        c = 0 if data[i + 2] == PAD else INV[data[i + 2]]
        d = 0 if data[i + 3] == PAD else INV[data[i + 3]]

        v = (a << 18) | (b << 12) | (c << 6) | d

        result.append((v >> 16) & 255)
        if data[i + 2] != PAD:
            result.append((v >> 8) & 255)
        if data[i + 3] != PAD:
            result.append(v & 255)

    return bytes(result).decode("latin1")


# ── Main encryption function ──────────────────────────────
def encrypt_str(plain: str) -> str:
    """Encrypt string using ChaCha20 + LZW + custom base64"""
    key, key_bytes, rounds = make_key()

    # Step 1: UTF-8 to LZW
    lzw_bytes = lzw_encode(plain.encode("utf-8"))
    lzw_str = lzw_bytes.decode("latin1")

    # Step 2: ChaCha XOR
    cipher = gg6(key, rounds, lzw_str)

    # Step 3: Splice key bytes
    split = 0
    for b in key_bytes:
        split = (split + b) % (len(lzw_bytes) + 1)
    for ch in cipher:
        split = (split + ord(ch)) % (len(lzw_bytes) + 1)

    merged = "L" + cipher[:split] + key_bytes.decode("latin1") + cipher[split:]

    # Step 4: Custom Base64
    return b64_encode(merged)


# ── Main decryption function ──────────────────────────────
def decrypt_str(token: str, sample: int = 8) -> str:
    """Decrypt string using custom base64 + ChaCha20 + LZW"""
    raw = b64_decode(token)
    if not raw or raw[0] != "L":
        raise ValueError("Malformed ciphertext")

    merged = raw[1:]  # Remove 'L'
    total = len(merged) - 48  # Minus key chunk

    for split in range(total + 1):
        key_chunk = merged[split : split + 48]
        if len(key_chunk) < 48:
            break

        # Rebuild 12 little-endian unsigned 32-bit words
        key = []
        for i in range(0, 48, 4):
            w = (
                ord(key_chunk[i])
                | (ord(key_chunk[i + 1]) << 8)
                | (ord(key_chunk[i + 2]) << 16)
                | (ord(key_chunk[i + 3]) << 24)
            ) & MASK32
            key.append(w)

        rounds = ((sum(w & 15 for w in key)) & 15) + 5
        if rounds > 20:
            continue

        cipher = merged[:split] + merged[split + 48 :]

        # Probe a tiny prefix
        try:
            probe = gg6(key, rounds, cipher[:sample])
            probe_bytes = bytes(ord(c) for c in probe)
            probe_plain = lzw_decode(probe_bytes).decode("utf-8")

            # Check if ASCII-like
            ascii_ok = all(
                (31 < ord(ch) < 127) or ch in "\r\n\t" for ch in probe_plain[:32]
            )
            if not ascii_ok:
                continue
        except Exception:
            continue

        # Full decrypt
        try:
            full = gg6(key, rounds, cipher)
            full_bytes = bytes(ord(c) for c in full)
            plain = lzw_decode(full_bytes).decode("utf-8")
            return plain
        except Exception:
            continue

    raise ValueError("Unable to decrypt – key insertion point not found")


# Export main function
__all__ = ["encrypt_str", "decrypt_str"]
