#!/usr/bin/env python3
"""Writes the parts of the README of the profile that come from GitHub: the
list of the public gists, and the chart of the languages of the public
repositories (assets/, in a light and in a dark version). The README
keeps everything else; each generated part sits between the markers
<!-- NAME:start --> and <!-- NAME:end -->.

Usage: profile.py [README]
GITHUB_TOKEN, if set, is used for the requests to the API of GitHub.
"""

import json
import os
import re
import sys
import urllib.request
from xml.sax.saxutils import escape

USER = 'dmeoli'
API = 'https://api.github.com'

# repositories whose code is mostly of others (a fork kept up, a tap, a site)
SKIP_REPOS = {'lemon-ng', 'homebrew-lemon-ng', 'dmeoli.github.io', USER}
# languages whose bytes are not code written (outputs of notebooks, pages)
SKIP_LANGS = {'Jupyter Notebook', 'HTML', 'CSS', 'SCSS'}
TOP = 8

# the repositories of the section Software, one card each, in this order
CARDS = ['NeuroSAT', 'PESAD', 'lamalunga', 'WNAffect', 'FuzzyCLIPS',
         'SicilianNMT', 'code-style', 'lemon-ng', 'ADS', 'PBeFS']

# the colors of the languages, as GitHub shows them (linguist)
LANG_COLORS = {
    'C++': '#f34b7d', 'C': '#555555', 'Python': '#3572A5',
    'Jupyter Notebook': '#DA5B0B', 'Prolog': '#74283c', 'TeX': '#3D6117',
    'CLIPS': '#00A300', 'Java': '#b07219', 'Ruby': '#701516',
    'Shell': '#89e051', 'CMake': '#DA3434', 'HTML': '#e34c26',
}

# octicons (MIT), 16 x 16: repo, star, repo-forked
ICON_REPO = ('M2 2.5A2.5 2.5 0 0 1 4.5 0h8.75a.75.75 0 0 1 .75.75v12.5a.75.7'
             '5 0 0 1-.75.75h-2.5a.75.75 0 0 1 0-1.5h1.75v-2h-8a1 1 0 0 0-.7'
             '14 1.7.75.75 0 1 1-1.072 1.05A2.495 2.495 0 0 1 2 11.5Zm10.5-1'
             'h-8a1 1 0 0 0-1 1v6.708A2.486 2.486 0 0 1 4.5 9h8ZM5 12.25a.25'
             '.25 0 0 1 .25-.25h3.5a.25.25 0 0 1 .25.25v3.25a.25.25 0 0 1-.4'
             '.2l-1.45-1.087a.249.249 0 0 0-.3 0L5.4 15.7a.25.25 0 0 1-.4-.2'
             'Z')
ICON_STAR = ('M8 .25a.75.75 0 0 1 .673.418l1.882 3.815 4.21.612a.75.75 0 0 1'
             ' .416 1.279l-3.046 2.97.719 4.192a.751.751 0 0 1-1.088.791L8 1'
             '2.347l-3.766 1.98a.75.75 0 0 1-1.088-.79l.72-4.194L.818 6.374a'
             '.75.75 0 0 1 .416-1.28l4.21-.611L7.327.668A.75.75 0 0 1 8 .25Z'
             'm0 2.445L6.615 5.5a.75.75 0 0 1-.564.41l-3.097.45 2.24 2.184a.'
             '75.75 0 0 1 .216.664l-.528 3.084 2.769-1.456a.75.75 0 0 1 .698'
             ' 0l2.77 1.456-.53-3.084a.75.75 0 0 1 .216-.664l2.24-2.183-3.09'
             '6-.45a.75.75 0 0 1-.564-.41L8 2.694Z')
ICON_FORK = ('M5 5.372v.878c0 .414.336.75.75.75h4.5a.75.75 0 0 0 .75-.75v-.8'
             '78a2.25 2.25 0 1 1 1.5 0v.878a2.25 2.25 0 0 1-2.25 2.25h-1.5v2'
             '.128a2.251 2.251 0 1 1-1.5 0V8.5h-1.5A2.25 2.25 0 0 1 3.5 6.25'
             'v-.878a2.25 2.25 0 1 1 1.5 0ZM5 3.25a.75.75 0 1 0-1.5 0 .75.75'
             ' 0 0 0 1.5 0Zm6.75.75a.75.75 0 1 0 0-1.5.75.75 0 0 0 0 1.5Zm-3'
             ' 8.75a.75.75 0 1 0-1.5 0 .75.75 0 0 0 1.5 0Z')

# the motion: everything comes in once, and a light runs along the purple
# accent of the cards; none for whoever asked the system for less motion
MOTION = ('@keyframes rise{from{opacity:0;transform:translateY(6px)}'
          'to{opacity:1;transform:none}}'
          '@keyframes grow{from{transform:scaleX(0)}to{transform:scaleX(1)}}'
          '@keyframes draw{from{transform:scaleY(0)}to{transform:scaleY(1)}}'
          '@keyframes show{from{opacity:0}to{opacity:1}}'
          '@media (prefers-reduced-motion: reduce){*{animation:none!important'
          '}}')
