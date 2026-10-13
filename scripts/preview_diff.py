"""Mark what changed between two versions of the page.

    python3 scripts/preview_diff.py OLD.html NEW.html OUT.html      review copy: changes always shown
    python3 scripts/preview_diff.py --set-baseline                  start a new "Show what changed" comparison
    python3 scripts/preview_diff.py --mirror OUT.html               the page with the switch, for the artifact copy

Review copy: OLD is the live page (normally `git show main:analysis/eldora_spending.html`), NEW the preview build.
OUT is NEW with added text highlighted, removed text struck through, and a panel for stepping through the changes.
It is for review only and is never published.

Live page: build_site.py calls switchable() to compare the page with the baseline kept in private/ (the version
before the latest major update) and adds a "Show what changed" switch to the latest-update notice. The marks are
hidden until a reader turns them on. --set-baseline copies the live version (main) to the baseline; run it on the
preview branch of each major update, before building, so the switch then shows that update's changes (and any minor
updates after it). The baseline stays in private/ and is never published as a page.

Charts (SVG), styles, and scripts are compared but never marked.
"""
import difflib
import html
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASELINE = os.path.join(ROOT, 'private', 'changes-baseline.html')
BASELINE_INFO = os.path.join(ROOT, 'private', 'changes-baseline.json')

TOKEN = re.compile(r'<[^>]+>|[^<\s]+|\s+')
SKIP = ('svg', 'style', 'script', 'title', 'head')

COLORS = '''ins.pv-add {{ background: #fff1a8; color: inherit; text-decoration: none; box-shadow: 0 0 0 2px #fff1a8; border-radius: 2px; }}
del.pv-del {{ background: #fbd5d5; color: #7a1f1f; text-decoration: line-through; border-radius: 2px; }}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) ins.pv-add {{ background: #5c4d00; box-shadow: 0 0 0 2px #5c4d00; }}
  :root:not([data-theme="light"]) del.pv-del {{ background: #5a1e1e; color: #ffd0d0; }} }}
:root[data-theme="dark"] ins.pv-add {{ background: #5c4d00; box-shadow: 0 0 0 2px #5c4d00; }}
:root[data-theme="dark"] del.pv-del {{ background: #5a1e1e; color: #ffd0d0; }}
pv-rep {{ white-space: normal; overflow-wrap: anywhere; line-height: 1.35; }}'''

PANEL_CSS = '''.pv-cur {{ outline: 3px solid #e07b00; outline-offset: 2px; }}
#pv-panel {{ position: fixed; right: 12px; bottom: calc(12px + env(safe-area-inset-bottom, 0px)); z-index: 99; display: flex; gap: 8px;
  align-items: center; padding: 8px 10px; font: 13px system-ui, sans-serif; background: #222; color: #fff; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,.3); }}
#pv-panel button {{ font: inherit; padding: 3px 9px; border-radius: 5px; border: 1px solid #888; background: #333; color: #fff; cursor: pointer; }}'''

# Live page: marks are inert (removed text hidden, added text unstyled) until the reader turns them on.
SWITCH_CSS = '''del.pv-del {{ display: none; }}
ins.pv-add {{ text-decoration: none; color: inherit; }}
#pv-panel[hidden] {{ display: none; }}
button.pv-toggle {{ font: inherit; color: var(--accent); background: none; border: 0; padding: 0; text-decoration: underline; cursor: pointer; }}
html.pv-on del.pv-del {{ display: inline; }}
'''

STEP_JS = '''
  var marks = Array.prototype.slice.call(document.querySelectorAll('ins.pv-add, del.pv-del'));
  var groups = [];
  marks.forEach(function (m) {
    var last = groups[groups.length - 1];
    var block = m.closest('p, li, tr, h1, h2, h3, dd, dt, div');
    if (last && last.block === block) last.els.push(m); else groups.push({ block: block, els: [m] });
  });
  var i = -1, n = document.getElementById('pv-n');
  function count() { n.textContent = LABEL(groups.length); }
  function go(d) {
    if (!groups.length) return;
    if (i >= 0) groups[i].els.forEach(function (e) { e.classList.remove('pv-cur'); });
    i = (i + d + groups.length) % groups.length;
    var g = groups[i];
    for (var p = g.els[0].parentElement; p; p = p.parentElement) if (p.tagName === 'DETAILS') p.open = true;
    g.els.forEach(function (e) { e.classList.add('pv-cur'); });
    g.els[0].scrollIntoView({ block: 'center', behavior: 'smooth' });
    n.textContent = (i + 1) + ' of ' + groups.length;
  }
  document.getElementById('pv-next').onclick = function () { go(1); };
  document.getElementById('pv-prev').onclick = function () { go(-1); };
'''


def tokens(doc):
    """Split into tags, words, and whitespace, flagging tokens inside elements that are never marked."""
    out, depth = [], {t: 0 for t in SKIP}
    for tok in TOKEN.findall(doc):
        m = re.match(r'<(/?)([a-zA-Z0-9]+)', tok)
        if m and m.group(2).lower() in SKIP and not tok.endswith('/>'):
            depth[m.group(2).lower()] += -1 if m.group(1) else 1
        out.append((tok, any(depth.values()) or tok.startswith('<')))
    return out


