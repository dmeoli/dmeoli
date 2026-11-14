#!/usr/bin/env python3
"""Writes the parts of the README of the profile that come from GitHub: the
list of the public gists, and the chart of the languages of the public
repositories (assets/, in a light, a dark and an automatic version). The README
keeps everything else; each generated part sits between the markers
<!-- NAME:start --> and <!-- NAME:end -->.

Usage: profile.py [README]
GITHUB_TOKEN, if set, is used for the requests to the API of GitHub.
"""

import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from xml.sax.saxutils import escape

import yaml

USER = 'dmeoli'
API = 'https://api.github.com'

# repositories whose code is mostly of others (a fork kept up, a tap, a site)
SKIP_REPOS = {'abLEMON', 'homebrew-ablemon', 'dmeoli.github.io', USER}
# languages whose bytes are not code written (outputs of notebooks, pages)
SKIP_LANGS = {'Jupyter Notebook', 'HTML', 'CSS', 'SCSS'}
TOP = 8

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
ICON_CODE = ('m11.28 3.22 4.25 4.25a.75.75 0 0 1 0 1.06l-4.25 4.25a.749.749 '
             '0 0 1-1.275-.326.749.749 0 0 1 .215-.734L13.94 8l-3.72-3.72a.7'
             '49.749 0 0 1 .326-1.275.749.749 0 0 1 .734.215Zm-6.56 0a.751.7'
             '51 0 0 1 1.042.018.751.751 0 0 1 .018 1.042L2.06 8l3.72 3.72a.'
             '749.749 0 0 1-.326 1.275.749.749 0 0 1-.734-.215L.47 8.53a.75.'
             '75 0 0 1 0-1.06Z')
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
    'light': {'bar': '#7338a8', 'text': '#1f2328', 'muted': '#59636e',
              'track': '#eee7f5', 'link': '#7338a8', 'border': '#d1d9e0',
              'bg': 'none', 'glow': ('#7338a8', '#ad85d0', '#7338a8')},
    'dark': {'bar': '#d4b9eb', 'text': '#e6edf3', 'muted': '#b4b9c0',
             'track': '#281e38', 'link': '#e1ccf4', 'border': '#3d444d',
             'bg': 'none', 'glow': ('#7338a8', '#d4b9eb', '#7338a8')},
}

# the ground and the border of the cards of each section, a scale of the
# purple from the projects to the earlier ones, and the gold of the gists,
# so that a card stands out from the page and tells its section
KINDS = {
    'projects': {'light': ('#ede5f4', '#cab3de'),
                 'dark': ('#302143', '#4a2a6a')},
    'tools': {'light': ('#f4eff8', '#d9c9e8'),
              'dark': ('#2b1f3c', '#40265c')},
    'earlier': {'light': ('#f9f7fc', '#e7ddf0'),
                'dark': ('#1e162a', '#37234e')},
    'gist': {'light': ('#f9f3e3', '#e3d3a4'),
             'dark': ('#272114', '#5e5132'),
             'glow': ('#846f2d', '#e0c97f', '#846f2d')},
}


def colors(theme, kind):
    """The colors of a card of the given section in the given theme."""
    c = dict(THEMES[theme])
    k = KINDS.get(kind)
    if k:
        c['bg'], c['border'] = k[theme]
        c['glow'] = k.get('glow', c['glow'])
    return c


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
        # the API of GitHub answers now and then with an error that the
        # same request does not give a moment later: three tries
        for attempt in range(3):
            try:
                with urllib.request.urlopen(req) as r:
                    data = json.load(r)
                    link = r.headers.get('Link', '')
                break
            except urllib.error.HTTPError:
                if attempt == 2:
                    raise
                time.sleep(5)
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


