#!/usr/bin/env python3
"""Turn a raw Claude Design export of the QAM site into the live index.html.

Reconstructed 2026-09-22 from the shipped index.html, after the original
build_launch.py went missing. Everything it adds is listed in the project doc
"QAM Site Launch Sept 17 2026".

  python3 build_launch.py <design-export.html> <reference-index.html> <out.html>
"""
import json, re, sys

CF_TOKEN = "6cf52cf4fefb413398c70a2e65d12f6d"

def read(p):
    with open(p, encoding="utf-8") as f:
        return f.read()

def template_of(s):
    m = re.search(r'(<script type="__bundler/template">)(.*?)(</script>)', s, re.S)
    if not m:
        raise SystemExit("no template block")
    return m, json.loads(m.group(2))

def put_template(s, m, tpl):
    # The bundler escapes every "/" as \u002F so that a literal </script>
    # inside the JSON can never close the surrounding <script> element.
    # json.dumps does not, so do it here: \u002F is identical to "/" in JSON.
    body = json.dumps(tpl).replace("/", "\\u002F")
    return s[:m.start(2)] + body + s[m.end(2):]

def main(src, ref, out):
    new, live = read(src), read(ref)

    # ---- 1. outer head -------------------------------------------------
    head_re = re.compile(r'(  <title>.*?</script>\n)(  <style>)', re.S)
    live_head = head_re.search(live)
    if not live_head:
        raise SystemExit("could not find the launch head block in the reference")
    if CF_TOKEN not in live_head.group(1):
        raise SystemExit("reference head is missing the analytics beacon")

    if '<title>Bundled Page</title>' not in new:
        raise SystemExit("export head does not look like a raw Design export")
    new = new.replace(
        '<html>\n<head>\n  <meta charset="utf-8">\n  <title>Bundled Page</title>\n  <style>',
        '<html lang="en">\n<head>\n  <meta charset="utf-8">\n'
        + live_head.group(1) + '  <style>', 1)

    # ---- 2. template ---------------------------------------------------
    mL, tL = template_of(live)
    mN, tN = template_of(new)

    tN = tN.replace('<!DOCTYPE html>\n<html>', '<!DOCTYPE html>\n<html lang="en">', 1)

    # head tags the export ships wrong or not at all
    og_live = re.search(
        r'(<meta property="og:image".*?<link rel="apple-touch-icon" href="/apple-touch-icon\.png">\s*'
        r'<script type="module" src="https://static\.cloudflareinsights\.com/beacon\.min\.js"[^>]*>\s*</script>)',
        tL, re.S)
    og_new = re.search(r'<meta property="og:image" content="assets/og-earth\.jpg">', tN)
    if not (og_live and og_new):
        raise SystemExit("could not line up the og/favicon block")
    tN = tN[:og_new.start()] + og_live.group(1) + tN[og_new.end():]

    # play-button hover CSS
    css_live = re.search(r'(\s*\[data-qam-play\] span \{.*?transform: none; \} \}\n)', tL, re.S)
    anchor = '  @keyframes qamdraw'
    if not css_live or anchor not in tN:
        raise SystemExit("could not place the play-button CSS")
    tN = tN.replace(anchor, css_live.group(1).rstrip('\n') + '\n' + anchor, 1)

    # the inert play badge becomes the real button
    btn_live = re.search(r'(<button type="button" data-qam-play="\d+".*?</button>)', tL, re.S)
    badge_new = re.search(
        r'<div style="position: absolute; left: 18px; bottom: 18px; pointer-events: none">.*?</div>',
        tN, re.S)
    if not (btn_live and badge_new):
        raise SystemExit("could not swap the play badge for the play button")
    tN = tN[:badge_new.start()] + btn_live.group(1) + tN[badge_new.end():]

    # the cut runs 3:16
    if 'Ninety seconds' in tN:
        tN = tN.replace('Ninety seconds', 'Three minutes')

    # Formspree honeypot, if an older export brings it back
    tN = re.sub(r'<input[^>]*name="_gotcha"[^>]*>', '', tN)

    # build stamp
    stamp_live = re.search(r"const QAM_BUILD = '([^']*)'", tL).group(1)
    tN = re.sub(r"const QAM_BUILD = '[^']*'",
                "const QAM_BUILD = '" + stamp_live + "'", tN, count=1)

    # click-to-play script
    play_live = re.search(r'(<script>\n\(function\(\)\{\n  document\.addEventListener\(.click.*?</script>)', tL, re.S)
    if not play_live:
        raise SystemExit("could not find the click-to-play script")
    if 'player.vimeo.com' not in tN:
        tN = tN.replace('</body>', play_live.group(1) + '\n</body>', 1)

    new = put_template(new, mN, tN)
    with open(out, "w", encoding="utf-8") as f:
        f.write(new)
    print("wrote", out, len(new), "chars")

if __name__ == "__main__":
    if len(sys.argv) != 4:
        raise SystemExit(__doc__)
    main(*sys.argv[1:])
