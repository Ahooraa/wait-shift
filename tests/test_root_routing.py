from types import SimpleNamespace

import numpy as np

from dfps.dispatchers import transfer_only
from dfps.model import Workflow
from dfps.root_routing import queue_aware_roots
from dfps.solution import BUSY, IDLE
from testbed import frozen_live


def root_routing_state():
    workflow = Workflow.from_edges(0, 2, [(0, 1)], [0, 1], {(0, 1): 1.0}, 1.0)
    hops = np.array([[0, 1], [1, 0]])
    net = SimpleNamespace(h=hops, bw=10., epd=0., stt=lambda size, a, b: hops[a, b]*size/10.)
    sim = SimpleNamespace(net=net, cnt=np.ones((2, 2), dtype=int), esc=np.array([3., 3.]),
                          storage_used=np.zeros(2), fst_vec=lambda f: np.zeros(2),
                          exec_time=np.ones(2), _late_idle=[[0, 1], [1, 1]],
                          queue=[[[object()], []], [[], []]])
    return sim, SimpleNamespace(wf=workflow, origin=0)


def test_a_less_busy_root_can_move_without_changing_downstream_assignments():
    sim, req = root_routing_state()
    assert transfer_only(sim, req) == {0: 0, 1: 0}
    assert queue_aware_roots(sim, req) == {0: 1, 1: 0}
    assert not sim.storage_used.any()


def test_queue_aware_root_requires_storage_and_a_replica():
    sim, req = root_routing_state()
    sim.esc[1] = .5
    assert queue_aware_roots(sim, req) == {0: 0, 1: 0}
    sim.esc[1] = 3.
    sim.cnt[0, 1] = 0
    assert queue_aware_roots(sim, req) == {0: 0, 1: 0}


def test_uncached_idle_count_selects_the_same_root():
    sim, req = root_routing_state()
    del sim._late_idle
    sim.inst = [[[SimpleNamespace(state=BUSY, run=object())], []],
                [[SimpleNamespace(state=IDLE, run=None)], []]]
    assert queue_aware_roots(sim, req) == {0: 1, 1: 0}


def test_f7_keeps_f6_placement_configuration():
    assert frozen_live.ARMS["frozen7"] == frozen_live.ARMS["frozen6"]
