"""Whole-simulation invariants: capacity, storage, conservation of requests (PLAN.md section 9.2)."""
import numpy as np

from dfps.nsga2 import PlacementProblem
from dfps.sa import SimulatedAnnealing
from dfps.sim import Sim
from dfps.workload import build_scenario


def small_scenario(seed=2, scale=0.3):
    return build_scenario(seed, "uniform", scale, ne=24, n_workflows=5, pool_size=10, duration_s=60.0)


def placement(sc, seed=0):
    pr = PlacementProblem(sc.network, sc.ecc, np.array([f.exec_time for f in sc.functions]))
    return pr.random(np.random.default_rng(seed))


def test_static_run_conserves_requests():
    sc = small_scenario()
    sim = Sim(sc, placement(sc), seed=1, warmup=0.0, duration=60.0)
    r = sim.run()
    sim.check_invariants()
    assert r["n_unfinished"] == 0 and r["n_completed"] == r["n_arrived"] == len(sc.arrivals)
    assert (sim.storage_used < 1e-6).all()                      # every consumed state was removed
    assert r["cold_starts"] == 0                                # static placement: no cold starts (p.10 Sec.5.2.1)


def test_dfps_run_keeps_invariants_at_every_adjustment():
    sc = small_scenario()
    sim = Sim(sc, placement(sc), adjuster=SimulatedAnnealing(seed=5, iterations=60), seed=1, warmup=0.0,
              duration=60.0, debug=True)                        # debug: check_invariants after every adjustment
    r = sim.run()
    sim.check_invariants()
    assert r["n_unfinished"] == 0 and r["n_completed"] == r["n_arrived"] == len(sc.arrivals)
    assert (sim.storage_used < 1e-6).all()
    assert r["n_adjust"] >= 10 and r["cold_starts"] > 0         # replacements happened and paid cold starts


def test_same_seed_is_reproducible():
    sc = small_scenario()
    X = placement(sc)
    a = Sim(sc, X, adjuster=SimulatedAnnealing(seed=5, iterations=30), seed=1, warmup=0.0, duration=60.0).run()
    b = Sim(sc, X, adjuster=SimulatedAnnealing(seed=5, iterations=30), seed=1, warmup=0.0, duration=60.0).run()
    wall = ("adjust_ms_p95", "plan_ms_p95", "plan_ms_mean")          # wall-clock decision timings are not deterministic
    strip = lambda r: {k: v for k, v in r.items() if k not in wall}
    assert strip(a) == strip(b)
    assert a["event_hash"] == b["event_hash"]                       # identical event sequence (Task 8 determinism check)


def test_event_hash_differs_for_different_seeds():
    sc = small_scenario()
    X = placement(sc)
    a = Sim(sc, X, seed=1, warmup=0.0, duration=60.0).run()
    b = Sim(sc, X, seed=2, warmup=0.0, duration=60.0).run()
    assert a["event_hash"] != b["event_hash"]


def test_admission_hook_and_extended_metrics():
    sc = small_scenario()
    X = placement(sc)
    base = Sim(sc, X, seed=1, warmup=0.0, duration=60.0).run()
    assert base["n_rejected"] == 0 and base["p50_makespan"] <= base["p95_makespan"] <= base["p99_makespan"]
    assert 0 <= base["slo_ok"] <= base["n_completed"]
    drop_half = lambda sim, req: req.id % 2 == 0                   # reject every second request
    r = Sim(sc, X, seed=1, warmup=0.0, duration=60.0, admission=drop_half).run()
    assert r["n_rejected"] > 0 and r["n_completed"] + r["n_rejected"] == r["n_arrived"] and r["n_unfinished"] == 0


def test_exec_sampler_hook_changes_service_times():
    sc = small_scenario()
    X = placement(sc)
    fast = Sim(sc, X, seed=1, warmup=0.0, duration=60.0, exec_sampler=lambda f, rng: 0.01).run()
    base = Sim(sc, X, seed=1, warmup=0.0, duration=60.0).run()
    assert fast["avg_makespan"] < base["avg_makespan"]
    assert fast["n_unfinished"] == 0


def test_adjuster_may_skip_reconfiguration():
    class Noop:
        next_interval = 5.0
        def run(self, sim):
            return None
    sc = small_scenario()
    r = Sim(sc, placement(sc), adjuster=Noop(), seed=1, warmup=0.0, duration=60.0).run()
    assert r["n_adjust"] == 0 and r["n_noop_adjust"] >= 10 and r["cold_starts"] == 0


def test_retry_throttle_default_is_identical_and_throttled_run_completes():
    sc = small_scenario()
    X = placement(sc)
    base = Sim(sc, X, seed=1, warmup=0.0, duration=60.0).run()
    same = Sim(sc, X, seed=1, warmup=0.0, duration=60.0, retry_min_interval=0.0).run()
    assert base["event_hash"] == same["event_hash"]
    thr = Sim(sc, X, seed=1, warmup=0.0, duration=60.0, retry_min_interval=1.0).run()
    assert thr["n_unfinished"] == 0 and thr["n_completed"] == base["n_completed"]


