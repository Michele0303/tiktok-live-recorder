import hashlib
import time
import math
import random
import re

# --- Constants / Seeds ---
aa = [
    4294967295,
    138,
    1498001188,
    211147047,
    253,
    re.compile(r"\s*\(\)\s*\{\s*\[\s*native\s+code\s*]\s*}\s*$"),
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


def _now_ms() -> int:
    return int(time.time() * 1000)


kt = [
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
    aa[0] & _now_ms(),
    math.floor(aa[77] * random.random()),
    math.floor(aa[77] * random.random()),
    math.floor(aa[77] * random.random()),
]
St = aa[88]
Ot = [aa[9], aa[69], aa[51], aa[92]]

# --- Primitive bitwise/ChaCha-like ---


def _rotl32(v: int, n: int) -> int:
    v &= 0xFFFFFFFF
    return ((v << n) & 0xFFFFFFFF) | (v >> (32 - n))


def _qr(e, t, r, n, o) -> None:
    # quarter round with rotation [16, 12, 8, 7]
    e[t] = (e[t] + e[r]) & 0xFFFFFFFF
    e[o] = _rotl32(e[o] ^ e[t], 16)
    e[n] = (e[n] + e[o]) & 0xFFFFFFFF
    e[r] = _rotl32(e[r] ^ e[n], 12)
    e[t] = (e[t] + e[r]) & 0xFFFFFFFF
    e[o] = _rotl32(e[o] ^ e[t], 8)
    e[n] = (e[n] + e[o]) & 0xFFFFFFFF
    e[r] = _rotl32(e[r] ^ e[n], 7)


def _inc_counter(e) -> None:
    e[12] = (e[12] + 1) & 0xFFFFFFFF


def _block(e, rounds: int):
    r = e[:]  # copy
    done = 0
    while done < rounds:
        # column round
        _qr(r, 0, 4, 8, 12)
        _qr(r, 1, 5, 9, 13)
        _qr(r, 2, 6, 10, 14)
        _qr(r, 3, 7, 11, 15)
        done += 1
        if done >= rounds:
            break
        # diagonal round
        _qr(r, 0, 5, 10, 15)
        _qr(r, 1, 6, 11, 12)
        _qr(r, 2, 7, 12, 13)
        _qr(r, 3, 4, 13, 14)
        done += 1
    for i in range(16):
        r[i] = (r[i] + e[i]) & 0xFFFFFFFF
    return r


def _spread(e):
    try:
        return list(e)
    except TypeError:
        raise TypeError("Invalid attempt to spread non-iterable instance.")


def _xor_stream(state, rounds: int, byte_arr: list) -> None:
    # byte_arr: list int 0..255
    n_full = len(byte_arr) // 4
    rem = len(byte_arr) % 4
    i_len = (len(byte_arr) + 3) // 4
    u = [0] * i_len

    for a in range(n_full):
        s = 4 * a
        u[a] = (
            byte_arr[s]
            | (byte_arr[s + 1] << 8)
            | (byte_arr[s + 2] << 16)
            | (byte_arr[s + 3] << 24)
        )
    if rem > 0:
        a = n_full
        u[a] = 0
        for c in range(rem):
            u[a] |= byte_arr[4 * a + c] << (8 * c)

    n_state = state[:]
    o = 0
    while o + 16 < len(u):
        block = _block(n_state, rounds)
        _inc_counter(n_state)
        for j in range(16):
            u[o + j] ^= block[j]
        o += 16

    a_rem = len(u) - o
    block = _block(n_state, rounds)
    for c in range(a_rem):
        u[o + c] ^= block[c]

    for a in range(n_full):
        f = 4 * a
        v = u[a]
        byte_arr[f] = v & 0xFF
        byte_arr[f + 1] = (v >> 8) & 0xFF
        byte_arr[f + 2] = (v >> 16) & 0xFF
        byte_arr[f + 3] = (v >> 24) & 0xFF
    if rem > 0:
        a = n_full
        for d in range(rem):
            byte_arr[4 * a + d] = (u[a] >> (8 * d)) & 0xFF


def _enc_block(key_elems, rounds: int, s: str) -> str:
    state = Ot + _spread(key_elems)
    n = [ord(ch) for ch in s]
    _xor_stream(state, rounds, n)
    return "".join(chr(c) for c in n)


def _num_to_uint8_array(value: int) -> list[int]:
    if value < 255 * 255:
        b = value.to_bytes(2, "big", signed=False)
    else:
        b = value.to_bytes(4, "big", signed=False)
    return list(b)


def _rand() -> float:
    global St, kt
    rb0 = 4294967296
    rb1 = 4294965248
    rb2 = 53
    rb3 = 0
    rb4 = 2
    rb5 = 11
    rb6 = 8
    rb7 = 7
    e = _block(kt, rb6)
    t = e[St]
    r = (rb1 & e[St + rb6]) >> rb5
    if rb7 == St:
        _inc_counter(kt)
        St = rb3
    else:
        St += 1
    return (t + rb0 * r) / (rb4**rb2)


def encode(query_string: str, body: str, user_agent: str) -> str:
    obj: dict[int, object] = {}
    obj[1] = 1
    obj[2] = 0
    obj[3] = hashlib.md5(query_string.encode("utf-8")).hexdigest()
    obj[4] = hashlib.md5(body.encode("utf-8")).hexdigest()
    obj[5] = hashlib.md5(user_agent.encode("utf-8")).hexdigest()

    timestamp_ms = _now_ms()
    obj[6] = timestamp_ms // 1000
    obj[7] = 1245783967
    obj[8] = (timestamp_ms * 1000) % 2147483648
    obj[9] = "5.1.0"
    obj[0] = obj[6] ^ obj[7] ^ obj[8] ^ obj[1] ^ obj[2]

    arr: list[int] = [len(obj)]
    for key in sorted(obj.keys()):
        val = obj[key]
        arr.append(int(key))
        if isinstance(val, (int, float)):
            val_arr = _num_to_uint8_array(int(val))
            len_arr = _num_to_uint8_array(len(val_arr))
        else:
            vb = str(val).encode("utf-8")
            val_arr = list(vb)
            len_arr = _num_to_uint8_array(len(val_arr))
        arr.extend(len_arr)
        arr.extend(val_arr)

    s = "".join(chr(b & 0xFF) for b in arr)

    some_random_char = chr(((1 << 6) ^ (1 << 3) ^ 3) & 0xFF)  # 'K'

    key = []
    key_bytes = []
    rounds = 0
    for _ in range(12):
        num = math.floor((2**32) * _rand()) & 0xFFFFFFFF
        key.append(num)
        rounds = ((num & 15) + rounds) & 15
        key_bytes.extend(
            [(num >> 0) & 255, (num >> 8) & 255, (num >> 16) & 255, (num >> 24) & 255]
        )
    rounds += 5

    x = _enc_block(key, rounds, s)

    some_val = 0
    for el in key_bytes:
        some_val = (some_val + el) % (len(x) + 1)
    for ch in x:
        some_val = (some_val + ord(ch)) % (len(x) + 1)

    key_str = "".join(chr(b) for b in key_bytes)
    s2 = some_random_char + x[:some_val] + key_str + x[some_val:]

    char_set = "u09tbS3UvgDEe6r-ZVMXzLpsAohTn7mdINQlW412GqBjfYiyk8JORCF5/xKHwacP="
    res = ""
    for i in range(3, len(s2) + 1, 3):
        val = (
            ((ord(s2[i - 3]) & 255) << 16)
            | ((ord(s2[i - 2]) & 255) << 8)
            | (ord(s2[i - 1]) & 255)
        )
        res += char_set[(val & 16515072) >> 18]
        res += char_set[(val & 258048) >> 12]
        res += char_set[(val & 4032) >> 6]
        res += char_set[(val & 63) >> 0]
    return res
