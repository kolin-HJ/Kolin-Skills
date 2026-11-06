import html
import json
import os
import shutil
import sys

FADE = 0.5
INTRO = 3.5
OUTRO = 4.5


def esc(text):
    return html.escape(text, quote=True)


def ring_box(box, scale, pad=10):
    x, y, w, h = box
    return round(x * scale - pad), round(y * scale - pad), round(w * scale + 2 * pad), round(h * scale + 2 * pad)


def demo_scene(scene, scale):
    sid = scene["id"]
    out = [
        "<template>",
        f"  <style>\n    #root {{ position: absolute; inset: 0; }}\n    #{sid}-stage {{ position: absolute; inset: 0; background: var(--sidebar); }}\n    .{sid}-layer {{ position: absolute; inset: 0; }}\n  </style>",
        f'  <div id="root" data-composition-id="{sid}" data-width="1920" data-height="1080">',
        f'    <div id="{sid}-stage">\n      <div class="frame">',
    ]
    tl = [f'tl.fromTo("#{sid}-stage", {{ opacity: 0 }}, {{ opacity: 1, duration: {FADE}, ease: "power1.out" }}, 0);']
    track = 0
    for li, layer in enumerate(scene["layers"]):
        lid, zid = f"{sid}-l{li}", f"{sid}-z{li}"
        out.append(f'        <div id="{lid}" class="{sid}-layer"><div id="{zid}" class="zoom">')
        out.append(
            f'          <video id="{sid}-v{li}" class="clip footage" data-start="{layer["start"]}" data-duration="{layer["dur"]}"'
            f' data-media-start="{layer["mediaStart"]}" data-track-index="{track}" src="assets/{esc(layer["src"])}" muted playsinline></video>'
        )
        track += 1
        if li > 0:
            tl.append(f'tl.fromTo("#{lid}", {{ opacity: 0 }}, {{ opacity: 1, duration: 0.35, ease: "none" }}, {layer["start"]});')
        for ri, ring in enumerate(layer.get("rings", [])):
            x, y, w, h = ring_box(ring["box"], scale)
            rid = f"{sid}-r{li}{ri}"
            label = f'<b id="{rid}-b">{esc(ring["label"])}</b>' if ring.get("label") else ""
            out.append(
                f'          <div id="{rid}" class="clip ring" data-start="{ring["t"]}" data-duration="{ring["d"]}" data-track-index="{track}"'
                f' style="left:{x}px;top:{y}px;width:{w}px;height:{h}px"><i id="{rid}-i"></i>{label}</div>'
            )
            tl.append(f'tl.fromTo("#{rid}-i", {{ opacity: 0, scale: 1.4 }}, {{ opacity: 1, scale: 1, duration: 0.35, ease: "back.out(2)" }}, {ring["t"]});')
            if label:
                tl.append(f'tl.fromTo("#{rid}-b", {{ opacity: 0, y: -8 }}, {{ opacity: 1, y: 0, duration: 0.3, ease: "power2.out" }}, {ring["t"] + 0.2});')
        track += 1
        if layer.get("zoom"):
            z = layer["zoom"]
            origin = f'{z["x"]}px {z["y"]}px'
            tl.append(
                f'tl.fromTo("#{zid}", {{ scale: 1, transformOrigin: "{origin}" }}, {{ scale: {z["scale"]}, transformOrigin: "{origin}", duration: 1.1, ease: "power2.inOut" }}, {z["t"]});'
            )
        out.append("        </div></div>")
    out.append("      </div>\n    </div>")
    for ci, cap in enumerate(scene.get("captions", [])):
        cid = f"{sid}-c{ci}"
        cls = " ".join(["cap"] + cap.get("place", []))
        sub = f'<div class="cap-sub">{esc(cap["sub"])}</div>' if cap.get("sub") else ""
        out.append(
            f'    <div id="{cid}" class="clip {cls}" data-start="{cap["t"]}" data-duration="{cap["d"]}" data-track-index="{track}">'
            f'<div id="{cid}-card" class="cap-card"><div class="cap-eyebrow">{esc(cap["eyebrow"])}</div>'
            f'<div class="cap-title">{esc(cap["title"])}</div>{sub}</div></div>'
        )
        tl.append(f'tl.fromTo("#{cid}-card", {{ opacity: 0, y: 30 }}, {{ opacity: 1, y: 0, duration: 0.5, ease: "power3.out" }}, {cap["t"]});')
        track += 1
    return finish(out, tl, sid)


