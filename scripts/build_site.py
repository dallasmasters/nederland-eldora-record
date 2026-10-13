"""Build the public website in docs/ (served by GitHub Pages) from the generated page in analysis/.

The analysis/*.html files are written for Claude's artifact viewer, which supplies the <!doctype>, <head> and a
small reset when it publishes. This script adds those so the pages stand alone, swaps any artifact links for relative
links, and adds the "last updated" line. It also writes docs/feed.xml, an Atom feed of the page's corrections and
updates (analysis/changes.json), so readers can follow changes in a feed reader.

Settings live in site_config.json (contact for corrections, optional public URL).
"""
import html
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from preview_diff import switchable  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'docs')
PAGES = [
    # source, output, artifact URL that other pages use to link to it, description for link previews
    ('eldora_spending.html', 'index.html', 'https://claude.ai/artifact/Y4wMfdqjojbxu6PBCwTLpn',
     'What the Town of Nederland has paid toward the Eldora Mountain Resort acquisition, where the money comes from, '
     'and how every Board of Trustees vote on the purchase went, drawn from Town records.'),
    ('opinion.html', 'opinion.html', 'https://eldorarecord.org/opinion.html',
     "Dallas Masters's opinions on the Town of Nederland's Eldora Mountain Resort purchase, kept separate from the "
     'Eldora Record, which is drawn only from Town records and official sources.'),
]
# Addresses from earlier versions of the site that now forward to the combined page
REDIRECTS = {'spending.html': 'index.html'}
# The artifact viewer's skeleton reset, reproduced so the pages look the same off claude.ai
RESET = ('<style>:root{color-scheme:light;padding-top:env(safe-area-inset-top,0px);'
         'padding-bottom:env(safe-area-inset-bottom,0px)}body{margin:0;font:14px/1.5 system-ui,-apple-system,'
         '"Segoe UI",Roboto,sans-serif;background:#fafafa}img{max-width:100%}[hidden]{display:none!important}</style>')


FEED = 'feed.xml'
FEED_TITLE = "Nederland Eldora Record: corrections and updates"


def first_sentence(text, limit=140):
    plain = ' '.join(html.unescape(re.sub(r'<[^>]+>', '', text)).split())
    m = re.match(r'(.+?[.!?])(\s|$)', plain)
    s = m.group(1) if m else plain
    return s if len(s) <= limit else s[:limit - 1].rsplit(' ', 1)[0] + '\u2026'


def feed(cfg):
    """Atom feed of analysis/changes.json, newest first. Each entry's id is its date and its order among that date's
    entries (entries are only ever appended), so editing an entry's text doesn't make it look new."""
    site = cfg.get('base_url', 'https://eldorarecord.org/').rstrip('/') + '/'
    entries = json.load(open(os.path.join(ROOT, 'analysis', 'changes.json')))
    seq, items = {}, []
    for c in entries:
        seq[c['date']] = seq.get(c['date'], 0) + 1
        items.append((c['date'], seq[c['date']], c))
    items.sort(key=lambda x: (x[0], x[1]), reverse=True)
    esc = html.escape
    out = ['<?xml version="1.0" encoding="utf-8"?>',
           '<feed xmlns="http://www.w3.org/2005/Atom">',
           f'  <title>{esc(FEED_TITLE)}</title>',
           f'  <subtitle>Corrections and updates to {esc(site)}, an independent compilation of Town of Nederland '
           'records on the Eldora Mountain Resort acquisition.</subtitle>',
           f'  <link rel="alternate" type="text/html" href="{esc(site)}"/>',
           f'  <link rel="self" type="application/atom+xml" href="{esc(site + FEED)}"/>',
           f'  <id>{esc(site + FEED)}</id>',
           f'  <updated>{items[0][0]}T00:00:00Z</updated>' if items else '',
           f'  <author><name>Dallas Masters</name><uri>{esc(site)}</uri></author>']
    for day, n, c in items:
        title = f"{c['type']}: {c.get('headline') or first_sentence(c['text'])}"
        body = re.sub(r'href="#', f'href="{site}#', c['text'])   # page anchors become full links
        out += ['  <entry>',
                f'    <title>{esc(title)}</title>',
                f'    <id>{esc(site)}#change-{day}-{n}</id>',
                f'    <link rel="alternate" type="text/html" href="{esc(site)}#changes"/>',
                f'    <updated>{day}T00:00:00Z</updated>',
                f'    <content type="html">{esc(body)}</content>',
                '  </entry>']
    out.append('</feed>')
    with open(os.path.join(OUT, FEED), 'w') as f:
        f.write('\n'.join(x for x in out if x) + '\n')
    return len(items)


