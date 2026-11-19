"""Queue-aware root selection with F6's non-root arrival plan."""
from collections import Counter

import numpy as np

from .dispatchers import transfer_only
from .solution import IDLE


def queue_aware_roots(sim, request):
    """Price transfer plus queue wait for each root without revising other tasks."""
    plan = transfer_only(sim, request)
    if plan is None:
        return None
    workflow = request.wf
    free = sim.esc - sim.storage_used
    for task, node in plan.items():
        free[node] -= workflow.input_total(task)
    assigned = Counter()
    idle_counts = getattr(sim, "_late_idle", None)
    for root in workflow.roots:
        function, size, previous = workflow.ft[root], workflow.input_total(root), plan[root]
        free[previous] += size
        eligible = np.flatnonzero((sim.cnt[function] > 0) & (free >= size - 1e-9))

        def score(node):
            idle = (idle_counts[node][function] if idle_counts is not None else
                    sum(i.state == IDLE and i.run is None for i in sim.inst[node][function]))
            queued = len(sim.queue[node][function]) + assigned[function, node]
            wait = (0.0 if idle > queued else
                    (queued + 1 - idle) * sim.exec_time[function] / sim.cnt[function, node])
            transfer = sim.net.stt(size, request.origin, node)
            return wait + transfer, transfer, node

        node = min(map(int, eligible), key=score, default=previous)
        plan[root] = node
        assigned[function, node] += 1
        free[node] -= size
    return plan
