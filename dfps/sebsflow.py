"""SeBS-Flow workflow definitions -> static DAGs, plus the DFPS Fig. 1 workflow (plan faas-edge-adaptation, "Workflows").

SeBS-Flow (Schmid et al., EuroSys 2025) defines workflows as JSON phase machines (task, map, parallel, loop, repeat, switch);
the fan-out of a `map` is decided at run time from the input array (p. 5), so a static DAG needs a parameter instantiation.
We use the configuration the paper itself reports (Table 4, p. 7; see knowledge/sources/schmid-2025-sebs-flow.md):

  Video Analysis  : F=10 frames, batch 5  -> 2 parallel `analyse`                         (4 functions in the paper)
  Trip Booking    : failure injected in the last confirm -> 4 forward + 3 compensations  (7 functions)
  MapReduce       : N=3 mappers, M=5 reducers                                            (9 functions)
  ExCamera        : 5 segments (30 frames, chunks of 6)                                   (16 functions)
  Machine Learning: K=2 classifiers                                                      (3 functions)
  1000Genome      : N=5 individuals, P=6 populations                                     (19 functions)

Phase-to-phase edges: SeBS-Flow phases are AND-joins (p. 4). We connect consecutive phases one-to-one when both are maps of
equal width (segment i feeds segment i), otherwise all-to-all (fan-out / fan-in). A `loop` over k items is k sequential
tasks. Per-function durations and per-edge payloads are NOT published (the paper gives workflow-level runtimes and total
transfer volumes only), so the simulator draws them from the plan's ranges like for the Alibaba DAGs.
Checked against Table 4 (2026-10-15): function counts match for Video (4), Trip Booking (7), ExCamera (16), ML (3),
1000Genome (19); MapReduce unrolls to 10 (split + 3 map + shuffle + 5 reduce; the paper says 9 without giving the edge list).
Critical paths match for Video (3), Trip Booking (7 with the failure path), ML (2); they differ for ExCamera (8 here vs 6:
the rebase loop is modelled as fully sequential) and 1000Genome (3 here vs 4). The paper does not publish edge lists.
"""
from __future__ import annotations

import json
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BASE = os.path.join(ROOT, "input", "data", "workflows", "sebs-flow", "600.workflows")

# width of every map (by state name) and iterations of every loop, per benchmark (Table 4)
CONFIG = {
    "650.vid": {"map": {"analyse-map": 2}},
    "6200.trip-booking": {"failure_at": "confirm"},
    "660.map-reduce": {"map": {"map-state": 3, "reduce-state": 5}},
    "680.excamera": {"map": {"encode-state": 5, "reencode-state": 5}, "loop": {"rebase-state": 5}},
    "690.ml": {"map": {"train-state": 2}},
    "6100.1000-genome": {"map": {"individuals": 5, "frequency": 6, "mutation_overlap": 6}},
}
EXPECTED_FUNCTIONS = {"650.vid": 4, "6200.trip-booking": 7, "660.map-reduce": 9, "680.excamera": 16, "690.ml": 3,
                      "6100.1000-genome": 19}


class _Builder:
    def __init__(self):
        self.names, self.edges = [], []

    def task(self, name):
        self.names.append(name)
        return len(self.names) - 1

    def link(self, prev, cur):
        """prev, cur: lists of task ids (the exits of the previous phase, the entries of this one)."""
        if not prev:
            return
        if len(prev) == len(cur) and len(cur) > 1:                 # map -> map of equal width: one-to-one
            self.edges += list(zip(prev, cur))
        else:                                                       # fan-out / fan-in (AND-join)
            self.edges += [(p, c) for p in prev for c in cur]


def _phase(b, name, st, cfg):
    """Expand one phase; returns (entry task ids, exit task ids)."""
    kind = st["type"]
    if kind == "task":
        t = b.task(st["func_name"])
        return [t], [t]
    if kind == "map":
        width = cfg.get("map", {}).get(name)
        if width is None:
            raise KeyError(f"no map width configured for {name}")
        inner = st["states"][st["root"]]
        ids = [b.task(inner.get("func_name", st["root"])) for _ in range(width)]
        return ids, ids
    if kind in ("loop", "repeat"):
        k = cfg.get("loop", {}).get(name, st.get("count", 1))
        ids = [b.task(st["func_name"]) for _ in range(int(k))]
        b.edges += list(zip(ids[:-1], ids[1:]))
        return ids[:1], ids[-1:]
    if kind == "parallel":
        ent, ext = [], []
        for br in st["parallel_functions"]:
            e, x = _machine(b, br, cfg)
            ent += e
            ext += x
        return ent, ext
    raise ValueError(f"unsupported phase type {kind}")


def _machine(b, sm, cfg):
    """Walk a phase machine from its root along `next` (with the configured failure injection). Returns (entries, exits)."""
    states, cur, prev, entries = sm["states"], sm["root"], None, None
    seen = set()
    while cur is not None:
        if cur in seen:
            raise ValueError("cycle in phase machine")
        seen.add(cur)
        st = states[cur]
        if st["type"] == "map" and "states" in st and st["root"] in st["states"] and st["states"][st["root"]]["type"] == "map":
            raise ValueError("nested maps not supported")
        e, x = _phase(b, cur, st, cfg)
        b.link(prev, e)
        entries = e if entries is None else entries
        prev = x
        if cfg.get("failure_at") == cur and "failure" in st:
            cur = st["failure"]
        elif st["type"] == "switch":
            cur = st.get("default")
        else:
            cur = st.get("next")
    return entries or [], prev or []


def sebsflow_dag(bench):
    """One SeBS-Flow benchmark as a DAG dict in the same format as workload.load_alibaba_batch_task (tasks in topological
    order: the expansion order is already topological)."""
    d = json.load(open(os.path.join(BASE, bench, "definition.json"), encoding="utf-8"))
    b = _Builder()
    _machine(b, d, CONFIG[bench])
    # 1000Genome nests maps inside `parallel` branches; their widths are configured by the inner state names
    return dict(job=f"sebsflow-{bench}", n=len(b.names), edges=sorted(set(b.edges)), span=float("nan"), names=b.names)


def dfps_fig1_dag():
    """DFPS Fig. 1 (p. 1): face detection -> duplicate check -> (thumbnail || indexing) -> persist metadata."""
    return dict(job="dfps-fig1-image-processing", n=5, edges=[(0, 1), (1, 2), (1, 3), (2, 4), (3, 4)], span=float("nan"),
                names=["face_detection", "check_face_duplicate", "thumbnail", "indexing", "persist_metadata"])


def all_named_dags():
    return [sebsflow_dag(b) for b in CONFIG] + [dfps_fig1_dag()]
