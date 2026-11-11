"""The calibration experiment's logic, on loopback agents (the real numbers come from the laptops)."""
import numpy as np
import pytest

from testbed import calibrate as C
from testbed.agentclient import AgentClient
from testbed.livesim import LiveLink
from tests.live_helpers import TOKEN, start_agent_processes, stop

SPEED = 10.0


@pytest.fixture(scope="module")
def agents():
    procs, ports = start_agent_processes(3, SPEED)
    yield ports
    stop(procs)


def test_run_rate_pairs_requests_and_reports_the_overhead(agents):
    clients = {f"a{i}": AgentClient("127.0.0.1", p, TOKEN) for i, p in enumerate(agents)}
    link = LiveLink(clients, LiveLink.blocks(6, list(clients)), speed=SPEED, payload_scale=100)
    r = C.run_rate(link, rate=2.0, app="660.map-reduce", ne=6, duration=15.0, warmup=2.0, drain_s=30.0)
    assert r["n_window_requests"] > 5 and r["n_completed"] == r["n_arrived"] > 0
    for k in ("overhead_mean_ms", "overhead_p99_ms", "overhead_per_task_ms", "hub_cpu_fraction", "inbox_max", "agent_timer_lateness_max_ms"):
        assert r[k] is not None and np.isfinite(r[k])
    assert r["tasks_per_s"] == pytest.approx(2.0 * 10)                              # map-reduce has 10 tasks
    assert r["sim_p50_ms"] > 0 and r["live_p50_ms"] > 0


def test_verdict_applies_the_stated_criteria():
    base = {"n_completed": 100, "n_arrived": 100, "late_events": 0, "n_events_total": 1000, "qfree_overhead_p95_ms": 10.0, "p99_ratio": 1.0, "hub_cpu_fraction": 0.3}
    rows = [dict(base, rate_per_s=5), dict(base, rate_per_s=20, qfree_overhead_p95_ms=15.0), dict(base, rate_per_s=50, qfree_overhead_p95_ms=80.0),
            dict(base, rate_per_s=100, late_events=300), dict(base, rate_per_s=150, p99_ratio=2.0), dict(base, rate_per_s=200, hub_cpu_fraction=0.97)]
    assert C.verdict(rows) == 20
    assert [r["sustained"] for r in rows] == [True, True, False, False, False, False]
    assert C.verdict([dict(base, rate_per_s=5, n_completed=50)]) is None
    assert C.verdict([dict(base, rate_per_s=5), {"rate_per_s": 10, "failed": "x", "sustained": False}]) == 5       # a failed rate is never sustained


def test_queue_free_ignores_requests_that_waited():
    class Sim:
        trace = {"tasks": [(1, 0, 0, 0, 0, 1.0, 1.0, 1.1, 0), (1, 0, 1, 0, 0, 1.1, 1.1, 1.2, 0), (2, 0, 0, 0, 0, 2.0, 2.5, 2.6, 0), (2, 0, 1, 0, 0, 2.6, 2.6, 2.7, 0)]}
    assert C.queue_free(Sim) == {1}
