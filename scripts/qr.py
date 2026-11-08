"""QR Code (ISO/IEC 18004 Model 2) encoder.

Supported: versions 1-20, ECC levels L/M/Q/H, byte mode with UTF-8.
Not supported: alphanumeric, numeric, kanji, ECI, structured append, versions 21-40.
UTF-8 byte mode is read without an ECI header by all modern phone cameras.
"""

# ---------- Tables ----------

_ECC_I = {"L": 0, "M": 1, "Q": 2, "H": 3}
_ECC_BITS = (0b01, 0b00, 0b11, 0b10)  # format indicator bits: L, M, Q, H

# Data codeword capacity: _DCAP[version-1][ecc_index]
_DCAP = [
    [19,16,13,9],[34,28,22,16],[55,44,34,26],[80,64,48,36],
    [108,86,62,46],[136,108,76,60],[156,124,88,66],[194,154,110,86],
    [232,182,132,100],[274,216,154,122],[324,254,180,140],[370,290,206,158],
    [428,334,244,180],[461,365,261,197],[523,415,295,223],[589,453,325,253],
    [647,507,367,283],[721,563,397,313],[795,627,445,341],[861,669,485,385],
]

# EC block info compact: (ec_per_block, count1, data1[, count2, data2])
# _ECB_RAW[version-1][ecc_index]
_ECB_RAW = [
    [(7,1,19),(10,1,16),(13,1,13),(17,1,9)],
    [(10,1,34),(16,1,28),(22,1,22),(28,1,16)],
    [(15,1,55),(26,1,44),(18,2,17),(22,2,13)],
    [(20,1,80),(18,2,32),(26,2,24),(16,4,9)],
    [(26,1,108),(24,2,43),(18,2,15,2,16),(22,2,11,2,12)],
    [(18,2,68),(16,4,27),(24,4,19),(28,4,15)],
    [(20,2,78),(18,4,31),(18,2,14,4,15),(26,4,13,1,14)],
    [(24,2,97),(22,2,38,2,39),(22,4,18,2,19),(26,4,14,2,15)],
    [(30,2,116),(22,3,36,2,37),(20,4,16,4,17),(24,4,12,4,13)],
    [(18,2,68,2,69),(26,4,43,1,44),(24,6,19,2,20),(28,6,15,2,16)],
    [(20,4,81),(30,1,50,4,51),(28,4,22,4,23),(24,3,12,8,13)],
    [(24,2,92,2,93),(22,6,36,2,37),(26,4,20,6,21),(28,7,14,4,15)],
    [(26,4,107),(22,8,37,1,38),(24,8,20,4,21),(22,12,11,4,12)],
    [(30,3,115,1,116),(24,4,40,5,41),(20,11,16,5,17),(24,11,12,5,13)],
    [(22,5,87,1,88),(24,5,41,5,42),(30,5,24,7,25),(24,11,12,7,13)],
    [(24,5,98,1,99),(28,7,45,3,46),(24,15,19,2,20),(30,3,15,13,16)],
    [(28,1,107,5,108),(28,10,46,1,47),(28,1,22,15,23),(28,2,14,17,15)],
    [(30,5,120,1,121),(26,9,43,4,44),(28,17,22,1,23),(28,2,14,19,15)],
    [(28,3,113,4,114),(26,3,44,11,45),(26,17,21,4,22),(26,9,13,16,14)],
    [(28,3,107,5,108),(26,3,41,13,42),(30,15,24,5,25),(28,15,15,10,16)],
]

# Alignment pattern positions per version (row/col values; all combinations minus finder corners)
_ALIGN = [
    [], [6,18], [6,22], [6,26], [6,30], [6,34],
    [6,22,38], [6,24,42], [6,26,46], [6,28,50],
    [6,30,54], [6,32,58], [6,34,62], [6,26,46,66],
    [6,26,48,70], [6,26,50,74], [6,30,54,78], [6,30,56,82],
    [6,30,58,86], [6,34,62,90],
]

# Remainder bits appended after codewords, indexed by version-1
_REM = [0, 7,7,7,7,7, 0,0,0,0,0,0,0, 3,3,3,3,3,3,3]

def _ecb(version, ei):
    t = _ECB_RAW[version - 1][ei]
    grps = [(t[1], t[2])]
    if len(t) > 3:
        grps.append((t[3], t[4]))
    return t[0], grps