FONT = ('text{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",'
        '"Noto Sans",Helvetica,Arial,sans-serif}')

THEMES = {
    'light': {'bar': '#7a52c0', 'text': '#1f2328', 'muted': '#59636e',
              'track': '#eae4f4', 'link': '#7a52c0', 'border': '#d1d9e0',
              'bg': '#ffffff', 'glow': ('#7a52c0', '#b39ddb', '#7a52c0')},
    'dark': {'bar': '#a98be0', 'text': '#e6edf3', 'muted': '#9198a1',
             'track': '#221c2e', 'link': '#a98be0', 'border': '#3d444d',
             'bg': '#0d1117', 'glow': ('#7a52c0', '#d9cdf0', '#7a52c0')},
}


def get(path, auth=True):
    """The JSON of a GET to the API, following the pages of a list; the
    token of a workflow cannot read the gists, which are public anyway,
    whence auth=False for them."""
    out, url = None, API + path
    while url:
        req = urllib.request.Request(url, headers={
            'Accept': 'application/vnd.github+json',
            'User-Agent': USER + '-profile'})
        token = os.environ.get('GITHUB_TOKEN') if auth else None
        if token:
            req.add_header('Authorization', 'Bearer ' + token)
        with urllib.request.urlopen(req) as r:
            data = json.load(r)
            link = r.headers.get('Link', '')
        if isinstance(data, list):
            out = (out or []) + data
        elif isinstance(data, dict) and 'items' in data and out is None:
            out = data
        else:
            return data
        m = re.search(r'<([^>]+)>; rel="next"', link)
        url = m.group(1) if m and isinstance(data, list) else None
    return out


def languages():
    """The bytes of each language over the public repositories that are
    not forks, the most used first."""
    total = {}
    for repo in get('/users/%s/repos?type=owner&per_page=100' % USER):
        if repo['fork'] or repo['private'] or repo['name'] in SKIP_REPOS:
            continue
        for lang, n in get('/repos/%s/languages' % repo['full_name']).items():
            if lang not in SKIP_LANGS:
                total[lang] = total.get(lang, 0) + n
    return sorted(total.items(), key=lambda kv: -kv[1])


def chart(langs, theme):
    """A bar per language, its share of the bytes at its end; the ones
    beyond the first TOP go together as Other."""
    rows = langs[:TOP]
    rest = sum(n for _, n in langs[TOP:])
    if rest:
        rows.append(('Other', rest))
    whole = sum(n for _, n in langs) or 1
    c = THEMES[theme]
    w, label, gap, row, bar_h = 480, 112, 8, 26, 12
    span = w - label - 56
    top = max(n for _, n in rows)
    h = len(rows) * row + 8
    out = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" '
           'viewBox="0 0 %d %d" role="img" aria-label="Languages of the '
           'public repositories, by share of bytes">' % (w, h, w, h),
           '<style>%s text{font-size:12px}.b{transform-box:fill-box;'
           'transform-origin:left;animation:grow .9s ease-out both}'
           '.p{animation:show .4s ease-out both}%s</style>'
           % (FONT, MOTION)]
    for k, (lang, n) in enumerate(rows):
        y = 4 + k * row
        length = max(4, span * n / top)
        share = 100 * n / whole
        out.append('<text x="%d" y="%d" text-anchor="end" fill="%s">%s'
                   '</text>' % (label - gap, y + 14, c['text'],
                                escape(lang)))
        out.append('<rect class="b" style="animation-delay:%.2fs" x="%d" '
                   'y="%d" width="%.1f" height="%d" rx="2" fill="%s">'
                   '<title>%s: %.1f%%</title></rect>'
                   % (0.1 * k, label, y + 5, length, bar_h, c['bar'],
                      escape(lang), share))
        out.append('<text class="p" style="animation-delay:%.2fs" x="%.1f" '
                   'y="%d" fill="%s">%s</text>'
                   % (0.1 * k + 0.8, label + length + 6, y + 14, c['muted'],
                      '%.1f%%' % share if share >= 0.1 else '<0.1%'))
    out.append('</svg>')
    return '\n'.join(out) + '\n'


def wrap(text, width, lines):
    """text in at most lines lines of width characters, the last one
    ending in an ellipsis if the text goes on."""
    words, out, cur = text.split(), [], ''
    for w in words:
        if len(cur) + len(w) + (1 if cur else 0) <= width:
            cur = (cur + ' ' + w) if cur else w
        else:
            out.append(cur)
            cur = w
    if cur:
        out.append(cur)
    if len(out) > lines:
        out = out[:lines]
        out[-1] = out[-1][:width - 1].rstrip(' ,.;:') + '\u2026'
    return out