def footer(x, y, c, lang, counts):
    """The language with its dot, then each (icon, number) of counts that
    is not zero, from x on the baseline y."""
    out = []
    if lang:
        out.append('<circle cx="%d" cy="%d" r="6" fill="%s"/>'
                   % (x + 6, y - 4, LANG_COLORS.get(lang, c['muted'])))
        out.append('<text x="%d" y="%d" font-size="12" fill="%s">%s</text>'
                   % (x + 16, y, c['muted'], escape(lang)))
        x += 24 + 7 * len(lang)
    for icon, n in counts:
        if not n:
            continue
        if icon:
            out.append('<path transform="translate(%d,%d)" fill="%s" '
                       'd="%s"/>' % (x, y - 12, c['muted'], icon))
            out.append('<text x="%d" y="%d" font-size="12" fill="%s">%s'
                       '</text>' % (x + 20, y, c['muted'], escape(str(n))))
            x += 32 + 7 * len(str(n))
        else:
            out.append('<text x="%d" y="%d" font-size="12" fill="%s">%s'
                       '</text>' % (x, y, c['muted'], escape(str(n))))
            x += 16 + 7 * len(str(n))
    return out


def frame(w, h, c, k, kind, label):
    """The head of the SVG of a card: its style and motion, the gradient
    of its accent, the box and the accent, on the left of a repository and
    on the top of a gist."""
    delay = 0.12 * k
    vertical = kind != 'gist'
    out = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" '
           'viewBox="0 0 %d %d" role="img" aria-label="%s">'
           % (w, h, w, h, escape(label)),
           '<style>%s.card{animation:rise .6s ease-out %.2fs both}'
           '.accent{transform-box:fill-box;transform-origin:%s;'
           'animation:%s .7s ease-out %.2fs both}'
           '.mono{font-family:ui-monospace,SFMono-Regular,"SF Mono",Menlo,'
           'Consolas,monospace}%s</style>'
           % (FONT, delay, 'top' if vertical else 'left',
              'draw' if vertical else 'grow', delay + 0.3, MOTION),
           '<defs><linearGradient id="glow" x1="0" y1="0" x2="%d" y2="%d">'
           '<stop offset="0" stop-color="%s"/><stop offset="0.5" '
           'stop-color="%s"/><stop offset="1" stop-color="%s"/>'
           '<animateTransform attributeName="gradientTransform" '
           'type="translate" values="%s" dur="6s" repeatCount="indefinite"/>'
           '</linearGradient></defs>'
           % (((0, 1) if vertical else (1, 0)) + c['glow'] +
              ('0 -1;0 1' if vertical else '-1 0;1 0',)),
           '<g class="card">',
           '<rect x="0.5" y="0.5" width="%d" height="%d" rx="6" fill="%s" '
           'stroke="%s"/>' % (w - 1, h - 1, c['bg'], c['border'])]
    if vertical:
        out.append('<rect class="accent" x="0.5" y="12" width="%d" '
                   'height="%d" rx="1.5" fill="url(#glow)"/>'
                   % (4 if kind == 'projects' else 3, h - 24))
    else:
        out.append('<rect class="accent" x="12" y="0.5" width="%d" '
                   'height="3" rx="1.5" fill="url(#glow)"/>' % (w - 24))
    return out


def card(repo, theme, k=0, kind='projects'):
    """A card of a repository, in the layout of the pinned ones: the owner
    before the name for a repository of another, the description as
    GitHub has it; a main project has a wider accent."""
    c = colors(theme, kind)
    w, h = 400, 120
    out = frame(w, h, c, k, kind, repo['name'])
    out.append('<path transform="translate(16,16)" fill="%s" d="%s"/>'
               % (c['muted'], ICON_REPO))
    # the owner and the name in one text, so that whoever draws it puts
    # them one after the other in the font it has
    owner = ''
    if repo['owner'] != USER:
        owner = '<tspan fill="%s">%s/</tspan>' % (c['muted'],
                                                 escape(repo['owner']))
    out.append('<text x="40" y="29" font-size="14">%s<tspan '
               'font-weight="600" fill="%s">%s</tspan></text>'
               % (owner, c['link'], escape(repo['name'])))
    for i, line in enumerate(wrap(repo['description'], 60, 2)):
        out.append('<text x="16" y="%d" font-size="12" fill="%s">%s</text>'
                   % (54 + 18 * i, c['muted'], escape(line)))
    out += footer(16, 100, c, repo['language'],
                  ((ICON_STAR, repo['stars']), (ICON_FORK, repo['forks'])))
    out += ['</g>', '</svg>']
    return '\n'.join(out) + '\n'


