"""Read cell values from an old-format Excel workbook (.xls, BIFF5/7 or BIFF8) without third-party libraries.

Town accounting exports arrive as .xls. This reads the OLE compound file, finds the Workbook (or Book) stream and
returns {sheet name: {(row, col): value}} for text and number cells, including cached formula results. Formatting,
dates and merged cells are not interpreted: dates come back as Excel serial numbers.
"""
import struct

END = 0xFFFFFFFA   # sector numbers at or above this end a chain


def cfb_stream(path, name):
    """Return the bytes of one stream from an OLE compound file."""
    b = open(path, 'rb').read()
    ssz = 1 << struct.unpack_from('<H', b, 30)[0]
    mssz = 1 << struct.unpack_from('<H', b, 32)[0]
    n_fat = struct.unpack_from('<I', b, 0x2C)[0]
    dir_start = struct.unpack_from('<I', b, 0x30)[0]
    cutoff = struct.unpack_from('<I', b, 0x38)[0]
    minifat_start = struct.unpack_from('<I', b, 0x3C)[0]
    difat_next, n_difat = struct.unpack_from('<II', b, 0x44)

    def sector(i):
        return b[512 + i * ssz: 512 + (i + 1) * ssz]

    difat = list(struct.unpack_from('<109I', b, 0x4C))
    for _ in range(n_difat):
        s = sector(difat_next)
        difat += struct.unpack_from(f'<{ssz // 4 - 1}I', s)
        difat_next = struct.unpack_from('<I', s, ssz - 4)[0]
    fat = []
    for i in difat[:n_fat]:
        fat += struct.unpack(f'<{ssz // 4}I', sector(i))

    def chain(start, table):
        while start < END:
            yield start
            start = table[start]

    directory = b''.join(sector(i) for i in chain(dir_start, fat))
    entries = []
    for o in range(0, len(directory), 128):
        e = directory[o:o + 128]
        name_len = struct.unpack_from('<H', e, 64)[0]
        entries.append((e[:max(name_len - 2, 0)].decode('utf-16le'), struct.unpack_from('<I', e, 116)[0],
                        struct.unpack_from('<Q', e, 120)[0] & 0xFFFFFFFF))
    root_start = entries[0][1]
    for entry_name, start, size in entries:
        if entry_name != name:
            continue
        if size >= cutoff:
            return b''.join(sector(i) for i in chain(start, fat))[:size]
        mini = b''.join(sector(i) for i in chain(root_start, fat))
        minifat = []
        for i in chain(minifat_start, fat):
            minifat += struct.unpack(f'<{ssz // 4}I', sector(i))
        return b''.join(mini[s * mssz:(s + 1) * mssz] for s in chain(start, minifat))[:size]
    return None


def _rk(v):
    """Decode an RK number (compressed integer or float)."""
    if v & 2:
        x = struct.unpack('<i', struct.pack('<I', v & 0xFFFFFFFC))[0] >> 2
    else:
        x = struct.unpack('<d', struct.pack('<Q', (v & 0xFFFFFFFC) << 32))[0]
    return x / 100 if v & 1 else x


def _records(w):
    o = 0
    while o + 4 <= len(w):
        t, n = struct.unpack_from('<HH', w, o)
        yield o, t, w[o + 4:o + 4 + n]
        o += 4 + n


def _sst(recs, i):
    """Decode the BIFF8 shared string table at record i, following CONTINUE records."""
    parts = [recs[i][2]]
    j = i + 1
    while j < len(recs) and recs[j][1] == 0x3C:
        parts.append(recs[j][2])
        j += 1
    pi, po = 0, 8
    out = []

    def take(k):
        nonlocal pi, po
        if po >= len(parts[pi]):
            pi, po = pi + 1, 0
        chunk = parts[pi][po:po + k]
        po += k
        return chunk

    for _ in range(struct.unpack_from('<I', parts[0], 4)[0]):
        count = struct.unpack('<H', take(2))[0]
        flags = take(1)[0]
        runs = struct.unpack('<H', take(2))[0] if flags & 8 else 0
        ext = struct.unpack('<I', take(4))[0] if flags & 4 else 0
        s, left, wide = '', count, flags & 1
        while left:
            if po >= len(parts[pi]):
                pi, po = pi + 1, 0
                wide = take(1)[0] & 1
            k = min(left, (len(parts[pi]) - po) // (2 if wide else 1))
            s += take(k * (2 if wide else 1)).decode('utf-16le' if wide else 'latin-1')
            left -= k
        for _ in range(runs * 4 + ext):
            take(1)
        out.append(s)
    return out


def read(path):
    w = cfb_stream(path, 'Workbook') or cfb_stream(path, 'Book')
    recs = list(_records(w))
    bof = recs[0][2]
    biff8 = len(bof) >= 16 and struct.unpack_from('<H', bof)[0] == 0x600

    def text(d, at, n):
        if biff8:
            wide = d[at] & 1
            return d[at + 1:at + 1 + n * (2 if wide else 1)].decode('utf-16le' if wide else 'latin-1')
        return d[at:at + n].decode('cp1252')

    sheets, sst = {}, []
    for i, (_, t, d) in enumerate(recs):
        if t == 0x85:   # BOUNDSHEET: stream offset of the sheet, then its name
            sheets[struct.unpack_from('<I', d)[0]] = text(d, 7, d[6]) if biff8 else d[7:7 + d[6]].decode('cp1252')
        elif t == 0xFC:
            sst = _sst(recs, i)
    out, cur, pending = {}, None, None
    for o, t, d in recs:
        if t == 0x809 and o in sheets:
            cur = out.setdefault(sheets[o], {})
        elif cur is None:
            continue
        elif t == 0xFD:   # LABELSST
            r, c = struct.unpack_from('<HH', d)
            cur[(r, c)] = sst[struct.unpack_from('<I', d, 6)[0]]
        elif t == 0x204:  # LABEL
            r, c = struct.unpack_from('<HH', d)
            cur[(r, c)] = text(d, 8, struct.unpack_from('<H', d, 6)[0])
        elif t == 0x203:  # NUMBER
            r, c = struct.unpack_from('<HH', d)
            cur[(r, c)] = struct.unpack_from('<d', d, 6)[0]
        elif t == 0x27E:  # RK
            r, c = struct.unpack_from('<HH', d)
            cur[(r, c)] = _rk(struct.unpack_from('<I', d, 6)[0])
        elif t == 0xBD:   # MULRK
            r, c = struct.unpack_from('<HH', d)
            for k in range((len(d) - 6) // 6):
                cur[(r, c + k)] = _rk(struct.unpack_from('<I', d, 6 + k * 6)[0])
        elif t == 0x06:   # FORMULA: cached result
            r, c = struct.unpack_from('<HH', d)
            v = d[6:14]
            if v[6:8] != b'\xff\xff':
                cur[(r, c)] = struct.unpack('<d', v)[0]
            elif v[0] == 0:
                pending = (r, c)   # string result follows in a STRING record
            elif v[0] == 1:
                cur[(r, c)] = bool(v[2])
        elif t == 0x207 and pending:   # STRING
            n = struct.unpack_from('<H', d)[0]
            cur[pending] = text(d, 2, n)
            pending = None
    return out


def rows(cells):
    """Yield (row number, [values]) for each non-empty row, with empty cells as ''."""
    if not cells:
        return
    width = max(c for _, c in cells) + 1
    for r in range(max(r for r, _ in cells) + 1):
        row = [cells.get((r, c), '') for c in range(width)]
        if any(v != '' for v in row):
            yield r, row
