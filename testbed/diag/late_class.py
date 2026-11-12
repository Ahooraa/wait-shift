"""The late-binding oracle class (see late_bind_probe.py). Diagnostic ORACLE (simulator only, development seeds 1-3, NOT a proposed controller): FROZEN-4 with the node of each non-join task chosen when the task becomes
ready (join the node with the smallest transfer + expected wait, from the live queues and idle containers) instead of at request arrival.
Tells how much of FROZEN-4's queueing is caused by deciding too early. Storage reservations are moved with the task."""
import sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from testbed.diag.latency_breakdown import RecSim, breakdown            # noqa: E402
from testbed import frozen_live as FL, sebs_scenario as S               # noqa: E402
from testbed.queue_runs import CELLS                                    # noqa: E402
from dfps.nsga2 import PlacementProblem                                 # noqa: E402
from dfps.solution import IDLE                                          # noqa: E402


class Late(RecSim):
    def _ev_done(self, ins, token, c):
        run = ins.run
        r, wf, t, k0 = run.req, run.req.wf, run.task, ins.node
        extra = {}                                          # tasks this very completion has just sent to a (function, node): not yet in its queue
        for ch in wf.children[t]:
            if len(wf.parents[ch]) != 1:
                continue
            f, tot = wf.ft[ch], wf.input_total(ch)
            old = int(r.plan[ch])
            ks = np.flatnonzero(self.cnt[f] > 0)
            best, bs = old, float("inf")
            for k in ks:
                k = int(k)
                if self.esc[k] - self.storage_used[k] + (tot if k == old else 0.0) < tot - 1e-9:
                    continue
                idle = sum(1 for i in self.inst[k][f] if i.state == IDLE and i.run is None)
                ql = len(self.queue[k][f]) + extra.get((f, k), 0)
                wait = 0.0 if idle > ql else (ql + 1 - idle) * float(self.exec_time[f]) / max(1, int(self.cnt[f, k]))
                sc_ = self.net.stt(wf.ss[(t, ch)], k0, k) + wait
                if sc_ < bs - 1e-12:
                    bs, best = sc_, k
            extra[(f, best)] = extra.get((f, best), 0) + 1
            if best != old:
                self.storage_used[old] -= tot
                self.storage_used[best] += tot
                r.plan[ch] = best
        super()._ev_done(ins, token, c)