def lines(toks):
    """Group tokens into source lines (split after whitespace that contains a newline), for a fast first pass."""
    out, cur = [], []
    for t in toks:
        cur.append(t)
        if t[0].isspace() and '\n' in t[0]:
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    return out


def visible(text):
    return html.unescape(text).strip()


def coalesce(ops, b, short=3):
    """Fold short unchanged stretches (a few words, no tags) between two changes into one change, so a rewritten
    sentence reads as old text struck through followed by the new text, not alternating words."""
    ops = [list(o) for o in ops]
    for k in range(1, len(ops) - 1):
        op, i1, i2, j1, j2 = ops[k]
        if op == 'equal' and ops[k - 1][0] != 'equal' and ops[k + 1][0] != 'equal':
            seg = b[j1:j2]
            if not any(t.startswith('<') for t, _ in seg) and len([t for t, _ in seg if t.strip()]) <= short:
                ops[k][0] = 'replace'
    merged = []
    for o in ops:
        if merged and o[0] != 'equal' and merged[-1][0] != 'equal':
            merged[-1] = ['replace', merged[-1][1], o[2], merged[-1][3], o[4]]
        else:
            merged.append(o)
    return merged


def mark_tokens(a, b, out):
    sm = difflib.SequenceMatcher(None, [t for t, _ in a], [t for t, _ in b], autojunk=False)
    for op, i1, i2, j1, j2 in coalesce(sm.get_opcodes(), b):
        if op == 'equal':
            out.extend(t for t, _ in b[j1:j2])
            continue
        # Removed words go in one struck-through run; their tags are dropped so they can't break the page.
        gone = ''.join(t for t, fixed in a[i1:i2] if not fixed)
        inside_skip = any(fixed and not t.startswith('<') for t, fixed in b[j1:j2])
        # A replacement (old and new words with no tag between) goes in one group that may wrap, so the pair
        # stacks instead of overflowing figures and cells that don't wrap (the fact boxes, amount columns).
        lead = []
        while j1 < j2 and not b[j1][1]:
            lead.append(b[j1][0])
            j1 += 1
        lead = ''.join(lead)
        if visible(gone) and not inside_skip:
            if visible(lead):
                out.append(f'<pv-rep><del class="pv-del">{gone}</del> <ins class="pv-add">{lead}</ins></pv-rep>')
            else:
                out.append(f'<del class="pv-del">{gone}</del>' + lead)
        elif lead:
            out.append(f'<ins class="pv-add">{lead}</ins>' if visible(lead) else lead)
        run = []
        for t, fixed in b[j1:j2]:
            if fixed:
                if run:
                    out.append(f'<ins class="pv-add">{"".join(run)}</ins>' if visible(''.join(run)) else ''.join(run))
                    run = []
                out.append(t)
            else:
                run.append(t)
        if run:
            out.append(f'<ins class="pv-add">{"".join(run)}</ins>' if visible(''.join(run)) else ''.join(run))


def marks(old, new):
    """NEW with <ins>/<del> marks against OLD. Unchanged lines are matched first, then words within changed lines."""
    la, lb = lines(tokens(old)), lines(tokens(new))
    sm = difflib.SequenceMatcher(None, [tuple(t for t, _ in x) for x in la], [tuple(t for t, _ in x) for x in lb],
                                 autojunk=False)
    out = []
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == 'equal':
            out.extend(t for x in lb[j1:j2] for t, _ in x)
        else:
            mark_tokens([t for x in la[i1:i2] for t in x], [t for x in lb[j1:j2] for t in x], out)
    return ''.join(out)


def css(*parts):
    return '<style>\n' + '\n'.join(parts).replace('{{', '{').replace('}}', '}') + '\n</style>'


def review(old, new):
    """Review copy: every change shown, with a panel to step through them."""
    doc = marks(old, new)
    js = ('<div id="pv-panel" role="region" aria-label="Preview changes"><span id="pv-n"></span>'
          '<button type="button" id="pv-prev">Prev</button><button type="button" id="pv-next">Next</button></div>\n'
          '<script>\n(function () {\n  var LABEL = function (k) { return k + (k === 1 ? " change" : " changes"); };'
          + STEP_JS + '  count();\n})();\n</script>')
    doc = doc.replace('</style>', '</style>' + css(COLORS, PANEL_CSS), 1)
    return doc.replace('</main>', '</main>' + js, 1) if '</main>' in doc else doc + js