def config():
    path = os.path.join(ROOT, 'site_config.json')
    return json.load(open(path)) if os.path.exists(path) else {}


def build(src, out, desc, cfg):
    body = open(os.path.join(ROOT, 'analysis', src)).read()
    # "Show what changed" switch: marks against the version before the latest major update (private/)
    if out == 'index.html':
        body = switchable(body)
    title = re.search(r'<title>(.*?)</title>', body).group(1)
    for _, other_out, url, _ in PAGES:
        body = body.replace(url, other_out)
    # links between our own pages open in the same tab on the website
    body = re.sub(r'<a href="(index|spending)\.html" target="_blank" rel="noopener">', r'<a href="\1.html">', body)
    style = ('<style>.updated{margin:0;font-size:13px;color:var(--muted)}'
             '.contact{margin-top:6px}</style>')
    if cfg.get('contact'):
        addr = html.escape(cfg['contact'])
        body = body.replace('</footer>', f' <span class="contact">Corrections: <a href="mailto:{addr}">{addr}</a></span></footer>', 1)
    head = [f'<meta charset="utf-8">',
            '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">',
            f'<meta name="description" content="{html.escape(desc)}">',
            f'<meta property="og:title" content="{html.escape(title)}">',
            f'<meta property="og:description" content="{html.escape(desc)}">',
            '<meta property="og:type" content="article">',
            f'<link rel="alternate" type="application/atom+xml" title="{html.escape(FEED_TITLE)}" href="{FEED}">']
    if cfg.get('base_url'):
        url = cfg['base_url'].rstrip('/') + '/' + ('' if out == 'index.html' else out)
        head += [f'<link rel="canonical" href="{url}">', f'<meta property="og:url" content="{url}">']
        if os.path.exists(os.path.join(OUT, 'preview.png')):   # social-card image, made by make_preview.py
            img = cfg['base_url'].rstrip('/') + '/preview.png'
            head += [f'<meta property="og:image" content="{img}">',
                     '<meta property="og:image:width" content="1200">',
                     '<meta property="og:image:height" content="630">',
                     '<meta property="og:image:alt" content="Nederland\'s Eldora acquisition: summary, costs, and where '
                     'the money is coming from. Independent citizen research at eldorarecord.org.">',
                     '<meta name="twitter:card" content="summary_large_image">',
                     f'<meta name="twitter:image" content="{img}">']
    page = ('<!doctype html>\n<html lang="en">\n<head>\n' + '\n'.join(head) + '\n' + RESET + style +
            '\n</head>\n<body>\n' + body + '\n</body>\n</html>\n')
    with open(os.path.join(OUT, out), 'w') as f:
        f.write(page)
    return title


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    open(os.path.join(OUT, '.nojekyll'), 'w').close()  # serve files as-is, no Jekyll processing
    cfg = config()
    for src, out, _, desc in PAGES:
        print(f'docs/{out}: {build(src, out, desc, cfg)}')
    print(f'docs/{FEED}: {feed(cfg)} entries')
    for old, new in REDIRECTS.items():
        with open(os.path.join(OUT, old), 'w') as f:
            f.write(f'<!doctype html>\n<meta charset="utf-8">\n<title>Moved</title>\n'
                    f'<meta http-equiv="refresh" content="0; url={new}">\n<link rel="canonical" href="{new}">\n'
                    f'<p>This page has moved to <a href="{new}">{new}</a>.</p>\n')
        print(f'docs/{old}: redirect to {new}')
    if cfg.get('base_url'):
        domain = re.sub(r'^https?://', '', cfg['base_url']).split('/')[0]
        if not domain.endswith('github.io'):
            open(os.path.join(OUT, 'CNAME'), 'w').write(domain + '\n')
