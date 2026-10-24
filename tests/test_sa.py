"""Alg.1 / Alg.2 line coverage with hand-computed values (PLAN.md section 9.3)."""
import numpy as np
import pytest

from dfps.sa import SimulatedAnnealing
from dfps.solution import Sol
from tests.helpers import ScriptedRng, inject, tiny_sim

# line network 0-1-2-3 ; functions f0 (mu 4, cold 3), f1 (mu 2, cold 5), f2 (mu 6, cold 7)
# instances: node0: f0,f1   node1: f0,f2   node2: f1,f2   node3: f0,f1
X = [[1, 1, 0], [1, 0, 1], [0, 1, 1], [1, 1, 0]]
MU, COLD = [4.0, 2.0, 6.0], [3.0, 5.0, 7.0]


def make(**kw):
    return tiny_sim(X, MU, COLD, **kw)


def test_aet_hand_computed():
    sim = make()
    run = inject(sim, task=1, node=2)                         # f1 request, 20 MB input, located on node 2
    sol = Sol(sim)
    # evaluate on node 3 (1 hop): input STT = 1*(20/50)=0.4 ; node3 has an idle f1 -> service 0 + mu 2 ; leaf task: no output
    assert sol.aet(run, 3, ahead=0) == pytest.approx(0.4 + 2.0)
    # one request ahead: the idle instance serves it first (finishes at 2), then rq: 2 + 2 = 4
    assert sol.aet(run, 3, ahead=1) == pytest.approx(0.4 + 4.0)
    # on its own node (2): no input transfer
    assert sol.aet(run, 2, ahead=0) == pytest.approx(2.0)


def test_aet_includes_output_transfer():
    sim = make()
    run = inject(sim, task=0, node=0, plan={0: 0, 1: 3})      # task 0 (f0) -> child planned on node 3
    sol = Sol(sim)
    # at node 1: input 20MB from node0 : 0.4 ; service f0 idle: 4 ; output 20MB node1->node3 (2 hops): 0.8
    assert sol.aet(run, 1, ahead=0) == pytest.approx(0.4 + 4.0 + 0.8)


def test_alg1_forced_relocation_and_ef():
    """e_s = node 2, f_r = f2 (only instance on node 2 -> fn_rs reaches 0), f_n = f0.
    Two queued f2 requests on node 2 must move to the warm f2 on node 1 (the only other node with f2)."""
    sim = make()
    sim.req_count[:] = 5
    sim.req_count[2, 2] = 0                                   # f2 on node 2 is the least utilised function there
    r1 = inject(sim, task=0, node=2, wf=None)                 # f0 task so use FT mapping: need f2 -> build with ft
    sim.queue[2][r1.f].clear()                                # (helper injects f0; clear and build f2 requests below)
    from dfps.model import Workflow
    wf2 = Workflow.from_edges(1, 1, [], [2], {}, 20.0)
    sim.sc.workflows.append(wf2)
    rq1, rq2 = inject(sim, 0, 2, wf=wf2), inject(sim, 0, 2, wf=wf2)
    assert rq1.f == 2 and len(sim.queue[2][2]) == 2
    sol = Sol(sim)
    old = [sol.aet(rq1, 2, ahead=0), sol.aet(rq2, 2, ahead=1)]       # in Sol_{t-1}: 6 and 12
    assert old == [pytest.approx(6.0), pytest.approx(12.0)]
    sa = SimulatedAnnealing(seed=0, vicinity=0)               # vicinity 0 -> no pull step
    sa.rng = ScriptedRng(integers=[2, 0])                     # e_s = 2 ; f_n = f0 (index 0)
    sol.begin()
    ef = sa.compute_neighbor(sol, sim)
    # node 1 holds the only other f2 (idle, mu 6): rq1: transfer 20MB 1 hop = 0.4 + 0 + 6 = 6.4 ; rq2 appended after rq1: 0.4+6+6 = 12.4
    assert ef == pytest.approx((6.0 - 6.4) + (12.0 - 12.4))   # forced moves have negative relocation gain here
    assert sol.cnt[2, 2] == 0 and sol.cnt[0, 2] == 1          # f2 instance replaced by an f0 instance on node 2
    assert sol.queue(2, 2) == [] and sol.queue(2, 1) == [rq1, rq2]
    assert sol.node_of(rq1) == 1 and sol.node_of(rq2) == 1