def switchable(new):
    """Live page: marks against the baseline, hidden until the reader clicks "Show what changed" in the notice.
    Returns NEW unchanged if there is no baseline or nothing to show."""
    if not os.path.exists(BASELINE):
        return new
    since = json.load(open(BASELINE_INFO)).get('label', 'the previous version') if os.path.exists(BASELINE_INFO) \
        else 'the previous version'
    doc = marks(open(BASELINE, encoding='utf-8').read(), new)
    if 'class="pv-add"' not in doc and 'class="pv-del"' not in doc:
        return new
    # The latest-update notice is new by definition, so it stays unmarked; the switch goes in it, before the
    # subscribe link.
    clean = re.search(r'<p class="latest">.*?</p>', new, re.S)
    if clean:
        doc = re.sub(r'<p class="latest">.*?</p>', lambda _: clean.group(0), doc, count=1, flags=re.S)
    m = re.search(r'<p class="latest">.*?(<a href="mailto:)', doc, re.S)
    if not m:
        return new
    button = '<button type="button" class="pv-toggle" aria-pressed="false">Show what changed</button> · '
    doc = doc[:m.start(1)] + button + doc[m.start(1):]
    js = ('<div id="pv-panel" role="region" aria-label="Changes to this page" hidden><span id="pv-n"></span>'
          '<button type="button" id="pv-prev">Prev</button><button type="button" id="pv-next">Next</button>'
          '<button type="button" id="pv-off">Hide</button></div>\n'
          '<script>\n(function () {\n  var SINCE = ' + json.dumps(f' since {since}') + ';\n'
          '  var LABEL = function (k) { return k + (k === 1 ? " change" : " changes") + SINCE; };' + STEP_JS +
          '''  var btn = document.querySelector('button.pv-toggle'), panel = document.getElementById('pv-panel');
  function set(on) {
    document.documentElement.classList.toggle('pv-on', on);
    panel.hidden = !on;
    btn.textContent = on ? 'Hide what changed' : 'Show what changed';
    btn.setAttribute('aria-pressed', on ? 'true' : 'false');
    if (on) { i = -1; count(); }
    else groups.forEach(function (g) { g.els.forEach(function (e) { e.classList.remove('pv-cur'); }); });
  }
  btn.onclick = function () { set(!document.documentElement.classList.contains('pv-on')); };
  document.getElementById('pv-off').onclick = function () { set(false); };
})();
</script>''')
    # Colors apply only while the switch is on; pv-rep wrapping too, so the page reads exactly as before when off.
    on = '\n'.join(('html.pv-on ' + ln if ln.startswith(('ins.', 'del.', 'pv-rep')) else ln)
                   for ln in COLORS.split('\n'))
    on = on.replace(':root:not([data-theme="light"]) ins', 'html.pv-on:not([data-theme="light"]) ins') \
           .replace(':root:not([data-theme="light"]) del', 'html.pv-on:not([data-theme="light"]) del') \
           .replace(':root[data-theme="dark"] ins', 'html.pv-on[data-theme="dark"] ins') \
           .replace(':root[data-theme="dark"] del', 'html.pv-on[data-theme="dark"] del')
    doc = doc.replace('</style>', '</style>' + css(SWITCH_CSS, on, PANEL_CSS), 1)
    return doc.replace('</main>', '</main>' + js, 1) if '</main>' in doc else doc + js


def set_baseline():
    """Make the live version (main) the comparison point for the live page's "Show what changed" switch."""
    page = subprocess.run(['git', 'show', 'main:analysis/eldora_spending.html'], cwd=ROOT, check=True,
                          capture_output=True, text=True).stdout
    changes = json.loads(subprocess.run(['git', 'show', 'main:analysis/changes.json'], cwd=ROOT, check=True,
                                        capture_output=True, text=True).stdout)
    last = max(c['date'] for c in changes)
    y, mo, dd = map(int, last.split('-'))
    month = ['Jan.', 'Feb.', 'March', 'April', 'May', 'June', 'July', 'Aug.', 'Sept.', 'Oct.', 'Nov.', 'Dec.'][mo - 1]
    os.makedirs(os.path.dirname(BASELINE), exist_ok=True)
    open(BASELINE, 'w', encoding='utf-8').write(page)
    json.dump({'date': last, 'label': f'the {month} {dd}, {y}, version'}, open(BASELINE_INFO, 'w'))
    print(f'baseline: live version of {last} -> {os.path.relpath(BASELINE, ROOT)}')


if __name__ == '__main__':
    if sys.argv[1:] == ['--set-baseline']:
        set_baseline()
        sys.exit()
    if sys.argv[1:2] == ['--mirror']:   # the page with the switch, for republishing the claude.ai artifact copy
        src = os.path.join(ROOT, 'analysis', 'eldora_spending.html')
        open(sys.argv[2], 'w', encoding='utf-8').write(switchable(open(src, encoding='utf-8').read()))
        sys.exit()
    old_path, new_path, out_path = sys.argv[1:4]
    result = review(open(old_path, encoding='utf-8').read(), open(new_path, encoding='utf-8').read())
    open(out_path, 'w', encoding='utf-8').write(result)
    print(f'{out_path}: {result.count("class=\"pv-add\"")} additions, {result.count("class=\"pv-del\"")} removals marked')
