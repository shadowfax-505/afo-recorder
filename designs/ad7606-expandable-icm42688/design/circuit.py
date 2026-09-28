"""AD7606 circuit source is circuit-spec.json. No ADS dependency."""
import json
from pathlib import Path
r=Path(__file__).resolve().parent
s=json.loads((r/"circuit-spec.json").read_text())
if (r/"placement-main.json").exists():
 p=json.loads((r/"placement-main.json").read_text())
 for c in s["parts"]:
  if c["ref"] in p:c["x"],c["y"],c["rotation"]=p[c["ref"]]
(r/"main.json").write_text(json.dumps(s,indent=2))