def finish(out, tl, sid):
    out.append("  </div>\n  <script>\n    const tl = gsap.timeline({ paused: true });")
    out += ["    " + line for line in tl]
    out.append(f'    window.__timelines["{sid}"] = tl;\n  </script>\n</template>\n')
    return "\n".join(out)


def scene_length(scene):
    ends = [layer["start"] + layer["dur"] for layer in scene["layers"]]
    ends += [cap["t"] + cap["d"] for cap in scene.get("captions", [])]
    return round(max(ends), 2)


def intro_scene(spec):
    out = [
        "<template>",
        "  <style>\n    #root { position: absolute; inset: 0; }\n    #in-bg { position: absolute; inset: 0; background: var(--sidebar); }"
        "\n    #in-body { position: absolute; inset: 0; display: flex; flex-direction: column; justify-content: center; padding: 0 240px; gap: 22px; color: var(--sidebar-foreground); }"
        "\n    #in-word { font-family: Georgia, serif; font-size: 28px; font-weight: 700; letter-spacing: .1em; text-transform: uppercase; opacity: .75; }"
        "\n    #in-title { font-family: Georgia, serif; font-size: 72px; line-height: 1.1; font-weight: 400; color: var(--sidebar-accent-foreground); }"
        "\n    #in-title b { font-weight: 700; }"
        "\n    #in-sub { display: flex; align-items: center; gap: 16px; font-family: Inter, sans-serif; font-size: 30px; font-weight: 500; }"
        "\n    #in-mark { width: 36px; height: 5px; border-radius: 2px; background: var(--marker); }\n  </style>",
        '  <div id="root" data-composition-id="intro" data-width="1920" data-height="1080">',
        '    <div id="in-bg"></div>\n    <div id="in-body">',
        f'      <div id="in-word">{esc(spec["brand"])}</div>',
        f'      <div id="in-title">What\'s new in {esc(spec["app"])}, <b>{esc(spec["date"])}</b></div>',
        f'      <div id="in-sub"><span id="in-mark"></span><span>{esc(spec["intro"])}</span></div>',
        "    </div>",
    ]
    tl = [
        'tl.fromTo("#in-word", { opacity: 0, y: 16 }, { opacity: 1, y: 0, duration: 0.5, ease: "power2.out" }, 0.15);',
        'tl.fromTo("#in-title", { y: 12 }, { y: 0, duration: 0.9, ease: "power3.out" }, 0);',
        'tl.fromTo("#in-mark", { scaleX: 0, transformOrigin: "left center" }, { scaleX: 1, duration: 0.5, ease: "expo.out" }, 0.8);',
        'tl.fromTo("#in-sub", { opacity: 0, x: -20 }, { opacity: 1, x: 0, duration: 0.5, ease: "sine.out" }, 0.8);',
    ]
    return finish(out, tl, "intro")


