"""Diagnostic (simulator only): how much capacity is stranded while tasks wait? Sampled every 2 s inside the window, per function: busy / idle / starting containers and queued tasks,
cluster-wide. 'Stranded' = a function has queued tasks while OTHER functions hold idle containers."""
import sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from testbed.diag.latency_breakdown import RecSim, RecOD, breakdown     # noqa: E402
from testbed import frozen_live as FL, baselines_live as BL, sebs_scenario as S    # noqa: E402
from testbed.queue_runs import CELLS                                    # noqa: E402
from dfps.nsga2 import PlacementProblem                                 # noqa: E402
from dfps.solution import IDLE, BUSY, COLD                              # noqa: E402


def sampler(base):
    class Samp(base):
        def _ev_done(self, ins, token, c):
            nxt = self.__dict__.get("_next", self.warmup)
            if self.now >= nxt and self.now <= self.duration:
                self._next = self.now + 2.0
                F, N = self.F, self.N
                st = np.zeros((3, F)); qd = np.zeros(F)
                for k in range(N):
                    for f in range(F):
                        for i in self.inst[k][f]:
                            st[0 if i.state == BUSY else 1 if i.state == IDLE else 2, f] += 1
                        qd[f] += len(self.queue[k][f]) if hasattr(self, "queue") and not hasattr(self, "nq") else 0
                if hasattr(self, "nq"):
                    for k in range(N):
                        for run in self.nq[k]:
                            qd[run.f] += 1
                self.__dict__.setdefault("_samples", []).append((st, qd))
            super()._ev_done(ins, token, c)
    return Samp


def main():
    app, seed = sys.argv[1], int(sys.argv[2])
    rho, cap, warm, window, drain = CELLS[app]; dur = warm + window
    sc, samp = S.build(seed, apps=[app], rho=rho, ne=10, duration_s=dur, rate_cap=cap)
    X0 = PlacementProblem(sc.network, sc.ecc, np.array([f.exec_time for f in sc.functions])).random(np.random.default_rng(seed))
    per = float(sys.argv[3]) if len(sys.argv) > 3 else 4.0
    dname = sys.argv[4] if len(sys.argv) > 4 else "transfer_only"
    from dfps import dispatchers as D
    for arm in (("frozen4", "rl") if len(sys.argv) <= 3 else ("frozen4",)):
        if arm == "rl":
            sim, _ = BL.build_rl(sc, seed, warmup=warm, duration=dur, sim_cls=sampler(RecOD), exec_sampler=samp)
        else:
            sim, _ = FL.build(sc, X0, seed, arm="frozen4", warmup=warm, duration=dur, exec_sampler=samp, sim_cls=sampler(__import__('testbed.diag.late_class', fromlist=['Late']).Late if dname.startswith('late') else RecSim), move_period=per, dispatcher=D.DISPATCHERS['transfer_only' if dname == 'late' else 'jsq' if dname == 'latejsq' else dname])
        sim.run()
        S_ = sim._samples; n = len(S_); F = sim.F
        busy = np.mean([s[0] for s, q in S_], axis=0); idle = np.mean([s[1] for s, q in S_], axis=0); cold = np.mean([s[2] for s, q in S_], axis=0); q = np.mean([q for s, q in S_], axis=0)
        strand = np.mean([(q_.sum() > 0) and any(s[1][g] > 0 for g in range(F) if q_[g] == 0) for s, q_ in S_])
        waiting = np.mean([q_.sum() > 0 for s, q_ in S_])
        idle_when_wait = np.mean([s[1].sum() for s, q_ in S_ if q_.sum() > 0] or [0])
        print(f"\n{app} seed {seed} {arm} (mover period {per}, dispatcher {dname}): {n} samples; slots {int(sc.ecc.sum())}; mean busy {busy.sum():.1f}, idle {idle.sum():.1f}, starting {cold.sum():.1f}")
        print("  per function  busy / idle / starting / queued:", [(round(float(busy[f]), 1), round(float(idle[f]), 1), round(float(cold[f]), 1), round(float(q[f]), 1)) for f in range(F)])
        qf0 = [(s[1][0], s[0][0], q_[0]) for s, q_ in S_ if q_[0] > 0]
        print(f"  function 0, only at samples where its tasks are queued ({len(qf0)} of {n}): idle containers {np.mean([x[0] for x in qf0]):.1f}, busy {np.mean([x[1] for x in qf0]):.1f}, queued {np.mean([x[2] for x in qf0]):.1f};  share of samples with idle f0 containers while f0 queued: {100*np.mean([x[0] > 0 for x in qf0]):.0f}%")
        print(f"  samples with any task waiting: {100*waiting:.0f}%;  of all samples, waiting while another function holds idle containers: {100*strand:.0f}%;  mean idle containers when something waits: {idle_when_wait:.1f}")


main()
