"""Plain text from a Word 97-2003 (.doc) file, read from its piece table. Field codes (tables of contents, page
numbers) are dropped and runs of blank lines collapsed. Used by add_records.py for records the Town sends as .doc.
"""
import re
import struct

import olefile


def text(path):
    ole = olefile.OleFileIO(path)
    wd = ole.openstream('WordDocument').read()
    flags = struct.unpack_from('<H', wd, 0xA)[0]
    table = ole.openstream('1Table' if flags & 0x200 else '0Table').read()
    fc_clx, lcb_clx = struct.unpack_from('<II', wd, 0x1A2)
    clx = table[fc_clx:fc_clx + lcb_clx]
    i = 0
    while clx[i] == 1:                       # skip Prc (property modifiers)
        i += 3 + struct.unpack_from('<H', clx, i + 1)[0]
    lcb = struct.unpack_from('<I', clx, i + 1)[0]
    plc = clx[i + 5:i + 5 + lcb]
    n = (lcb - 4) // 12
    cps = struct.unpack_from(f'<{n + 1}I', plc, 0)
    out = []
    for k in range(n):
        fc = struct.unpack_from('<I', plc, 4 * (n + 1) + 8 * k + 2)[0]
        length = cps[k + 1] - cps[k]
        if fc & 0x40000000:                  # 8-bit text
            fc = (fc & 0x3FFFFFFF) // 2
            out.append(wd[fc:fc + length].decode('cp1252', 'replace'))
        else:
            out.append(wd[fc:fc + 2 * length].decode('utf-16le', 'replace'))
    t = ''.join(out)
    t = re.sub(r'\x13[^\x14\x15]*\x14?', '', t)   # field instructions; keep field results
    for a, b in (('\r', '\n'), ('\x07', '\t'), ('\x0b', '\n'), ('\x0c', '\n'), ('\x15', ''), ('\x01', ''),
                 ('\x08', ''), ('\x1e', '-'), ('\x1f', '')):
        t = t.replace(a, b)
    t = re.sub(r'[ \t]+', ' ', t)
    t = re.sub(r' *\n *', '\n', t)
    return re.sub(r'\n{2,}', '\n', t).strip()


def pages(path, size=4000):
    """Split into numbered text sections of about `size` characters at line breaks. These are not printed pages."""
    t, out = text(path), []
    while t:
        cut = len(t) if len(t) <= size else (t.rfind('\n', 0, size) + 1 or size)
        out.append({'n': len(out) + 1, 'text': t[:cut].strip(), 'ocr': False})
        t = t[cut:]
    return out