def notes_scene(spec):
    rows, sels = [], []
    words = 0
    for gi, group in enumerate(spec["notes"]):
        rows.append(f'        <div id="nt-g{gi}">\n          <div class="nt-page">{esc(group["page"])}</div>')
        sels.append(f"#nt-g{gi} .nt-page")
        for ii, item in enumerate(group["items"]):
            rows.append(f'          <div id="nt-b{gi}-{ii}" class="nt-item">{esc(item)}</div>')
            sels.append(f"#nt-b{gi}-{ii}")
            words += len(item.split())
        rows.append("        </div>")
    out = [
        "<template>",
        "  <style>\n    #root { position: absolute; inset: 0; }\n    #nt-bg { position: absolute; inset: 0; background: var(--muted); }"
        "\n    #nt-body { position: absolute; inset: 0; padding: 90px 200px; display: flex; flex-direction: column; gap: 26px; color: var(--foreground); }"
        "\n    #nt-head { display: flex; align-items: center; gap: 16px; font-family: Inter, sans-serif; font-size: 28px; font-weight: 700; letter-spacing: .1em; text-transform: uppercase; color: var(--muted-foreground); }"
        '\n    #nt-head::before { content: ""; width: 28px; height: 5px; border-radius: 2px; background: var(--marker); }'
        "\n    #nt-title { font-family: Georgia, serif; font-size: 80px; font-weight: 700; line-height: 1.1; margin-top: -12px; }"
        "\n    #nt-card { background: var(--card); border: 1px solid var(--border); border-radius: var(--radius-md); box-shadow: var(--shadow-surface); padding: 34px 48px; display: flex; flex-direction: column; gap: 16px; }"
        "\n    .nt-page { font-family: Inter, sans-serif; font-size: 28px; font-weight: 700; letter-spacing: .06em; text-transform: uppercase; color: var(--muted-foreground); margin-top: 4px; }"
        "\n    .nt-item { display: flex; gap: 18px; font-family: Inter, sans-serif; font-size: 40px; line-height: 1.3; color: var(--foreground); }"
        '\n    .nt-item::before { content: ""; flex: none; width: 10px; height: 10px; border-radius: 3px; background: var(--primary); margin-top: 20px; }\n  </style>',
        '  <div id="root" data-composition-id="notes" data-width="1920" data-height="1080">',
        '    <div id="nt-bg"></div>\n    <div id="nt-body">',
        '      <div id="nt-head">Also in this update</div>\n      <div id="nt-title">Also new</div>',
        '      <div id="nt-card" data-hold>',
        *rows,
        "      </div>\n    </div>",
    ]
    tl = [
        'tl.fromTo("#nt-bg", { opacity: 0 }, { opacity: 1, duration: 0.5, ease: "power1.out" }, 0);',
        'tl.fromTo("#nt-head", { opacity: 0, y: 14 }, { opacity: 1, y: 0, duration: 0.5, ease: "power2.out" }, 0.3);',
        'tl.fromTo("#nt-title", { opacity: 0, y: 30 }, { opacity: 1, y: 0, duration: 0.6, ease: "power3.out" }, 0.4);',
        'tl.fromTo("#nt-card", { opacity: 0, y: 24 }, { opacity: 1, y: 0, duration: 0.6, ease: "expo.out" }, 0.7);',
    ]
    for i, sel in enumerate(sels):
        dx = 0 if sel.endswith(".nt-page") else -24
        tl.append(f'tl.fromTo("{sel}", {{ opacity: 0, x: {dx} }}, {{ opacity: 1, x: 0, duration: 0.45, ease: "power2.out" }}, {round(1.1 + i * 0.9, 2)});')
    length = round(1.1 + len(sels) * 0.9 + words / 3, 1)
    return finish(out, tl, "notes"), length


def outro_scene(spec):
    chips = "".join(f'        <span class="out-chip">{esc(page)}</span>\n' for page in spec["pages"])
    out = [
        "<template>",
        "  <style>\n    #root { position: absolute; inset: 0; }\n    #out-bg { position: absolute; inset: 0; background: var(--sidebar); }"
        "\n    #out-body { position: absolute; inset: 0; display: flex; flex-direction: column; justify-content: center; padding: 0 240px; gap: 34px; color: var(--sidebar-foreground); }"
        "\n    #out-title { font-family: Georgia, serif; font-size: 72px; line-height: 1.1; color: var(--sidebar-accent-foreground); }"
        "\n    #out-title b { font-weight: 700; }"
        "\n    #out-label { display: flex; align-items: center; gap: 16px; font-family: Inter, sans-serif; font-size: 28px; font-weight: 700; letter-spacing: .06em; text-transform: uppercase; opacity: .8; }"
        '\n    #out-label::before { content: ""; width: 28px; height: 5px; border-radius: 2px; background: var(--marker); }'
        "\n    #out-pages { display: flex; flex-wrap: wrap; gap: 14px; max-width: 1440px; }"
        "\n    .out-chip { font-family: Inter, sans-serif; font-size: 34px; font-weight: 500; padding: 12px 22px; border-radius: var(--radius-sm); background: var(--sidebar-accent); border: 1px solid var(--sidebar-border); color: var(--sidebar-accent-foreground); }\n  </style>",
        '  <div id="root" data-composition-id="outro" data-width="1920" data-height="1080">',
        '    <div id="out-bg"></div>\n    <div id="out-body">',
        f'      <div id="out-title">What\'s new in {esc(spec["app"])}, <b>{esc(spec["date"])}</b></div>',
        '      <div id="out-label">Where to find it</div>',
        f'      <div id="out-pages">\n{chips}      </div>',
        "    </div>",
    ]
    tl = [
        'tl.fromTo("#out-bg", { opacity: 0 }, { opacity: 1, duration: 0.5, ease: "power1.out" }, 0);',
        'tl.fromTo("#out-title", { opacity: 0, y: 30 }, { opacity: 1, y: 0, duration: 0.6, ease: "power3.out" }, 0.3);',
        'tl.fromTo("#out-label", { opacity: 0 }, { opacity: 1, duration: 0.4, ease: "sine.out" }, 0.7);',
        'tl.fromTo(".out-chip", { opacity: 0, y: 16 }, { opacity: 1, y: 0, duration: 0.4, ease: "back.out(1.6)", stagger: 0.12 }, 0.9);',
    ]
    return finish(out, tl, "outro")