# ---------- GF(256) over x^8+x^4+x^3+x^2+1 ----------

_EXP = [0] * 512
_LOG = [0] * 256
_v = 1
for _i in range(255):
    _EXP[_i] = _v
    _LOG[_v] = _i
    _v <<= 1
    if _v & 0x100:
        _v ^= 0x11D
for _i in range(255, 512):
    _EXP[_i] = _EXP[_i - 255]
del _v, _i


def _gmul(a, b):
    return 0 if (a == 0 or b == 0) else _EXP[_LOG[a] + _LOG[b]]


def _rs_gen(n):
    """Degree-n generator polynomial, big-endian: [gn=1, g_{n-1}, ..., g0]."""
    g = [1]
    for i in range(n):
        ng = [0] * (len(g) + 1)
        for j, c in enumerate(g):
            ng[j] ^= c
            ng[j + 1] ^= _gmul(c, _EXP[i])
        g = ng
    return g


def _rs_enc(data, n_ec):
    """Return n_ec EC codewords for data (list of ints 0-255)."""
    g = _rs_gen(n_ec)
    r = list(data) + [0] * n_ec
    for i in range(len(data)):
        c = r[i]
        if c:
            for j, gc in enumerate(g):
                r[i + j] ^= _gmul(c, gc)
    return r[len(data):]

# ---------- BCH ----------

def _bch_fmt(d5):
    """10-bit BCH remainder for 5-bit format info (generator 0x537)."""
    d = d5 << 10
    for i in range(14, 9, -1):
        if (d >> i) & 1:
            d ^= 0x537 << (i - 10)
    return d & 0x3FF


def _fmt_info(ei, mask_num):
    """15-bit format information word (XOR-masked)."""
    d = (_ECC_BITS[ei] << 3) | mask_num
    return ((d << 10) | _bch_fmt(d)) ^ 0x5412


def _ver_info(version):
    """18-bit version information for version >= 7 (generator 0x1F25)."""
    d = version << 12
    for i in range(17, 11, -1):
        if (d >> i) & 1:
            d ^= 0x1F25 << (i - 12)
    return (version << 12) | (d & 0xFFF)

# ---------- Data encoding ----------

def _encode_data(payload, version, ei):
    """Return list of data codewords for payload (bytes)."""
    cap = _DCAP[version - 1][ei]
    nb = len(payload)
    count_bits = 8 if version <= 9 else 16

    bits = []
    def push(val, n):
        for sh in range(n - 1, -1, -1):
            bits.append((val >> sh) & 1)

    push(0b0100, 4)
    push(nb, count_bits)
    for b in payload:
        push(b, 8)
    term = min(4, cap * 8 - len(bits))
    push(0, term)
    while len(bits) % 8:
        bits.append(0)

    cws = []
    for i in range(0, len(bits), 8):
        byte = 0
        for j in range(8):
            byte = (byte << 1) | bits[i + j]
        cws.append(byte)

    pads = [0xEC, 0x11]
    pi = 0
    while len(cws) < cap:
        cws.append(pads[pi & 1])
        pi += 1
    return cws[:cap]


def _interleave(data_cws, version, ei):
    """Interleave data and EC codewords across all blocks."""
    ec_per_block, groups = _ecb(version, ei)
    blocks = []
    pos = 0
    for count, k in groups:
        for _ in range(count):
            d = data_cws[pos:pos + k]
            blocks.append((d, _rs_enc(d, ec_per_block)))
            pos += k

    out = []
    max_d = max(len(d) for d, _ in blocks)
    for i in range(max_d):
        for d, _ in blocks:
            if i < len(d):
                out.append(d[i])
    for i in range(ec_per_block):
        for _, ec in blocks:
            out.append(ec[i])
    return out

# ---------- Matrix helpers ----------

def _new_mat(n):
    return [[None] * n for _ in range(n)], [[False] * n for _ in range(n)]


def _sfn(m, f, r, c, v):
    m[r][c] = v
    f[r][c] = True


def _finder(m, f, r, c):
    pat = [0b1111111, 0b1000001, 0b1011101, 0b1011101, 0b1011101, 0b1000001, 0b1111111]
    for dr in range(7):
        for dc in range(7):
            _sfn(m, f, r + dr, c + dc, bool((pat[dr] >> (6 - dc)) & 1))