def card(repo, theme, k=0):
    """A card of a repository, in the layout of the pinned ones, the k-th
    of the list coming in a little after the one before it."""
    c = THEMES[theme]
    w, h = 400, 120
    lang = repo.get('language') or ''
    delay = 0.12 * k
    out = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" '
           'viewBox="0 0 %d %d" role="img" aria-label="%s">'
           % (w, h, w, h, escape(repo['name'])),
           '<style>%s.card{animation:rise .6s ease-out %.2fs both}'
           '.accent{transform-box:fill-box;transform-origin:top;'
           'animation:draw .7s ease-out %.2fs both}%s</style>'
           % (FONT, delay, delay + 0.3, MOTION),
           '<defs><linearGradient id="glow" x1="0" y1="0" x2="0" y2="1">'
           '<stop offset="0" stop-color="%s"/><stop offset="0.5" '
           'stop-color="%s"/><stop offset="1" stop-color="%s"/>'
           '<animateTransform attributeName="gradientTransform" '
           'type="translate" values="0 -1;0 1" dur="6s" '
           'repeatCount="indefinite"/></linearGradient></defs>' % c['glow'],
           '<g class="card">',
           '<rect x="0.5" y="0.5" width="%d" height="%d" rx="6" fill="%s" '
           'stroke="%s"/>' % (w - 1, h - 1, c['bg'], c['border']),
           '<rect class="accent" x="0.5" y="12" width="3" height="%d" '
           'rx="1.5" fill="url(#glow)"/>' % (h - 24),
           '<path transform="translate(16,16)" fill="%s" d="%s"/>'
           % (c['muted'], ICON_REPO),
           '<text x="40" y="29" font-size="14" font-weight="600" fill="%s">'
           '%s</text>' % (c['link'], escape(repo['name']))]
    for k, line in enumerate(wrap(repo.get('description') or '', 60, 2)):
        out.append('<text x="16" y="%d" font-size="12" fill="%s">%s</text>'
                   % (54 + 18 * k, c['muted'], escape(line)))
    x, y = 16, 100
    if lang:
        out.append('<circle cx="%d" cy="%d" r="6" fill="%s"/>'
                   % (x + 6, y - 4, LANG_COLORS.get(lang, c['muted'])))
        out.append('<text x="%d" y="%d" font-size="12" fill="%s">%s</text>'
                   % (x + 16, y, c['muted'], escape(lang)))
        x += 24 + 7 * len(lang)
    for icon, n in ((ICON_STAR, repo['stargazers_count']),
                    (ICON_FORK, repo['forks_count'])):
        if not n:
            continue
        out.append('<path transform="translate(%d,%d)" fill="%s" d="%s"/>'
                   % (x, y - 12, c['muted'], icon))
        out.append('<text x="%d" y="%d" font-size="12" fill="%s">%d</text>'
                   % (x + 20, y, c['muted'], n))
        x += 32 + 7 * len(str(n))
    out.append('</g>')
    out.append('</svg>')
    return '\n'.join(out) + '\n'


def cards(root):
    """The cards of CARDS, written in assets/cards, and the markdown that
    shows them two per row, each linking to its repository."""
    os.makedirs(os.path.join(root, 'assets', 'cards'), exist_ok=True)
    items = []
    for k, name in enumerate(CARDS):
        repo = get('/repos/%s/%s' % (USER, name))
        for theme in THEMES:
            with open(os.path.join(root, 'assets', 'cards', '%s-%s.svg'
                                   % (name, theme)), 'w') as f:
                f.write(card(repo, theme, k))
        items.append(
            '<a href="%s"><picture><source media="(prefers-color-scheme: '
            'dark)" srcset="assets/cards/%s-dark.svg"><img alt="%s" '
            'src="assets/cards/%s-light.svg" width="400"></picture></a>'
            % (repo['html_url'], name, escape(name), name))
    return '\n'.join(items)


def gists():
    lines = []
    for g in get('/users/%s/gists?per_page=100' % USER, auth=False):
        if not g['public']:
            continue
        desc = (g['description'] or '').strip()
        name, _, rest = desc.partition(':')
        if not rest:
            name, rest = next(iter(g['files'])), desc
        lines.append('- [%s](%s): %s' % (name.strip(), g['html_url'],
                                         rest.strip()))
    return '\n'.join(lines)


def put(text, name, body):
    start, end = '<!-- %s:start -->' % name, '<!-- %s:end -->' % name
    pattern = re.compile(re.escape(start) + '.*?' + re.escape(end), re.S)
    return pattern.sub(lambda _: start + '\n' + body + '\n' + end, text)


def main(argv):
    readme = argv[0] if argv else 'README.md'
    root = os.path.dirname(os.path.abspath(readme))
    langs = languages()
    for theme in THEMES:
        with open(os.path.join(root, 'assets', 'languages-%s.svg' % theme),
                  'w') as f:
            f.write(chart(langs, theme))
    with open(readme) as f:
        text = f.read()
    text = put(text, 'cards', cards(root))
    text = put(text, 'gists', gists())
    with open(readme, 'w') as f:
        f.write(text)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