def test_alg1_pull_gain_positive():
    """Replace f_r=f1 (node 0, but node0 also keeps... use ecc) by f_n=f2 on node 0: node 1 (1 hop, vicinity) has a long
    queue of f2 requests -> the ones with positive relocation gain are pulled to node 0."""
    sim = make()
    from dfps.model import Workflow
    wf2 = Workflow.from_edges(1, 1, [], [2], {}, 20.0)
    sim.sc.workflows.append(wf2)
    qs = [inject(sim, 0, 1, wf=wf2) for _ in range(4)]       # 4 f2 requests queued on node 1 (1 f2 instance there)
    sim.req_count[:] = 5
    sim.req_count[1, 0] = 0                                  # f1 is least used on node 0
    sol = Sol(sim)
    sa = SimulatedAnnealing(seed=0, vicinity=1)
    sa.rng = ScriptedRng(integers=[0, 2])                    # e_s = node 0 ; f_n = f2
    sol.begin()
    ef = sa.compute_neighbor(sol, sim)
    assert sol.cnt[1, 0] == 0 and sol.cnt[2, 0] == 1
    moved = [q for q in qs if sol.node_of(q) == 0]
    assert moved and ef > 0                                   # only positive gains are accepted (Eq.8)
    # node 0's new f2 instance is cold (7 s) so it can serve at most the requests that beat the 4-deep queue on node 1
    first = qs[0]
    gain0 = (0.0 + 6.0 * 1) - (0.4 + 7.0 + 6.0)               # rq at index 0 on node1: 6 ; on node 0: 0.4+cold 7+6 = 13.4 -> negative
    assert gain0 < 0 and sol.node_of(first) == 1              # the head of the queue stays (negative gain)


def test_alg2_acceptance_variants():
    sim = make()
    for variant, expect_revert in (("literal", False), ("prose", True)):
        sa = SimulatedAnnealing(seed=0, iterations=1, accept=variant)
        calls = []
        sa.compute_neighbor = lambda sol, s: (calls.append(1), -5.0)[1]     # EF = -5 (worse)
        sa.rng = ScriptedRng(random=[0.99])                                  # random(0,1) = 0.99 >= exp(delta/T)? T=10: exp(-0.5)=0.607
        sol = sa.run(sim)
        assert calls
        assert (sa.stats["reverted"] == 1) == expect_revert, variant


def test_rollback_restores_solution():
    sim = make()
    sol = Sol(sim)
    sol.begin()
    before = (sol.cnt.copy(), sol.free.copy(), list(sol.av(0, 0)))
    sol.set_cnt(0, 0, 5)
    sol.set_av(0, 0, [])
    sol.add_free(1, -10.0)
    sol.rollback()
    assert (sol.cnt == before[0]).all() and (sol.free == before[1]).all() and sol.av(0, 0) == before[2]


def test_f_n_equal_f_r_is_noop_and_last_instance_rejected():
    sim = make()
    sol = Sol(sim)
    sa = SimulatedAnnealing(seed=0)
    sa.rng = ScriptedRng(integers=[0, 0])                    # e_s = 0, f_r = (only candidate choice -> first present = f0), f_n = 0
    assert sa.compute_neighbor(sol, sim) == 0.0              # A-32
    sim2 = tiny_sim([[1, 1, 0], [0, 0, 1]], MU, COLD)        # f2 exists once only, on node 1
    sol2 = Sol(sim2)
    sa2 = SimulatedAnnealing(seed=0)
    sim2.req_count[:] = 5
    sa2.rng = ScriptedRng(integers=[1, 0])                   # e_s = 1 (holds only f2), f_n = f0
    assert sa2.compute_neighbor(sol2, sim2) is None          # A-31: never remove the last instance
