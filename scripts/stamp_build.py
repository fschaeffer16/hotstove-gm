#!/usr/bin/env python3
"""Prepare index.html for the GitHub site: copy from the working source, add Home Screen tags,
stamp a build id, and write version.json so installed Home Screen apps reload themselves.
Usage: python3 scripts/stamp_build.py /path/to/source/index.html"""
import sys, os, re, json, datetime
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'index.html')
s = open(src, encoding='utf-8').read()
tags = '''<link rel="manifest" href="manifest.json">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="Hot Stove GM">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="theme-color" content="#0b1a33">
'''
if 'rel="manifest"' not in s:
    s = s.replace('<link rel="apple-touch-icon" href="apple-touch-icon.png">',
                  '<link rel="apple-touch-icon" href="apple-touch-icon.png">\n' + tags, 1)
build = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d%H%M%S')
s, n = re.subn(r"const BUILD='[^']*';", f"const BUILD='{build}';", s)
assert n == 1, 'BUILD constant not found'
open(os.path.join(ROOT, 'index.html'), 'w', encoding='utf-8').write(s)
json.dump({'build': build}, open(os.path.join(ROOT, 'version.json'), 'w'))
print('build', build)
