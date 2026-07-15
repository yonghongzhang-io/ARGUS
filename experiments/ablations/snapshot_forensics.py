"""Which dated gpt-4o snapshot reproduces the June-era Table-1 numbers?

Runs the two-stage assessor and the reimplemented single-pass on the 11 clear
flaws against a PINNED snapshot (ARGUS_LLM_MODEL). If a snapshot reproduces
detection 1.000/loc 0.909 (two-stage) and ~0.455 (single-pass), the paper can
pin that snapshot and keep its historical numbers reproducibly.
"""
import json, os, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src")); sys.path.insert(0, str(ROOT / "experiments" / "ablations"))
from argus.config import load_flaws
from argus.evaluation.runner import evaluate_flaws
from argus.evaluation.injection import inject_flaw
from argus.evaluation.metrics import evaluate_pair, summarize_results
from argus.agent.llm_assessor import make_client
from complete_matrix import audit_singlepass

snap = sys.argv[1]
os.environ["ARGUS_LLM_MODEL"] = snap
paper = json.loads((ROOT/"examples/papers/clean_supported.json").read_text())
flaws = load_flaws()

t0=time.time()
res = evaluate_flaws(paper, sorted(flaws), max_steps=1, assessor="llm")
s = res["summary"]
print(f"[{snap}] two-stage: det={s['detection_rate']:.3f} fa={s['false_alarm_rate']:.3f} "
      f"loc={s['localization_acc']:.3f} ({time.time()-t0:.0f}s)", flush=True)

client = make_client()

# NOTE: audit_singlepass hardcodes model="gpt-4o"; monkeypatch via env-resolved wrapper
import complete_matrix as cm
_orig = cm.create_structured
def patched(client, **kw):
    kw["model"] = snap
    return _orig(client, **kw)
cm.create_structured = patched

clean = audit_singlepass(paper, client)
pairs=[]
for fid in sorted(flaws):
    inj = inject_flaw(paper, fid)
    m = audit_singlepass(inj, client)
    pairs.append(evaluate_pair(clean, m, flaws[fid]["target_dimension"], threshold="medium"))
ss = summarize_results(pairs)
print(f"[{snap}] single-pass: det={ss['detection_rate']:.3f} fa={ss['false_alarm_rate']:.3f} "
      f"loc={ss['localization_acc']:.3f}")
out = {"snapshot": snap, "two_stage": s, "single_pass": ss}
(Path(__file__).parent / f"forensics_{snap}.json").write_text(json.dumps(out, indent=1))
print("wrote", f"forensics_{snap}.json")
