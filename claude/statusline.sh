#!/bin/bash
input=$(cat)
dir=$(jq -r '.workspace.current_dir // .cwd // empty' <<<"$input" 2>/dev/null)
status=""
if [ -n "$dir" ] && top=$(git -C "$dir" rev-parse --show-toplevel 2>/dev/null) && [ -f "$top/.pstack/status.md" ]; then
  status=$(awk '
    match($0, /^[ \t]*(Blocked|Asks|Next):[ \t]*/) {
      key = $0; sub(/^[ \t]*/, "", key); sub(/:.*/, "", key); key = tolower(key)
      val = substr($0, RLENGTH + 1)
      if (val != "" && !(key in seen)) { seen[key] = val }
    }
    END {
      if (("blocked" in seen) || ("asks" in seen)) {
        if ("blocked" in seen) print "blocked\t" seen["blocked"]
        if ("asks" in seen) print "asks\t" seen["asks"]
      } else if ("next" in seen) print "next\t" seen["next"]
    }' "$top/.pstack/status.md")
fi
jq -r --arg status "$status" '
  def rgb(r; g; b; s): "\u001b[38;2;\(r);\(g);\(b)m" + s + "\u001b[0m";
  def lbl(s): rgb(127; 132; 156; s);
  def val(s): rgb(203; 166; 247; s);
  def pct(x): if x == null then "--" else "\(x | round)%" end;
  def clip(s): if (s | length) > 60 then s[:59] + "…" else s end;
  [ lbl("session ") + val(pct(.rate_limits.five_hour.used_percentage)),
    lbl("week ")    + val(pct(.rate_limits.seven_day.used_percentage)),
    lbl("context ") + val(if .context_window.total_input_tokens == null then "--"
                       else "\(.context_window.total_input_tokens / 1000 | round)K" end)
  ] + [ $status | split("\n")[] | select(. != "") | split("\t") | lbl(.[0] + " ") + val(clip(.[1])) ]
  | join(lbl(" · "))
' <<<"$input"
