"""Edge network: hop counts h_kk', bandwidth bw, state transmission time STT (p.5 Eq.1-2).

STT(s, e_k, e_k') = h_kk' * (epd_kk' + etd_kk'),  etd_kk' = SS(s) / bw,  epd = 0 (p.5).
The serialisation time is multiplied by the hop count (store-and-forward per hop): kept literal.
GT-ITM itself is not available; `transit_stub` is a documented transit-stub generator (A-19)."""
from __future__ import annotations

import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import shortest_path

from .constants import PAPER


class Network:
    def __init__(self, ne, edges, bw=None):
        self.ne = ne
        self.edges = sorted({(min(a, b), max(a, b)) for a, b in edges if a != b})
        self.bw = float(PAPER["average_bandwidth_mb_s"]["value"] if bw is None else bw)
        self.epd = float(PAPER["propagation_delay_s"]["value"])
        a = np.zeros((ne, ne))
        for u, v in self.edges:
            a[u, v] = a[v, u] = 1.0
        self.adj = a
        h = shortest_path(csr_matrix(a), unweighted=True, directed=False)
        if not np.isfinite(h).all():
            raise ValueError("network is not connected")
        self.h = h.astype(np.int64)
        self.diameter = int(self.h.max())
        self.neighbors = [np.flatnonzero(a[k]) for k in range(ne)]

    def stt(self, size_mb, k, k2):
        """Eq. 1-2 for one state of size SS = size_mb."""
        return float(self.h[k, k2] * (self.epd + size_mb / self.bw))

    def stt_matrix(self, size_mb):
        """STT between every ordered pair of nodes for a state of the given size."""
        return self.h * (self.epd + size_mb / self.bw)


def transit_stub(ne, rng, p_transit=0.6, p_stub=0.42, stub_size=(4, 8)):
    """Single transit domain of Nt nodes; stub domains of 4-8 nodes (random connected graphs) hang off the transit
    nodes in round-robin order, each attached by one edge (A-19)."""
    nt = max(2, ne // 16)
    edges = []
    nodes_left = ne - nt

    def connected_random(nodes, p):
        order = list(nodes)
        rng.shuffle(order)
        es = [(order[i], order[int(rng.integers(0, i))]) for i in range(1, len(order))]  # random spanning tree
        for i in range(len(order)):
            for j in range(i + 1, len(order)):
                if rng.random() < p:
                    es.append((order[i], order[j]))
        return es

    edges += connected_random(range(nt), p_transit)
    nxt, t = nt, 0
    while nodes_left > 0:
        size = int(min(nodes_left, rng.integers(stub_size[0], stub_size[1] + 1)))
        stub = list(range(nxt, nxt + size))
        if size > 1:
            edges += connected_random(stub, p_stub)
        edges.append((int(rng.choice(stub)), t % nt))
        nxt += size
        nodes_left -= size
        t += 1
    return Network(ne, edges)