def _finders(m, f, n):
    for fr, fc in [(0, 0), (0, n - 7), (n - 7, 0)]:
        _finder(m, f, fr, fc)
    # Separators: TL
    for i in range(8):
        _sfn(m, f, 7, i, False)
        _sfn(m, f, i, 7, False)
    # TR
    for i in range(8):
        _sfn(m, f, 7, n - 8 + i, False)
        _sfn(m, f, i, n - 8, False)
    # BL
    for i in range(8):
        _sfn(m, f, n - 8, i, False)
        _sfn(m, f, n - 8 + i, 7, False)


def _timing(m, f, n):
    for i in range(8, n - 8):
        _sfn(m, f, 6, i, i % 2 == 0)
        _sfn(m, f, i, 6, i % 2 == 0)


def _alignment(m, f, n, version):
    pos = _ALIGN[version - 1]
    for r in pos:
        for c in pos:
            if f[r][c]:
                continue
            for dr in range(-2, 3):
                for dc in range(-2, 3):
                    dark = abs(dr) == 2 or abs(dc) == 2 or (dr == 0 and dc == 0)
                    _sfn(m, f, r + dr, c + dc, dark)


def _reserve_fmt(m, f, n):
    def mark(r, c, v=False):
        m[r][c] = v; f[r][c] = True
    # Vertical strip: col 8, rows 0-5, 7, 8 (TL area) + rows 14..n-1 (BL area)
    for i in range(6):
        mark(i, 8)
    mark(7, 8); mark(8, 8)
    for i in range(8, 15):
        mark(n - 15 + i, 8)   # rows n-7..n-1 (14..20 for v1)
    # Horizontal strip: row 8, cols n-1..n-8 (TR area) + col 7 + cols 5..0 (TL area)
    for i in range(8):
        mark(8, n - 1 - i)    # cols n-1..n-8 (20..13 for v1)
    mark(8, 7)
    for i in range(9, 15):
        mark(8, 15 - i - 1)   # cols 5..0
    # Dark module always dark (also a function module)
    m[n - 8][8] = True
    f[n - 8][8] = True


def _reserve_ver(m, f, n, version):
    if version < 7:
        return
    for i in range(18):
        r, c = i // 3, n - 11 + i % 3
        m[r][c] = False; f[r][c] = True
        m[c][r] = False; f[c][r] = True


def _place_fmt(m, n, fi):
    def b(i):
        return bool((fi >> i) & 1)

    # Vertical strip (col 8): bit i at row i (0-5), bit 6 at row 7, bit 7 at row 8,
    # then bits 8-14 at rows n-7..n-1
    for i in range(6):
        m[i][8] = b(i)
    m[7][8] = b(6)
    m[8][8] = b(7)
    for i in range(8, 15):
        m[n - 15 + i][8] = b(i)   # rows 14..20 for v1

    # Horizontal strip (row 8): bits 0-7 at cols n-1..n-8 (MSB leftward),
    # bit 8 at col 7, bits 9-14 at cols 5..0 (MSB rightward)
    for i in range(8):
        m[8][n - 1 - i] = b(i)
    m[8][7] = b(8)
    for i in range(9, 15):
        m[8][15 - i - 1] = b(i)   # cols 5..0

    m[n - 8][8] = True  # dark module always dark


def _place_ver(m, n, version):
    if version < 7:
        return
    vi = _ver_info(version)
    for i in range(18):
        bit = bool((vi >> i) & 1)
        r, c = i // 3, n - 11 + i % 3
        m[r][c] = bit
        m[c][r] = bit


def _place_data(m, f, n, bits):
    idx = 0
    going_up = True
    right = n - 1
    while right >= 1:
        if right == 6:
            right -= 1
        rows = range(n - 1, -1, -1) if going_up else range(n)
        for row in rows:
            for col in (right, right - 1):
                if not f[row][col]:
                    m[row][col] = bool(bits[idx]) if idx < len(bits) else False
                    idx += 1
        going_up = not going_up
        right -= 2

# ---------- Masking ----------

