#!/usr/bin/env python3
import json, os, requests, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
env = {}
el = ROOT / "portal" / ".env.local"
if el.exists():
    for line in el.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line: continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip().strip('"').strip("'")
url = env.get("SUPABASE_URL") or os.environ.get("SUPABASE_URL")
key = env.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
if not url or not key:
    print("no supabase env")
    sys.exit(1)
h = {"apikey": key, "Authorization": "Bearer " + key, "Accept": "application/json"}

# total
r = requests.get(url + "/rest/v1/graph_nodes?select=count&graph_version=eq.newbooks-v1&limit=1", headers=h, timeout=30)
print("SUPABASE graph_nodes count:", r.text[:200] if r.ok else r.status_code)

# large sample for chapter presence + patch_* fields
r2 = requests.get(url + "/rest/v1/graph_nodes?select=id,source_file,properties&graph_version=eq.newbooks-v1&limit=3000", headers=h, timeout=120)
rows = r2.json() if r2.ok else []
has_ch = [x for x in rows if isinstance(x.get("properties"), dict) and x["properties"].get("chapter_id")]
has_pm = [x for x in rows if isinstance(x.get("properties"), dict) and x["properties"].get("patch_method")]
has_rn = [x for x in rows if isinstance(x.get("properties"), dict) and x["properties"].get("review_needed") is not None]
print(f"In sample {len(rows)}: chapter_id={len(has_ch)} patch_method={len(has_pm)} review_needed_set={len(has_rn)}")

# per-book probes (use stems that had 0 before)
for stem in ["Jaimini", "Saravali", "Hora_Sara", "Jataka_Tatva", "Uttara", "Brihat_Samhita", "Prasna_Marga"]:
    r3 = requests.get(url + f"/rest/v1/graph_nodes?select=id,source_file,properties&graph_version=eq.newbooks-v1&source_file=ilike.%{stem}%&limit=400", headers=h, timeout=60)
    sm = r3.json() if r3.ok else []
    smc = [x for x in sm if isinstance(x.get("properties"), dict) and x["properties"].get("chapter_id")]
    print(f"  {stem}: fetched={len(sm)} with_chapter={len(smc)} sample_pmethod={sum(1 for x in sm if (x.get('properties') or {}).get('patch_method'))}")

# overall estimated covered using a second page
print("done")

print("\n=== EXACT RN SAMPLES ===")
import json as _json, time as _t
patches = _json.load(open("knowledge-graph/patches/node-chapter-map.json"))["patches"]
rn_true = [p for p in patches if p.get("review_needed")][:6]
for p in rn_true:
    nid = p["node_id"]
    rr = requests.get(url + f"/rest/v1/graph_nodes?id=eq.{nid}&graph_version=eq.newbooks-v1&select=id,source_file,properties&limit=1", headers=h, timeout=15)
    rw = (rr.json() or [{}])[0] if rr.ok else {}
    prp = rw.get("properties") or {}
    print("  ", nid[:58], "ch=", prp.get("chapter_id"), "rn=", prp.get("review_needed"), "pm=", prp.get("patch_method"))