def index_html(timeline, total):
    rows = "".join(
        f'      <div id="{sid}" class="clip" data-composition-id="{sid}" data-composition-src="compositions/{sid}.html" data-start="{start}"'
        f' data-duration="{length}" data-track-index="{1 + i % 2}" data-track-kind="graphics" data-width="1920" data-height="1080" style="z-index:{i + 1}"></div>\n'
        for i, (sid, start, length) in enumerate(timeline)
    )
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=1920, height=1080" />
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.15.0/dist/gsap.min.js"></script>
    <link rel="stylesheet" href="assets/hj-tokens.css" />
    <link rel="stylesheet" href="assets/scene.css" />
    <style>
      * {{ margin: 0; padding: 0; box-sizing: border-box; }}
      html, body {{ margin: 0; width: 1920px; height: 1080px; overflow: hidden; background: var(--sidebar); -webkit-font-smoothing: antialiased; }}
      .backdrop {{ position: absolute; inset: 0; background: var(--sidebar); }}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="{total}" data-width="1920" data-height="1080">
      <div class="backdrop"></div>
{rows}    </div>
    <script>
      window.__timelines = window.__timelines || {{}};
      const tl = gsap.timeline({{ paused: true }});
      window.__timelines["main"] = tl;
    </script>
  </body>
</html>
"""


def build(spec_path, project):
    with open(spec_path) as f:
        spec = json.load(f)
    scale = 1728 / spec["viewport"][0]
    comps = os.path.join(project, "compositions")
    os.makedirs(comps, exist_ok=True)
    os.makedirs(os.path.join(project, "assets"), exist_ok=True)
    shutil.copy(os.path.join(os.path.dirname(os.path.abspath(__file__)), "scene.css"), os.path.join(project, "assets", "scene.css"))
    files = {"intro": intro_scene(spec)}
    lengths = {"intro": INTRO}
    for scene in spec["scenes"]:
        files[scene["id"]] = demo_scene(scene, scale)
        lengths[scene["id"]] = scene_length(scene)
    order = ["intro"] + [scene["id"] for scene in spec["scenes"]]
    if spec.get("notes"):
        files["notes"], lengths["notes"] = notes_scene(spec)
        order.append("notes")
    files["outro"] = outro_scene(spec)
    lengths["outro"] = OUTRO
    order.append("outro")
    timeline, start = [], 0.0
    for sid in order:
        timeline.append((sid, round(start, 2), lengths[sid]))
        start += lengths[sid] - FADE
    total = round(start + FADE, 1)
    for sid, body in files.items():
        with open(os.path.join(comps, f"{sid}.html"), "w") as f:
            f.write(body)
    with open(os.path.join(project, "index.html"), "w") as f:
        f.write(index_html(timeline, total))
    for sid, start, length in timeline:
        print(f"{sid:<14} {start:>6.2f}  {length:>5.2f}s")
    print(f"total {total}s")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("usage: scenes.py <spec.json> <project dir>")
    build(sys.argv[1], sys.argv[2])