def test_retry_cap_bounds_attempts_per_round():
    sc = small_scenario()
    X = placement(sc)
    sim = Sim(sc, X, seed=1, warmup=0.0, duration=60.0, retry_max_attempts=2)
    class R:  # five waiting requests that can never be placed
        pass
    calls = []
    sim._plan = lambda r: (calls.append(r) or False)
    sim.waiting.extend([R() for _ in range(5)])
    sim._retry_waiting()
    assert len(calls) == 2 and len(sim.waiting) == 5                  # only 2 attempted; all 5 still waiting (round-robin)
    full = Sim(sc, X, seed=1, warmup=0.0, duration=60.0)
    calls2 = []
    full._plan = lambda r: (calls2.append(r) or False)
    full.waiting.extend([R() for _ in range(5)])
    full._retry_waiting()
    assert len(calls2) == 5                                           # default unchanged


def test_retry_event_does_not_livelock_on_float_rounding():
    """Regression (2026-10-14): (t + 1.0) - t < 1.0 for t = 7.1997616808981535; the retry event used to re-schedule itself at
    the same timestamp forever. Now the event retries unconditionally and the clock advances."""
    import heapq
    t0 = 7.1997616808981535
    assert (t0 + 1.0) - t0 < 1.0                                       # the rounding case that triggered the bug
    sc = small_scenario()
    sim = Sim(sc, placement(sc), seed=1, warmup=0.0, duration=60.0, retry_min_interval=1.0, retry_max_attempts=10)
    sim.events.clear()
    sim._plan = lambda r: False                                        # waiting requests can never be placed
    sim.waiting.extend([object(), object()])
    sim._last_retry, sim.now = t0, t0 + 0.5
    sim._maybe_retry()                                                 # too early: schedules a retry at t0 + 1.0
    assert len(sim.events) == 1
    for _ in range(100):                                               # the old code never left t0 + 1.0
        if not sim.events:
            break
        t, _, kind, a, b, c = heapq.heappop(sim.events)
        sim.now = t
        getattr(sim, "_ev_" + kind)(a, b, c)
    assert sim.n_retry_rounds == 1 and not sim.events and not sim._retry_pending


def test_stuck_clock_guard_raises_instead_of_hanging():
    import pytest
    sc = small_scenario()
    sim = Sim(sc, placement(sc), seed=1, warmup=0.0, duration=60.0)
    sim.events.clear()
    def loop(a, b, c):
        sim._at(sim.now, "loop")                                       # an event that re-schedules itself at the same time
    sim._ev_loop = loop
    sim._at(1.0, "loop")
    with pytest.raises(RuntimeError, match="livelock"):
        sim.run()


def test_reroute_without_room_waits_instead_of_crashing():
    """A-25b (2026-10-14): the request's node lost its instance and the only node holding the function has no free storage.
    Old behaviour: RuntimeError. Now the request waits (1 s polls) and moves as soon as room appears."""
    import heapq
    import numpy as np
    from dfps.model import Workflow
    from dfps.sim import Req, Run
    from tests.helpers import tiny_sim
    wf = Workflow.from_edges(0, 2, [(0, 1)], [0, 1], {(0, 1): 20.0}, 20.0)
    sim = tiny_sim([[1, 0], [0, 1]], [1.0, 1.0], [1.0, 1.0], esc_mb=100.0, wf=wf)   # f0 only on node 0, f1 only on node 1
    sim.events.clear()
    r = Req()
    r.id, r.wf, r.origin, r.t_arr, r.t_done = 0, wf, 0, 0.0, None
    r.plan, r.pending, r.left = {0: 0, 1: 0}, [0, 0], 2
    run = Run(r, 1, 0)                                                 # task 1 (f1) planned on node 0, which has no f1
    sim.storage_used[0] += run.total
    sim.storage_used[1] = sim.esc[1]                                   # node 1 (the only f1 holder) is full
    sim._enqueue(run, 0)
    assert sim.n_parked == 1 and run.node == 0 and len(sim.events) == 1
    sim.storage_used[1] = 0.0                                          # room frees up
    for _ in range(10):
        if not sim.events:
            break
        t, _, kind, a, b, c = heapq.heappop(sim.events)
        sim.now = t
        getattr(sim, "_ev_" + kind)(a, b, c)
        if run.node == 1 and run in sim.queue[1][1] or (run.node == 1 and sim.inst[1][1][0].run is run):
            break
    assert run.node == 1 and sim.n_rerouted == 1
    assert np.isclose(sim.storage_used[0], 0.0)                         # states moved off node 0