def gist_card(g, theme, k=0):
    """A card of a gist: the code icon, the name in monospace as a file,
    the accent on the top and the language."""
    c = colors(theme, 'gist')
    w, h = 400, 120
    out = frame(w, h, c, k, 'gist', g['name'])
    out.append('<path transform="translate(16,18)" fill="%s" d="%s"/>'
               % (c['muted'], ICON_CODE))
    out.append('<text class="mono" x="40" y="31" font-size="14" '
               'font-weight="600" fill="%s">%s</text>'
               % (c['link'], escape(g['name'])))
    for i, line in enumerate(wrap(g['description'], 60, 2)):
        out.append('<text x="16" y="%d" font-size="12" fill="%s">%s</text>'
                   % (56 + 18 * i, c['muted'], escape(line)))
    out += footer(16, 100, c, g['language'], ())
    out += ['</g>', '</svg>']
    return '\n'.join(out) + '\n'


def auto(light, dark):
    """The light and the dark version in one SVG, which shows the one of
    the color scheme of the viewer: GitLab drops <picture> and <source>,
    so its README gets this one from the <img>. The two versions share
    the head and the style; the ids get the theme as suffix."""
    head, style = light.split('\n', 2)[:2]
    parts = []
    for theme, svg in (('light', light), ('dark', dark)):
        body = svg.split('\n', 2)[2].rsplit('</svg>', 1)[0]
        for name in re.findall(r' id="([^"]+)"', body):
            body = re.sub(r'(id="|#)%s\b' % re.escape(name),
                          r'\g<1>%s-%s' % (name, theme), body)
        parts.append('<g class="%s">\n%s</g>\n' % (theme, body))
    style = style.replace('</style>', '.dark{display:none}@media '
                          '(prefers-color-scheme: dark){.light{display:none}'
                          '.dark{display:inline}}</style>')
    return '%s\n%s\n%s</svg>\n' % (head, style, ''.join(parts))


def picture(href, path, alt, width):
    """GitHub picks a <source> by its own theme, so the <img> is seen only
    where <picture> is dropped (GitLab): it gets the automatic version."""
    return ('<a href="%s"><picture><source media="(prefers-color-scheme: '
            'dark)" srcset="%s-dark.svg"><source media="(prefers-color-'
            'scheme: light)" srcset="%s-light.svg"><img alt="%s" '
            'src="%s-auto.svg" width="%d"></picture></a>'
            % (href, path, path, escape(alt), path, width))


def write_themes(root, path, draw):
    """path-light.svg, path-dark.svg and path-auto.svg, from draw(theme)."""
    svg = {theme: draw(theme) for theme in THEMES}
    for theme in THEMES:
        write(root, '%s-%s.svg' % (path, theme), svg[theme])
    write(root, path + '-auto.svg', auto(svg['light'], svg['dark']))


def write(root, path, svg):
    full = os.path.join(root, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, 'w') as f:
        f.write(svg)


def repo_data(full):
    """The fields of a card of the repository owner/name (or name, of
    USER), as GitHub has them."""
    key = full if '/' in full else '%s/%s' % (USER, full)
    r = get('/repos/' + key)
    data = {'name': r['name'], 'owner': r['owner']['login'],
            'description': r.get('description') or '',
            'language': r.get('language') or '',
            'stars': r['stargazers_count'], 'forks': r['forks_count'],
            'url': r['html_url']}
    return data


