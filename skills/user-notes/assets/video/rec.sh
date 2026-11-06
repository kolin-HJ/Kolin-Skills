SESSION="${SESSION:-user-notes-video}"
A() { agent-browser --session "$SESSION" "$@"; }
fresh() {
  A close >/dev/null 2>&1
  A --init-script "$1" set viewport 1440 900
}
tag() {
  A eval "(() => { const want = $2; const el = [...document.querySelectorAll(want.q)].filter(e => e.offsetParent !== null).find(e => want.t ? (e.innerText || '').trim() === want.t : true); if (!el) return 'MISSING'; el.setAttribute('data-un', '$1'); return 'ok'; })()"
}
box() { A get box "[data-un=$1]" --json | tr -d '\n'; echo; }
mark() { echo "$1 $(python3 -c 'import time; print(time.time())')" >> "$MARKS"; }
