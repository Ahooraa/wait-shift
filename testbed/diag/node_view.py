"""Diagnostic (simulator only): per node, for ExCamera function 0: queued tasks, idle and busy containers, and how full the node's state storage is."""
import sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from testbed.diag.latency_breakdown import RecSim                       # noqa: E402
from testbed import frozen_live as FL, sebs_scenario as S               # noqa: E402
from testbed.queue_runs import CELLS                                    # noqa: E402
from dfps.nsga2 import PlacementProblem                                 # noqa: E402
from dfps.solution import IDLE, BUSY                                    # noqa: E402

app, seed, FN = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
rho, cap, warm, window, drain = CELLS[app]; dur = warm + window


class V(RecSim):
    def _ev_done(self, ins, token, c):
        if self.now >= self.__dict__.get("_nx", self.warmup) and self.now <= self.duration:
            self._nx = self.now + 2.0
            N = self.N
            row = np.zeros((N, 5))
            for k in range(N):
                row[k, 0] = len(self.queue[k][FN])
                row[k, 1] = sum(1 for i in self.inst[k][FN] if i.state == IDLE)
                row[k, 2] = sum(1 for i in self.inst[k][FN] if i.state == BUSY)
                row[k, 3] = self.storage_used[k] / max(self.esc[k], 1e-9)
                row[k, 4] = float(np.asarray(self.storage_used[k]))
            self.__dict__.setdefault("_rows", []).append(row)
        super()._ev_done(ins, token, c)


sc, samp = S.build(seed, apps=[app], rho=rho, ne=10, duration_s=dur, rate_cap=cap)
X0 = PlacementProblem(sc.network, sc.ecc, np.array([f.exec_time for f in sc.functions])).random(np.random.default_rng(seed))
sim, _ = FL.build(sc, X0, seed, arm="frozen4", warmup=warm, duration=dur, exec_sampler=samp, sim_cls=V)
sim.run()
R = np.array(sim._rows)
print(f"{app} seed {seed}, function {FN}: per node, mean over {len(R)} samples")
print(f"{'node':>4}{'slots':>6}{'storage cap':>12}{'queued':>8}{'idle':>6}{'busy':>6}{'storage used %':>16}")
for k in range(sim.N):
    print(f"{k:4d}{int(sc.ecc[k]):6d}{float(sim.esc[k]):12.0f}{R[:,k,0].mean():8.1f}{R[:,k,1].mean():6.1f}{R[:,k,2].mean():6.1f}{100*R[:,k,3].mean():16.0f}")
q = R[:, :, 0]; idl = R[:, :, 1]
both = ((q > 0) & True)
print(f"\nnode-samples with a queue AND an idle container of function {FN} on the same node: {100*np.mean((q>0)&(idl>0)):.1f}%  (a task waiting next to a free container: should be ~0)")
print(f"node-samples with a queue and no idle container: {100*np.mean((q>0)&(idl==0)):.0f}%;   idle containers and no queue: {100*np.mean((q==0)&(idl>0)):.0f}%")
print("sim.N", sim.N, " waiting-for-storage requests at end:", len(getattr(sim, 'waiting', [])), " n_rejected", sim.n_rejected)
