"""Step A collector (2026-10-28): one full 900 s F3 run of 'ours' (FROZEN2, lam=0.5, penalties OFF), with
  - the task trace (Sim(trace=True)),
  - a per-move log: source (rebal / reroute / orphan), from/to, queue position and the queue neighbours directly ahead
    and behind at move time (empirical counterfactual: had the task stayed, it would have started between them),
    AET parts (inp, svc, out) at the old and the new node from the pre-step state,
  - start time of every run, and every container-count change (time, [(f, k)]).
Behaviour is identical to the baseline (logging only). Dumps plain Python structures to stepA.pkl."""
import pickle
import sys
import time

import numpy as np

from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1]))

import faaspr_fig11_f3 as m  # noqa: E402
from dfps.o3s import O3SimAdjuster  # noqa: E402
from dfps.sim import Sim  # noqa: E402
from dfps.solution import Sol  # noqa: E402
from dfps.variants import make_adjuster, sim_kwargs  # noqa: E402
from frozen2 import FROZEN2  # noqa: E402

OUT = str(HERE / "results" / "penalty_stepA" / "stepA.pkl")      # derived (~30 MB, *.pkl is gitignored): rerun to rebuild


def key(run):
    return None if run is None else (run.req.id, run.task, run.n_moves)


class LSim(Sim):
    def _init_log(self):
        self.mlog, self.starts, self.cnt_events = [], {}, []
        self.src, self._pre = "other", None

    def _start(self, ins, run):
        super()._start(ins, run)
        self.starts[(run.req.id, run.task)] = (self.now, int(ins.node), run.n_moves, int(run.f))

    def _reroute(self, run):
        prev = self.src
        if self.src != "orphan":
            self.src = "reroute"
        super()._reroute(run)
        self.src = prev

    def apply_placement(self, X):
        before = self.cnt.copy()
        prev, self.src = self.src, "orphan"
        super().apply_placement(X)
        self.src = prev
        ch = np.argwhere(self.cnt != before)
        if len(ch):
            self.cnt_events.append((self.now, [(int(f), int(k)) for f, k in ch]))

    def apply_solution(self, sol):
        before = self.cnt.copy()
        pre, s0 = {}, None
        for run, k_new in list(sol.rnode.items()):
            if k_new != run.node and run in self.queue[run.node][run.f]:
                if s0 is None:
                    s0 = Sol(self)
                q = self.queue[run.node][run.f]
                pos = q.index(run)
                pre[id(run)] = dict(a_old=s0.aet(run, run.node, parts=True), a_new=s0.aet(run, int(k_new), parts=True),
                                    pos=pos, qlen_old=len(q), qlen_new=len(self.queue[int(k_new)][run.f]),
                                    cnt_old=int(self.cnt[run.f, run.node]), cnt_new=int(self.cnt[run.f, int(k_new)]),
                                    ahead=key(q[pos - 1]) if pos > 0 else None,
                                    behind=key(q[pos + 1]) if pos + 1 < len(q) else None)
        self._pre, prev, self.src = pre, self.src, "rebal"
        super().apply_solution(sol)
        self._pre, self.src = None, prev
        ch = np.argwhere(self.cnt != before)
        if len(ch):
            self.cnt_events.append((self.now, [(int(f), int(k)) for f, k in ch]))

    def relocate(self, run, k_new):
        k_old = run.node
        p = self._pre.get(id(run)) if self._pre else None
        delay = self.move_cost * sum(self.net.stt(s, k_old, int(k_new)) for s in run.sizes)
        rec = dict(t=self.now, rid=run.req.id, wid=run.req.wf.id, task=run.task, f=run.f, k_old=int(k_old), k_new=int(k_new),
                   plan=int(run.req.plan[run.task]), n_before=run.n_moves, src=self.src, delay=delay, total=run.total,
                   t_arr=run.req.t_arr, t_first=run.t_first, inwin=bool(self.in_window(run.req.t_arr)))
        if p:
            rec.update(p)
        self.mlog.append(rec)
        super().relocate(run, k_new)


sc, X0 = m.build("F3", 0.7, 5, 1)
kw = sim_kwargs("B_STAR", m.ASSUME)
DUR = float(sys.argv[1]) if len(sys.argv) > 1 else 900.0
if DUR != 900.0:
    OUT = OUT.replace(".pkl", f"_{int(DUR)}.pkl")
kw.update(warmup=m.d.WARMUP, duration=DUR, retry_min_interval=1.0, retry_max_attempts=10, trace=True)
adj = O3SimAdjuster(make_adjuster("B_STAR", m.ASSUME, seed=1 + 300), m.MOVE_PERIOD_F3, epoch=60.0, horizon=120.0, K=5,
                     seed=1 + 800, warmup=m.d.WARMUP, blind=True, cand_mode="nosim", churn=dict(FROZEN2, lam=0.5),
                     sizing_cache={})
kw["interval"] = adj.next_interval
sim = LSim(sc, X0.copy(), adjuster=adj, seed=1 + 400, **kw)
sim._init_log()
t0 = time.time()
res = sim.run()
sim.check_invariants()
print("p99", res["p99_makespan"], "n_moved", res["n_moved"], "logged moves", len(sim.mlog), f"{time.time()-t0:.0f}s", flush=True)

wfs = {}
for w in sc.workflows:
    wfs[w.id] = dict(n=w.n, ft=list(w.ft), parents=[list(p) for p in w.parents], children=[list(c) for c in w.children],
                     ss=dict(w.ss), input_size=float(w.input_size), crit=float(sim.crit_path[w.id]))
dump = dict(trace=sim.trace, mlog=sim.mlog, starts=sim.starts, cnt_events=sim.cnt_events, wfs=wfs,
            exec_time=[float(x) for x in sim.exec_time], h=sim.net.h.tolist(), bw=sim.net.bw, epd=sim.net.epd,
            slo_factor=sim.slo_factor, move_cost=sim.move_cost, warmup=sim.warmup, duration=sim.duration,
            period=m.MOVE_PERIOD_F3, p99=res["p99_makespan"], n_moved=res["n_moved"])
with open(OUT, "wb") as fh:
    pickle.dump(dump, fh)
print("dumped", OUT, flush=True)
