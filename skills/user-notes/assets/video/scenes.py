import html
import json
import os
import shutil
import sys

FADE = 0.5
INTRO = 5.0
OUTRO = 4.5
ENTER = "{ opacity: 0, x: 60 }"
LEAD = 0.6
RING = 1.6


def esc(text):
    return html.escape(text, quote=True)


def ring_box(box, scale, pad=10):
    x, y, w, h = box
    return round(x * scale - pad), round(y * scale - pad), round(w * scale + 2 * pad), round(h * scale + 2 * pad)


def read_marks(path):
    marks = {}
    with open(path) as f:
        for line in f:
            name, at, *box = line.split()
            if name in marks:
                sys.exit(f"{path}: {name} is marked twice; tag the second target with another name")
            marks[name] = (float(at), [int(v) for v in box])
    zero = marks["start"][0]
    return {name: (at - zero, box) for name, (at, box) in marks.items() if name != "start"}


def scene_events(scene, base):
    events = {"start": (0.0, [])}
    for layer in scene["layers"]:
        path = os.path.join(base, layer["marks"])
        for name, (at, box) in read_marks(path).items():
            if name in events:
                sys.exit(f"{scene['id']}: {name} is marked in two layers; tag one of them with another name")
            if at < layer["mediaStart"]:
                sys.exit(f"{path}: {name} happens before mediaStart {layer['mediaStart']}")
            events[name] = (layer["start"] + at - layer["mediaStart"], box)
    return events


def when(events, sid, item, lead=0.0):
    name = item["at"]
    if name not in events:
        sys.exit(f"{sid}: no mark named {name}; marked: {', '.join(events)}")
    at, box = events[name]
    return round(max(0.0, at + item.get("offset", 0) - lead), 2), box


def target(events, sid, item, lead=0.0):
    t, box = when(events, sid, item, lead)
    if not box:
        sys.exit(f"{sid}: {item['at']} has no box; mark it with click, hover or typein")
    return t, box


def demo_scene(scene, scale, base):
    sid = scene["id"]
    events = scene_events(scene, base)
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
            t, box = target(events, sid, ring, LEAD)
            d = ring.get("d", RING)
            x, y, w, h = ring_box(box, scale)
            rid = f"{sid}-r{li}{ri}"
            label = f'<b id="{rid}-b">{esc(ring["label"])}</b>' if ring.get("label") else ""
            out.append(
                f'          <div id="{rid}" class="clip ring" data-start="{t}" data-duration="{d}" data-track-index="{track}"'
                f' style="left:{x}px;top:{y}px;width:{w}px;height:{h}px"><i id="{rid}-i"></i>{label}</div>'
            )
            tl.append(f'tl.fromTo("#{rid}-i", {{ opacity: 0, scale: 1.4 }}, {{ opacity: 1, scale: 1, duration: 0.35, ease: "back.out(2)" }}, {t});')
            if label:
                tl.append(f'tl.fromTo("#{rid}-b", {{ opacity: 0, y: -8 }}, {{ opacity: 1, y: 0, duration: 0.3, ease: "power2.out" }}, {round(t + 0.2, 2)});')
        track += 1
        if layer.get("zoom"):
            z = layer["zoom"]
            t, (x, y, w, h) = target(events, sid, z)
            origin = f"{round((x + w / 2) * scale)}px {round((y + h / 2) * scale)}px"
            tl.append(
                f'tl.fromTo("#{zid}", {{ scale: 1, transformOrigin: "{origin}" }}, {{ scale: {z["scale"]}, transformOrigin: "{origin}", duration: 1.1, ease: "power2.inOut" }}, {t});'
            )
        out.append("        </div></div>")
    out.append("      </div>\n    </div>")
    captions = [{**cap, "t": when(events, sid, cap)[0]} for cap in scene.get("captions", [])]
    for ci, cap in enumerate(captions):
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
    ends = [layer["start"] + layer["dur"] for layer in scene["layers"]] + [cap["t"] + cap["d"] for cap in captions]
    return finish(out, tl, sid), round(max(ends), 2)


