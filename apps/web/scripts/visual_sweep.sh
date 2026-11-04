#!/bin/bash
# Pemeriksaan visual terprogram: overflow horizontal per halaman/viewport.
set -u
BASE="http://127.0.0.1:5173"
TID="b3f0a2de-1111-4000-8000-tenant01"
PAGES=(
  "/|landing"
  "/login|login"
  "/register|register"
  "/app/$TID/overview|overview"
  "/app/$TID/customers|customers"
  "/app/$TID/customers/svc-002|customer-detail"
  "/app/$TID/routers|routers"
  "/app/$TID/routers/rtr-101|router-detail"
  "/app/$TID/routers/new|router-new"
  "/app/$TID/imports/router|import-wizard"
  "/app/$TID/imports/csv|import-csv"
  "/app/$TID/backups|backups"
  "/app/$TID/monitoring|monitoring"
  "/app/$TID/jobs|jobs"
  "/app/$TID/jobs/job-5012|job-detail"
  "/app/$TID/radius|radius"
  "/app/$TID/packages|packages"
  "/app/$TID/settings/team|settings-team"
  "/app/$TID/settings/subscription|settings-subscription"
  "/admin/subscriptions|admin"
)
VIEWPORTS=("1440 900" "1280 800" "768 1024" "360 800")

printf '%-24s %-6s %-11s %s\n' "page" "vp" "sw/cw" "overflow"
for vp in "${VIEWPORTS[@]}"; do
  set -- $vp
  agent-browser set viewport "$1" "$2" > /dev/null 2>&1
  for entry in "${PAGES[@]}"; do
    route="${entry%%|*}"; name="${entry##*|}"
    agent-browser open "$BASE$route" > /dev/null 2>&1
    agent-browser wait --load networkidle > /dev/null 2>&1
    sleep 1
    res=$(agent-browser eval "document.documentElement.scrollWidth + '/' + document.documentElement.clientWidth" --json 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['result'])" 2>/dev/null)
    sw="${res%%/*}"; cw="${res##*/}"
    if [ -n "$sw" ] && [ -n "$cw" ] && [ "$sw" -gt "$cw" ]; then
      flag="OVERFLOW(+$((sw-cw))px)"
    else
      flag="ok"
    fi
    printf '%-24s %-6s %-11s %s\n' "$name" "$1" "$res" "$flag"
  done
done
