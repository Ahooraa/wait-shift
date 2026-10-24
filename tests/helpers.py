"""Hand-built tiny systems for unit tests (no randomness unless asked for)."""
import numpy as np

from dfps.model import Function, Scenario, Workflow
from dfps.network import Network
from dfps.sim import Run, Req, Sim


class ScriptedRng:
    """Replays chosen values for the random draws of Alg.1 / Alg.2 (integers, choice, random)."""
    def __init__(self, integers=(), random=()):
        self.i, self.r = list(integers), list(random)

    def integers(self, lo, hi=None, size=None):
        return self.i.pop(0)

    def choice(self, arr, *a, **k):
        return list(arr)[0]

    def random(self):
        return self.r.pop(0)


def line_net(n):
    return Network(n, [(i, i + 1) for i in range(n - 1)])


def tiny_sim(X, exec_times, cold, ecc=None, esc_mb=1e6, wf=None, **kw):
    n = len(X)
    net = line_net(n)
    funcs = [Function(i, e, c) for i, (e, c) in enumerate(zip(exec_times, cold))]
    ecc = np.array(ecc if ecc is not None else np.asarray(X).sum(1))
    wf = wf or Workflow.from_edges(0, 2, [(0, 1)], [0, 1], {(0, 1): 20.0}, 20.0)
    sc = Scenario(funcs, [wf], net, ecc, np.full(n, esc_mb), [], dict(duration_s=300.0))
    return Sim(sc, np.asarray(X), **kw)


def inject(sim, task, node, wf=None, plan=None):
    """Put a ready-to-execute request for `task` of the (single) workflow into FRQ_{f,node}."""
    wf = wf or sim.sc.workflows[0]
    r = Req()
    r.id, r.wf, r.origin, r.t_arr, r.t_done = len(sim.req_ids) if hasattr(sim, "req_ids") else 0, wf, 0, 0.0, None
    r.plan = plan or {t: node for t in range(wf.n)}
    r.pending = [0] * wf.n
    r.left = wf.n
    run = Run(r, task, node)
    sim.queue[node][run.f].append(run)
    sim.storage_used[node] += run.total
    return run
