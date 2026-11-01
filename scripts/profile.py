#!/usr/bin/env python3
"""Writes the parts of the README of the profile that come from GitHub: the
list of the public gists, the pull requests to the projects of others, and
the chart of the languages of the public repositories (assets/, in a light
and in a dark version). The README keeps everything else; each generated
part sits between the markers <!-- NAME:start --> and <!-- NAME:end -->.

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
# the projects of others listed by name, the ones with the most merged
SHOWN = 6

THEMES = {
    'light': {'bar': '#7a52c0', 'text': '#1f2328', 'muted': '#59636e',
              'track': '#eae4f4'},
    'dark': {'bar': '#a98be0', 'text': '#e6edf3', 'muted': '#9198a1',
             'track': '#221c2e'},
}


def get(path):
    """The JSON of a GET to the API, following the pages of a list."""
    out, url = None, API + path
    while url:
        req = urllib.request.Request(url, headers={
            'Accept': 'application/vnd.github+json',
            'User-Agent': USER + '-profile'})
        token = os.environ.get('GITHUB_TOKEN')
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
           '<style>text{font:12px -apple-system,BlinkMacSystemFont,'
           '"Segoe UI",Helvetica,Arial,sans-serif}</style>']
    for k, (lang, n) in enumerate(rows):
        y = 4 + k * row
        length = max(4, span * n / top)
        share = 100 * n / whole
        out.append('<text x="%d" y="%d" text-anchor="end" fill="%s">%s'
                   '</text>' % (label - gap, y + 14, c['text'],
                                escape(lang)))
        out.append('<rect x="%d" y="%d" width="%.1f" height="%d" rx="2" '
                   'fill="%s"><title>%s: %.1f%%</title></rect>'
                   % (label, y + 5, length, bar_h, c['bar'], escape(lang),
                      share))
        out.append('<text x="%.1f" y="%d" fill="%s">%s</text>'
                   % (label + length + 6, y + 14, c['muted'],
                      '%.1f%%' % share if share >= 0.1 else '<0.1%'))
    out.append('</svg>')
    return '\n'.join(out) + '\n'


def gists():
    lines = []
    for g in get('/users/%s/gists?per_page=100' % USER):
        if not g['public']:
            continue
        desc = (g['description'] or '').strip()
        name, _, rest = desc.partition(':')
        if not rest:
            name, rest = next(iter(g['files'])), desc
        lines.append('- [%s](%s): %s' % (name.strip(), g['html_url'],
                                         rest.strip()))
    return '\n'.join(lines)


def contributions():
    """The projects of others with a pull request merged or open, those
    with the most merged first."""
    q = 'is:pr author:%s -user:%s' % (USER, USER)
    found, page = [], 1
    while True:   # the search gives 100 results a page, 1000 at most
        items = get('/search/issues?per_page=100&page=%d&q=%s'
                    % (page, urllib.request.quote(q)))['items']
        found += items
        if len(items) < 100 or page == 10:
            break
        page += 1
    repos = {}
    for pr in found:
        name = pr['repository_url'].split('/repos/')[1]
        merged = bool(pr.get('pull_request', {}).get('merged_at'))
        m, o = repos.get(name, (0, 0))
        if merged:
            m += 1
        elif pr['state'] == 'open':
            o += 1
        repos[name] = (m, o)
    link = ('[%%s](https://github.com/%%s/pulls?q=is%%%%3Apr+author%%%%3A%s)'
            % USER)
    merged = sorted(((n, m, o) for n, (m, o) in repos.items() if m),
                    key=lambda t: (-t[1], t[0].lower()))
    lines = []
    for name, m, o in merged[:SHOWN]:
        lines.append('- %s: %d merged%s' % (link % (name, name), m,
                                            ', %d open' % o if o else ''))
    others = sum(1 for m, o in repos.values() if m or o) - \
        len(merged[:SHOWN])
    if others > 0:
        lines.append('- and %d more projects, see [all the pull requests]'
                     '(https://github.com/pulls?q=is%%3Apr+author%%3A%s'
                     '+-user%%3A%s)' % (others, USER, USER))
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
    text = put(text, 'gists', gists())
    text = put(text, 'contributions', contributions())
    with open(readme, 'w') as f:
        f.write(text)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
