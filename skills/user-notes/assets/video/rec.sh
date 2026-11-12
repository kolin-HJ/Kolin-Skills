SESSION="${SESSION:-user-notes-video}"
A() { agent-browser --session "$SESSION" "$@"; }
pause() { python3 -c 'import sys, time; time.sleep(float(sys.argv[1]))' "$1"; }
now() { python3 -c 'import time; print(time.time())'; }
fresh() {
  A close >/dev/null 2>&1
  A --init-script "$1" set viewport 1440 900
}
tag() {
  A eval "(() => { const want = $2; const el = [...document.querySelectorAll(want.q)].filter(e => e.offsetParent !== null).find(e => want.t ? (e.innerText || '').trim() === want.t : true); if (!el) return 'MISSING'; el.setAttribute('data-un', '$1'); return 'ok'; })()"
}
box() {
  A get box "[data-un=$1]" --json | python3 -c 'import json, sys; b = json.load(sys.stdin)["data"]; print(round(b["x"]), round(b["y"]), round(b["width"]), round(b["height"]))'
}
mark() { echo "$1 $(now)${2:+ $2}" >> "$MARKS"; }
roll() {
  : > "$MARKS"
  A record start "$1" --cursor >/dev/null
  mark start
  pause 1
}
wrap() {
  pause 1.5
  A record stop
}
glide() {
  local b x y w h
  b=$(box "$1") || return 1
  read -r x y w h <<< "$b"
  A mouse move $((x + w / 2)) $((y + h / 2)) --human --duration 800 >/dev/null
  pause 0.3
  echo "$b"
}
hover() {
  local b
  b=$(glide "$1") || return 1
  mark "$1" "$b"
  pause 1
}
click() {
  local b
  b=$(glide "$1") || return 1
  A mouse down >/dev/null
  A mouse up >/dev/null
  mark "$1" "$b"
  pause 1
}
typein() {
  click "$1" || return 1
  local i
  for ((i = 0; i < ${#2}; i++)); do
    A keyboard type "${2:$i:1}" >/dev/null
    pause 0.07
  done
  pause 1
}