def software(root):
    """The sections of projects.yml: the cards of their repositories,
    written in assets/cards, the markdown that shows them two a row under
    the title of each section, and the entries of the personal page,
    which shows the same cards with the notes."""
    with open(os.path.join(root, 'projects.yml')) as f:
        spec = yaml.safe_load(f)
    md, data = [], []
    for sec in spec['sections']:
        kind = sec['id']
        items, entries = [], []
        for k, entry in enumerate(sec['repos']):
            if isinstance(entry, str):
                entry = {'repo': entry}
            repo = repo_data(entry['repo'])
            slug = entry['repo'].replace('/', '-')
            write_themes(root, 'assets/cards/' + slug,
                         lambda theme: card(repo, theme, k, kind))
            items.append(picture(repo['url'], 'assets/cards/' + slug,
                                 repo['name'], 400))
            entries.append({'name': repo['name'], 'url': repo['url'],
                            'card': 'assets/cards/' + slug,
                            'note': entry.get('note')})
        # the notes of the cards, in English and above them, {who} as a link
        notes = ['**%s**: %s' % (e['name'], e['note']['en'].replace(
                     '{who}', '[%s](%s)' % (e['note'].get('who'),
                                            e['note'].get('url'))))
                 for e in entries if e['note']]
        md.append('### %s %s\n\n%s%s' % (sec['emoji'], sec['title']['en'],
                                          ''.join(n + '\n\n' for n in notes),
                                          '\n'.join(items)))
        data.append({'id': sec['id'], 'title': sec['title'],
                     'emoji': sec['emoji'],
                     'repos': entries})
    return '\n\n'.join(md), data


def gists(root):
    """The cards of the public gists, newest first, their markdown, and
    the entries of the page."""
    items, entries = [], []
    k = 0
    for g in get('/users/%s/gists?per_page=100' % USER, auth=False):
        if not g['public']:
            continue
        desc = (g['description'] or '').strip()
        name, _, rest = desc.partition(':')
        files = list(g['files'].values())
        if not rest:
            name, rest = files[0]['filename'], desc
        rest = rest.strip()
        data = {'name': name.strip(), 'description': rest[:1].upper() +
                rest[1:],
                'language': next((f['language'] for f in files
                                  if f.get('language') not in
                                  (None, 'Markdown', 'Text', 'INI')), '')}
        write_themes(root, 'assets/gists/' + g['id'],
                     lambda theme: gist_card(data, theme, k))
        items.append(picture(g['html_url'], 'assets/gists/' + g['id'],
                             data['name'], 400))
        entries.append({'name': data['name'], 'url': g['html_url'],
                        'card': 'assets/gists/' + g['id']})
        k += 1
    return '\n'.join(items), entries


def put(text, name, body):
    start, end = '<!-- %s:start -->' % name, '<!-- %s:end -->' % name
    pattern = re.compile(re.escape(start) + '.*?' + re.escape(end), re.S)
    return pattern.sub(lambda _: start + '\n' + body + '\n' + end, text)


def main(argv):
    readme = argv[0] if argv else 'README.md'
    root = os.path.dirname(os.path.abspath(readme))
    langs = languages()
    write_themes(root, 'assets/languages', lambda theme: chart(langs, theme))
    with open(readme) as f:
        text = f.read()
    # the sections and the gists, also in assets/projects.json, from which
    # the personal page shows the same cards in the same order
    md, data = software(root)
    text = put(text, 'software', md)
    md, entries = gists(root)
    text = put(text, 'gists', md)
    data.append({'id': 'gists', 'title': {'en': 'Gists', 'it': 'Gist'},
                 'emoji': '\U0001F4DD', 'repos': entries})
    write(root, 'assets/projects.json',
          json.dumps({'sections': data}, indent=1, ensure_ascii=False) +
          '\n')
    with open(readme, 'w') as f:
        f.write(text)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
