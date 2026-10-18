#!/bin/bash
jq -r '
  def rgb(r; g; b; s): "\u001b[38;2;\(r);\(g);\(b)m" + s + "\u001b[0m";
  def lbl(s): rgb(127; 132; 156; s);
  def val(s): rgb(203; 166; 247; s);
  def pct(x): if x == null then "--" else "\(x | round)%" end;
  [ lbl("session ") + val(pct(.rate_limits.five_hour.used_percentage)),
    lbl("week ")    + val(pct(.rate_limits.seven_day.used_percentage)),
    lbl("context ") + val(if .context_window.total_input_tokens == null then "--"
                       else "\(.context_window.total_input_tokens / 1000 | round)K" end)
  ] | join(lbl(" · "))
'