def finish(out, tl, sid):
    out.append("  </div>\n  <script>\n    const tl = gsap.timeline({ paused: true });")
    out += ["    " + line for line in tl]
    out.append(f'    window.__timelines["{sid}"] = tl;\n  </script>\n</template>\n')
    return "\n".join(out)


def side_scene(sid, body, media, length, shot_from):
    out = [
        "<template>",
        '  <style>\n    #root { position: absolute; inset: 0; }\n  </style>',
        f'  <div id="root" data-composition-id="{sid}" data-width="1920" data-height="1080">',
        f'    <div id="{sid}-bg" class="side-bg"></div>\n    <div id="{sid}-body" class="side-body">',
        *body,
        "    </div>",
        f'    <video id="{sid}-shot" class="clip shot" data-start="0" data-duration="{length}" data-media-start="0" data-track-index="0"'
        f' src="assets/{esc(media)}" muted playsinline></video>'
        if media.endswith(".mp4")
        else f'    <img id="{sid}-shot" class="shot" src="assets/{esc(media)}" alt="" />',
    ]
    tl = [
        f'tl.fromTo("#{sid}-bg", {{ opacity: 0 }}, {{ opacity: 1, duration: 0.3, ease: "power1.out" }}, 0);',
        f'tl.fromTo("#{sid}-shot", {shot_from}, {{ opacity: 1, x: 0, duration: 0.8, ease: "power3.out" }}, 0);',
        f'tl.fromTo("#{sid}-body > *", {{ opacity: 0, y: 16 }}, {{ opacity: 1, y: 0, duration: 0.5, ease: "power2.out", stagger: 0.25 }}, 0.35);',
    ]
    return finish(out, tl, sid)


def title_line(spec):
    return f'      <div class="side-title">What\'s new in {esc(spec["app"])}, <b>{esc(spec["date"])}</b></div>'


def intro_scene(spec):
    body = [
        f'      <div class="side-word">{esc(spec["brand"])}</div>',
        title_line(spec),
        f'      <div class="side-label side-count">{esc(spec["intro"])}</div>',
    ]
    return side_scene("intro", body, spec["stage"]["intro"], INTRO, "{ opacity: 1, x: 60 }")


def note_scene(index, note):
    body = [
        f'      <div class="side-label">Also new · {esc(note["page"])}</div>',
        f'      <div class="side-title">{esc(note["text"])}</div>',
    ]
    return side_scene(f"note{index}", body, note["clip"], note["dur"], ENTER)


def outro_scene(spec):
    chips = "".join(f'<span class="side-chip">{esc(page)}</span>' for page in spec["pages"])
    body = [
        title_line(spec),
        '      <div class="side-label">Where to find it</div>',
        f'      <div class="side-chips">{chips}</div>',
    ]
    return side_scene("outro", body, spec["stage"]["outro"], OUTRO, ENTER)


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
    base = os.path.dirname(os.path.abspath(spec_path))
    comps = os.path.join(project, "compositions")
    os.makedirs(comps, exist_ok=True)
    os.makedirs(os.path.join(project, "assets"), exist_ok=True)
    shutil.copy(os.path.join(os.path.dirname(os.path.abspath(__file__)), "scene.css"), os.path.join(project, "assets", "scene.css"))
    files = {"intro": intro_scene(spec)}
    lengths = {"intro": INTRO}
    for scene in spec["scenes"]:
        files[scene["id"]], lengths[scene["id"]] = demo_scene(scene, scale, base)
    order = ["intro"] + [scene["id"] for scene in spec["scenes"]]
    for i, note in enumerate(spec.get("notes", [])):
        files[f"note{i}"], lengths[f"note{i}"] = note_scene(i, note), note["dur"]
        order.append(f"note{i}")
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