_MASKS = [
    lambda r, c: (r + c) % 2 == 0,
    lambda r, c: r % 2 == 0,
    lambda r, c: c % 3 == 0,
    lambda r, c: (r + c) % 3 == 0,
    lambda r, c: (r // 2 + c // 3) % 2 == 0,
    lambda r, c: (r * c) % 2 + (r * c) % 3 == 0,
    lambda r, c: ((r * c) % 2 + (r * c) % 3) % 2 == 0,
    lambda r, c: ((r + c) % 2 + (r * c) % 3) % 2 == 0,
]


def _apply_mask(m, f, n, mn):
    fn = _MASKS[mn]
    for r in range(n):
        for c in range(n):
            if not f[r][c] and fn(r, c):
                m[r][c] = not m[r][c]


def _score(m, n):
    s = 0
    p1 = [1, 0, 1, 1, 1, 0, 1, 0, 0, 0, 0]
    p2 = [0, 0, 0, 0, 1, 0, 1, 1, 1, 0, 1]

    for line in list(m) + [[m[r][c] for r in range(n)] for c in range(n)]:
        run = 1
        for i in range(1, n):
            if line[i] == line[i - 1]:
                run += 1
                if run == 5:
                    s += 3
                elif run > 5:
                    s += 1
            else:
                run = 1
        seg = [int(x) for x in line]
        for k in range(n - 10):
            chunk = seg[k:k + 11]
            if chunk == p1 or chunk == p2:
                s += 40

    for r in range(n - 1):
        for c in range(n - 1):
            v = m[r][c]
            if v == m[r][c + 1] == m[r + 1][c] == m[r + 1][c + 1]:
                s += 3

    dark = sum(m[r][c] for r in range(n) for c in range(n))
    s += (abs(dark * 100 // (n * n) - 50) // 5) * 10
    return s

# ---------- Public API ----------

def version_for(data, ecc="M"):
    """Return the smallest version (1-20) that fits data at the given ECC level.

    Raises ValueError if data is too long for version 20.
    """
    if isinstance(data, str):
        data = data.encode("utf-8")
    ei = _ECC_I[ecc.upper()]
    nb = len(data)
    for v in range(1, 21):
        cb = 8 if v <= 9 else 16
        if 4 + cb + nb * 8 <= _DCAP[v - 1][ei] * 8:
            return v
    raise ValueError(f"Data ({nb} bytes) too long for versions 1-20 at ECC {ecc}")


def matrix(data, ecc="M", force_mask=-1):
    """Return square list[list[bool]] (True=dark, no quiet zone).

    force_mask (0-7) skips best-mask selection; used for testing.
    """
    if isinstance(data, str):
        data = data.encode("utf-8")
    ei = _ECC_I[ecc.upper()]
    version = version_for(data, ecc)
    n = 4 * version + 17

    cws = _interleave(_encode_data(data, version, ei), version, ei)
    bits = []
    for cw in cws:
        for sh in range(7, -1, -1):
            bits.append((cw >> sh) & 1)
    bits += [0] * _REM[version - 1]

    m, f = _new_mat(n)
    _finders(m, f, n)
    _alignment(m, f, n, version)  # must run before timing so shared cells go to timing
    _timing(m, f, n)
    _reserve_fmt(m, f, n)
    _reserve_ver(m, f, n, version)
    _place_data(m, f, n, bits)

    if force_mask >= 0:
        best = force_mask
    else:
        best, best_s = 0, 10 ** 9
        for mn in range(8):
            mc = [row[:] for row in m]
            _apply_mask(mc, f, n, mn)
            s = _score(mc, n)
            if s < best_s:
                best_s, best = s, mn

    _apply_mask(m, f, n, best)
    _place_fmt(m, n, _fmt_info(ei, best))
    _place_ver(m, n, version)
    return m


def svg(data, ecc="M", border=4, dark="#000", light="#fff"):
    """Return a small standalone SVG string for data."""
    if isinstance(data, str):
        data = data.encode("utf-8")
    m = matrix(data, ecc)
    n = len(m)
    sz = n + 2 * border
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {sz} {sz}"'
             f' style="background:{light}"><g fill="{dark}">']
    for r in range(n):
        for c in range(n):
            if m[r][c]:
                parts.append(f'<rect x="{c + border}" y="{r + border}" width="1" height="1"/>')
    parts.append("</g></svg>")
    return "".join(parts)
