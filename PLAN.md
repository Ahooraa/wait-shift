# DFPS re-implementation plan

**Paper:** B. Zolfaghari, S. Abrishami, A. Rasoolzadegan, B. Javadi, "Dynamic Function Placement and
Request Scheduling of Serverless Workflows in Edge Environment," *IEEE Transactions on Services
Computing*, 2025 (accepted author version, not fully edited), DOI 10.1109/TSC.2025.3592226. 13 pages.
No code released.

**Implementation status:** see `STATUS.md` (phases 0-5 done; open items in `DEVIATIONS.md`).

**Goal:** a faithful, runnable re-implementation of DFPS (initial placement with NSGA-II, request
scheduling by graph pattern matching, periodic replacement and rescheduling with simulated annealing)
and of its baselines. It should reproduce the paper's *trends* (Figs. 5–7) and be usable later as a
fair baseline in other studies.

**Tags:**
- **[PAPER p.X §/Eq/Alg/Tab]**: stated in the paper, with location.
- **[ERRATUM]**: the printed formula or algorithm contradicts the paper's own text or mathematics (§3).
- **[MISSING A-xx]**: needed to run but not given; default listed in §10.
- **[INFERRED]**: follows from the paper but isn't written explicitly.
- **[FIG≈]**: value read off a plot.

---

## 0. Caution and fairness rules (read first; these are binding)

This re-implementation exists to represent DFPS **as its authors described it**, so it can serve as
a fair baseline. Being "helpful" by quietly improving it is the main risk.

1. **Do not change any setting the paper states.**
   - Every constant in §4 (Table 2, Np = 100, the 4 s replacement interval, 50 MB/s, the arrival-rate
     ranges, the scaling factors, the network sizes, the application counts, 10 workloads) must be used
     exactly as printed.
   - The values live in one file (`config/paper_constants.yaml`) with the page reference next to each.
   - A test (`tests/test_paper_constants.py`) asserts that every value equals the paper value. Changing
     one must make that test fail.
2. **Use the paper's terms and names. Don't rename or reinterpret them.**
   - Code identifiers and docs use the paper's symbols: `ecc_k, esc_k, EWF_k, ESS_k, FRQ_lk, fn_lk, FT,
     SS, STT, FST, FRN, AET, RG, EF, FAN, FEN`, proximity level / proximity criterion / proportionality
     criterion, P-graph / R-graph, g-node / g-edge, relocation gain, replacement interval,
     *ready-to-execute*, makespan.
   - Baseline names are exactly **SR, SG, Heu, RL**. Metrics are exactly **average makespan,
     utilization, number of cold starts**.
   - Don't substitute "latency" for makespan or "autoscaling" for replacement.
3. **Implement algorithms line by line.**
   - Alg. 1 and Alg. 2 are implemented in the same order, with the same choices (random node, least
     utilized function, random new function from F, vicinity of k hops, ready-to-execute requests only,
     the same acceptance structure).
   - Each code line carries a comment with the algorithm line number (`# Alg.1 l.12`).
   - Don't add extra moves, smarter tie-breaking, caching that changes decisions, or early stopping.
4. **Errata are never fixed silently.**
   - Where the printed formula contradicts the paper's own prose or mathematics (§3), implement **both**:
     - `literal`: exactly as printed;
     - `prose`: the minimal change that makes it do what the paper's text says it does.
   - Primary results use `prose` **only for the four errata E-1, E-2, E-5, E-6**, and are always shown
     next to `literal`.
   - Anything else the paper states explicitly (for example Alg. 2 returning the *last* solution) stays
     literal, even if a "better" variant exists. Better variants may only appear as clearly labelled
     extra experiments.
5. **Fill missing details neutrally.**
   - A missing detail ([MISSING A-xx]) gets the most neutral, standard default: uniform over a stated
     range, standard NSGA-II/SA settings from the cited references, and so on.
   - It's recorded in §10, in `DEVIATIONS.md`, and in every output file's metadata, and it gets a
     sensitivity run.
   - Never pick a default because it makes DFPS (or a baseline) look better or worse.
6. **Double-check before trusting anything:**
   - **Two-source transcription:** every equation, algorithm and constant is read from the PDF text
     layer and from a rendered page image (≥ 200 dpi). They must agree; this plan has already done that
     once (§3–§5).
   - **Worked numeric example per equation:** each one in `tests/test_equations.py`, computed by hand
     (or independently in a notebook) and asserted in code.
   - **Independent re-derivation** of the queueing formulas (§5.3) against a textbook source *and* a
     small Monte-Carlo M/M/c simulation (within 2%).
   - **Second reading of Alg. 1–2** by a different person (or a second pass on another day), ticking off
     each line against the code.
   - **Reference check:** every cited source used for an assumption is opened and confirmed.
7. **Same conditions for every method:** the same simulator, topology, workloads, seeds, capacities,
   cold-start model, state sizes and metric code for DFPS, SR, SG, Heu and RL. No method gets extra
   tuning that the others don't.
8. **Report honestly:**
   - Reproduction is judged on the paper's **orderings and trends** (§9.4), not exact numbers, because
     many details are missing.
   - Every mismatch is reported with its likely cause (which A-xx or E-x). Results are never adjusted
     to match the paper's figures.

---

## 1. What DFPS is, in one page

- **Setting [PAPER p.4 §3.1]:** a multi-access edge computing network of `Ne` edge nodes managed by a
  central controller. User requests for `Nw` workflow types (DAGs) arrive via the nearest base station.
- **Edge node [PAPER p.4]:** `e_k = ⟨ecc_k, esc_k, EWF_k, ESS_k⟩`:
  - container capacity `ecc_k`: number of function instances (each container has a fixed CPU/memory size);
  - storage capacity `esc_k`: space for intermediate states;
  - warm functions `EWF_k`;
  - stored states `ESS_k`.

  Per function and node: request queue `FRQ_lk` and number of instances `fn_lk`.
- **Execution [PAPER p.5]:**
  - When all parent tasks of `t_ij` are done and their states have reached the designated node e_k,
    the task is *ready-to-execute*. Its request enters `FRQ_lk` (with `f_l = FT(t_ij)`) and waits for
    one of the `fn_lk` instances.
  - The output state is transferred directly to, and stored on, the nodes where the subsequent tasks
    are scheduled. Consumed input states are removed after execution.
- **Objective [PAPER p.5 §3.2]:** minimise the average workflow makespan `WM(w_i)` (request received →
  last task completed), subject to container and storage capacities.
- **Three components [PAPER §4]:**
  1. **Initial placement (§4.1):** NSGA-II over instance counts per node and function. Objectives:
     proximity criterion and proportionality criterion. Runs once, before requests.
  2. **Request scheduling (§4.2):** per request, select instances by graph pattern matching (P-graph =
     workflow, R-graph = warm instances). g-edge weight = FST (M/M/c) + STT.
  3. **Dynamic replacement and rescheduling (§4.3):** every replacement interval, simulated annealing
     (Alg. 2) over neighbour moves (Alg. 1). Evaluation EF = sum of relocation gains.

---

## 2. Verification log of this plan (what was checked, and how)

| Item | Text layer | Rendered page (≥ 200 dpi) | Status |
|---|---|---|---|
| Eq. 1–2 (STT, etd) | p.5 | p.5 | Agree. Note: prose says `eh_kk'`, equation uses `h_kk'` (same quantity, cosmetic) |
| Eq. 3 (proportionality) | p.6 | p.6 | Agree: **signed** sum, printed without abs → E-1 |
| Eq. 4 (FEN) | p.6 | p.6 | Agree |
| Eq. 5–6 (FST, FRN) | p.7 | p.7 | Agree; Eq. 6 lacks P0 → E-2 (re-derived, §5.3) |
| Eq. 7 (Sol0) | p.8 | p.8 | Agree |
| Eq. 8 (RG) | p.8 | p.8 | Agree |
| Alg. 1 (29 lines) | p.8 | p.8 | Agree line by line; l.23 "FRQ_rs" → E-6 |
| Alg. 2 (15 lines) | p.9 | p.9 | Agree line by line; l.8 test → E-5; returns `Sol_t` (last) |
| Table 2 (10 rows) | p.10 | p.10 | Agree (§4) |
| §4.4 constants (Np = 100, No = 2) | p.9 | p.9 | Agree |
| §5.1–5.2 settings | p.9–10 | p.9–10 | Agree (§4) |
| Refs [18] [28] [38] [39] [42] [43] [44] [45] | p.12–13 | — | Confirmed titles and venues (§11) |

---

## 3. Errata and ambiguities (verified; handled as in §0 rule 4)

### 3.1 Errata: printed formula or algorithm contradicts the paper's own text or mathematics

| ID | Where | What is printed | Why it can't be what the authors meant | `prose` variant (default for primary results) |
|---|---|---|---|---|
| **E-1** | p.6 Eq. 3 | `Σ_{f_l∈F} (FAN(f_l) − FEN(f_l))` | Every chromosome fills each node exactly (`Σ_l X[k][l] = ecc_k`), so `Σ_l FAN = Σ_k ecc_k`. By Eq. 4, `Σ_l FEN = Σ_k ecc_k × Σ_l μ_l/Σ_l' μ_l' = Σ_k ecc_k`. So Eq. 3 is **identically 0** and can't measure "the alignment between the number of instances … and the average execution time" (p.6 text). | `Σ_l abs(FAN(f_l) − FEN(f_l))`, the smallest change that measures misalignment. `literal` = signed sum (constant 0, so NSGA-II effectively optimises proximity only). |
| **E-2** | p.7 Eq. 6 | `FRN = (λ/μ)^fn·λμ / ((fn−1)!(fn·μ−λ)²) + λ/μ` | The paper says the queue is "modeled as an M/M/c queue" and uses "queue theory formulas" [40]. The standard M/M/c mean number in system is `L = Lq + λ/μ` with `Lq = P0·(λ/μ)^c·λμ / ((c−1)!(cμ−λ)²)`. The printed formula is exactly this **without P0** (derivation in §5.3). | Standard Erlang-C `L` with P0. `literal` = printed formula. |
| **E-5** | p.9 Alg. 2 l.7–9 | `if Δ < 0 then if random(0,1) >= e^(−Δ/T) then Sol_t ← Sol_{t−1}` | With Δ < 0, `−Δ/T > 0`, so `e^(−Δ/T) > 1 > random(0,1)`. The revert **never** happens and every worse move is accepted. That contradicts the prose (p.8): the algorithm "decides whether to move … based on a probability function, … reducing the likelihood of selecting worse solutions over time". | Revert if `random(0,1) >= e^(Δ/T)`, i.e. accept a worse move with probability `e^(Δ/T)` (Metropolis, [41]). `literal` = as printed. |
| **E-6** | p.8 Alg. 1 l.23 | "Add r_q to the end of FRQ_rs" | Lines 19–25 move requests of the **new** function f_n from neighbours to e_s (p.8 text: "reschedule some of the requests for f_n … to e_s"). f_r has no instance there for them. | Append to `FRQ_ns` (only meaningful reading; there is no `literal` variant, since it would put f_n requests in an f_r queue). |

### 3.2 Points that are *not* errata: keep them literal

| ID | Where | Statement | Handling |
|---|---|---|---|
| L-1 | p.9 Alg. 2 l.14, p.8 text | Simulated annealing returns the **current (last)** solution, not the best seen | Literal: return last. A "best-seen" variant is an optional, labelled extra experiment only. |
| L-2 | p.8 Alg. 1 l.4 | `f_n ← random function from F` (not excluding f_r) | Literal: any function in F. If `f_n = f_r`, the move is a no-op swap and is still evaluated as Alg. 1 prescribes. |
| L-3 | p.10 Tab. 2, p.10 text | Replacement interval **4 s**, chosen by a 1–9 s sweep | 4 s in all primary runs; the 1–9 s sweep reproduced as in the paper. (p.7 also says the interval "is set to the average critical path length"; that's reported, not used.) |
| L-4 | p.9 §4.4 | NSGA-II population **Np = 100**; 2 objectives | Exactly 100 and 2 objectives. |

### 3.3 Ambiguities (the paper allows more than one reading; pick neutrally, document, run sensitivity)

| ID | Where | Ambiguity | Default |
|---|---|---|---|
| Q-1 | p.6 vs p.7 Eq. 4/6 | μ_l is called "average execution time" (p.7), but Eq. 6 uses it as a **rate**. Eq. 4 weights instance counts by μ_l, where longer execution means more instances (p.6 text), so a time. | Eq. 4: `μ_l` = mean execution time. Eq. 5–6: rate = `1/μ_l`. The symbols are kept, and the conversion is explicit in code. |
| Q-2 | p.5 §3.1 vs p.6 §4.2 vs p.7 | Storage check: "sufficient space to store the **input** states of those tasks" (p.5) vs "enough space to store the intermediate state **generated for** that function" (p.6) vs "states required for executing a function request" (p.7) | Check space for the task's **input** states at its node (p.5/p.7 agree). The output-state reading is a sensitivity variant. |
| Q-3 | p.7 | g-edges exist only between parent and child functions, so **root tasks** have no service-time weight, and the input transfer from the user isn't modelled | A virtual source g-node at the request's base station, edges to root candidates, weight = FST + STT of the request input. Labelled as an addition [MISSING A-09]. |
| Q-4 | p.7 Eq. 5 | FST undefined when `λ_lk = 0` or the queue is unstable (`fn_lk·μ ≤ λ`) | `λ = 0`: FST = 1/rate (execution time). Unstable: FST = (queued requests + 1) × exec time / fn_lk. [MISSING A-10] |
| Q-5 | p.6 | Proximity level: is level 0 the node itself (its own warm functions)? | Level 0 = e_k itself, level 1 = its neighbours, and so on (breadth-first search from e_k). Variant: start at the neighbours. |
| Q-6 | p.8 Alg. 1 l.3 | "Least utilized" = fewest requests in the past interval (p.8 text). Ties are unspecified. | Ties broken uniformly at random (neutral, keeps the algorithm's randomness). |
| Q-7 | p.10 Tab. 2 vs p.9 text | Table 2: "Incoming request rate 0.5–100 per second". Text: per-application Poisson means of 200–700 ms (Uniform), or 50–100 ms for about 20% of apps and 2–4 s for the rest (Pareto), scaled by 0.25…2. These don't map one-to-one; for example, Uniform at ×0.25 gives about 0.36–1.25 requests/s per app. | Generate arrivals **exactly as the text describes**. Log the resulting per-app and total rates and note any values outside 0.5–100/s. Don't rescale. |
| Q-8 | p.8 Alg. 1 l.5–7 | Is a request *running* on the removed f_r instance affected? | Not affected: it finishes, and then the instance disappears. |

---

## 4. Constants the paper states: must not change (`config/paper_constants.yaml`)

| Constant | Value | Source |
|---|---|---|
| Function run-time | 2–10 s | p.10 Tab. 2 (range from [45]) |
| Cold-start delay | 2–10 s | p.10 Tab. 2 (range from [45]) |
| Intermediate state size | 10–50 MB | p.10 Tab. 2 |
| Number of workflows | 15 (scenario 3: 5 → 40) | p.10 Tab. 2, §5.2.3 |
| Number of edge nodes | 80 (scenario 2: 20 → 160) | p.10 Tab. 2, §5.2.2 |
| Average bandwidth between nodes | 50 MB per second | p.10 Tab. 2 |
| Edge node function capacity (`ecc_k`) | 5–25 | p.10 Tab. 2 |
| Edge node storage capacity (`esc_k`) | 10–30 GB | p.10 Tab. 2 |
| Incoming request rate | 0.5–100 per second (see Q-7) | p.10 Tab. 2 |
| Replacement interval | 4 s (sweep 1–9 s) | p.10 Tab. 2, p.10 text |
| Propagation delay `epd` | 0 (negligible) | p.5 |
| Uniform workload | Poisson, per-app mean U-range 200–700 ms | p.9 |
| Pareto workload | ~20% of apps: mean 50–100 ms; others: 2–4 s | p.9 |
| Arrival scaling factors | 0.25, 0.50, 0.75, …, 2.00 (8 points) | p.10 §5.2.1 |
| Workloads per experiment | 10 (comparable parameters) | p.10 §5.2 |
| Statistics | Repeated-measures ANOVA, p < 0.05 | p.10 §5.2 |
| NSGA-II population `Np` | 100 | p.9 §4.4 |
| NSGA-II objectives `No` | 2 | p.9 §4.4 |
| Alibaba jobs kept | execution time under one minute | p.9 §5.1 |
| Topology generator | GT-ITM | p.9 §5.1 [44] |
| Simulator used by authors | EdgeCloudSim, extended | p.9 §5.1 [42] |

**Ranges are only ranges.** The paper never states a distribution, so drawing uniformly within each
range is a [MISSING A-01] default, not a paper fact.

---

## 5. Model, equations and algorithms, implementation level

### 5.1 Objects

```
Workflow   w_i = <T_i, S_i>;  FT(t_ij); SS(s_ij)                    [PAPER p.4]
Function   f_l ∈ F; μ_l (mean execution time, Q-1); cold-start delay
EdgeNode   e_k = <ecc_k, esc_k, EWF_k, ESS_k>; fn_lk; FRQ_lk         [PAPER p.4]
Network    hop counts h_kk' (shortest path), bw                     [PAPER p.5, p.7]
Request    one execution of w_i from a base station; static plan {t_ij → e_k}
```

### 5.2 State transmission [PAPER p.5 Eq. 1–2]

`STT(s_ij, e_k, e_k') = h_kk' × (epd_kk' + etd_kk')`, `etd_kk' = SS(s_ij) / bw`, `epd = 0`, `bw = 50 MB/s`.

Notes:
- The serialisation time is multiplied by the hop count (store-and-forward per hop). **Keep it literal.**
- Same node: `h = 0`, so STT = 0.
- No link sharing or contention is modelled in the paper [INFERRED]. Don't add contention to primary runs.

**Worked example (test):** SS = 30 MB, h = 3, bw = 50 MB/s gives 3 × (0 + 0.6) = **1.8 s**.

### 5.3 Service-time estimate [PAPER p.7 Eq. 5–6] (re-derived)

Standard M/M/c with arrival rate λ, per-server rate μ, c servers, offered load a = λ/μ, ρ = a/c < 1:
- `P0 = [ Σ_{n=0}^{c−1} a^n/n! + a^c/(c!(1−ρ)) ]^−1`
- `Lq = P0 · a^c · ρ / (c! (1−ρ)²)`

Substituting `ρ = λ/(cμ)` and `(1−ρ)² = (cμ−λ)²/(cμ)²`:
- `Lq = P0 · a^c · λμ / ((c−1)! (cμ−λ)²)`
- `L = Lq + λ/μ`, and `FST = L/λ` by Little's law.

The paper's Eq. 6 equals this L **with P0 removed** (E-2).

**Worked example (test):** λ = 1.5/s, mean execution 1 s (μ = 1/s), c = 2: a = 1.5, ρ = 0.75,
P0 = 1/(1 + 1.5 + 2.25/(2·0.25)) = 1/7 ≈ 0.142857.
- Lq = (1/7)·2.25·0.75/(2·0.0625) = **1.928571**; L = **3.428571**; FST = **2.285714 s**.
- Paper-literal Eq. 6: 2.25·1.5/(1·0.25) + 1.5 = **15.0**, so FST = **10.0 s**.

The test asserts both, and a 10⁶-arrival M/M/2 simulation must match the `prose` value within 2%.

### 5.4 Initial placement: NSGA-II [PAPER p.5–6 §4.1, Fig. 3, ref. 38]

- **Chromosome [p.5–6, Fig. 3a]:** one placement vector per node, length |F|. Entry = number of
  instances of that function (0 if absent). **Each vector sums to `ecc_k`.** Vectors are concatenated
  in a fixed node order.
- **Initial population [p.6]:** Np = 100 random chromosomes respecting `ecc_k`. Distribution
  [MISSING A-02: uniform multinomial over F].
- **Proximity criterion [p.6]:** for each e_k, breadth-first search over neighbours; at each level,
  add the warm functions found; proximity level = first level at which the visited functions equal F
  (Q-5). Criterion = Σ_k proximity level. If F is never covered: [MISSING A-03: diameter + 1].
- **Proportionality criterion [p.6 Eq. 3–4]:** E-1 (`prose`: abs; `literal`: signed). FAN(f_l) =
  available instances of f_l in the network; FEN(f_l) per Eq. 4 with μ_l as mean execution time (Q-1).
  **Lower is better for both** [p.6].
- **Selection [p.6]:** non-dominated sorting and the crowded-comparison operator [38].
- **Crossover [p.6, Fig. 3b]:** two parents; a random subset of edge nodes; their placement vectors are
  swapped, giving two offspring. Subset size distribution [MISSING A-04: each node with p = 0.5].
- **Mutation [p.6]:** on one edge node, +1 for a randomly chosen function and −1 for another randomly
  chosen function on the same node. The decreased function must have ≥ 1 instance (needed to keep
  counts non-negative) [INFERRED]. Rates [MISSING A-05: standard NSGA-II defaults from [38], crossover
  probability 0.9, mutation probability 1/(chromosome length) per gene, adapted to one move per
  mutated offspring; documented].
- **Survivor selection [p.6]:** combine parents and offspring, re-sort, and keep the best Np (elitist).
  Generations Ni [MISSING A-06: 250, a common NSGA-II budget; sensitivity 100/500].
- **Final choice [p.6]:** take the non-dominated set; divide each criterion by its minimum within
  that set; pick the lowest sum of the two normalised criteria. (With `literal` E-1 the minimum is 0;
  handle as 0/0 → treat the proportionality term as 1 for all, documented.)
- **Library:** own implementation, cross-checked on a toy instance against `pymoo`'s NSGA-II with the
  same operators.

### 5.5 Request scheduling: graph pattern matching [PAPER p.6–7 §4.2, Fig. 4, ref. 39]

- **P-graph [p.7]:** the workflow DAG. Each task is a labelled g-node; repeated function types get
  unique labels.
- **R-graph [p.7], built for each request:**
  - For each e_k and each task t of the requested workflow with `FT(t) ∈ EWF_k`: g-node `(t, e_k)`.
  - Remove it if e_k lacks storage (Q-2).
  - **g-edge** `(u, e_k) → (v, e_k')` for every workflow edge u → v. **Weight = FST(FT(v), e_k') + STT(s_uv, e_k, e_k')**, with the hop count from the shortest path [p.7].
  - Root handling: Q-3.
- **Matching [p.7, ref. 39 Cheng, Zeng, Yu, ICDE 2013, "Top-k graph pattern matching over large
  graphs"]:** "a number of minimum spanning trees are first found by searching for the pattern graph
  within the reference graph. Then, the missing paths in the spanning trees are substituted with the
  shortest alternative paths … The match with the least total graph edge weight is selected" [p.7].
  - **Before coding this step, read [39] and transcribe its algorithm** (two-source rule, §0.6). The
    paper's description is brief, and our version must follow [39], not our own idea of matching.
  - Planned structure, to be confirmed against [39]:
    1. enumerate the top-k lowest-weight matches of a spanning tree of the P-graph in the R-graph;
    2. for each, add the weights of the non-tree P-graph edges (the "missing paths");
    3. return the lowest total.
  - k and the number of spanning trees [MISSING A-07].
  - **Test oracle:** brute force over all assignments for DAGs with ≤ 8 tasks; report how often and by
    how much the matching differs (no tuning to close the gap).
- **The plan is static once made [p.4–5].** Only the replacement/rescheduling step changes it.

### 5.6 Dynamic replacement and rescheduling: simulated annealing [PAPER p.7–9 §4.3, Alg. 1–2, Eq. 7–8]

- **Every replacement interval** (4 s, L-3), build `Sol0 = {⟨EWF_k, ESS_k, ∪_l FRQ_lk⟩ | 1 ≤ k ≤ Ne}` (Eq. 7).
- **ComputeNeighbor (Alg. 1, literal except E-6):**
  - l.2: `e_s` = random edge node.
  - l.3: `f_r` = least utilized function on e_s (fewest requests in the past interval, Q-6).
  - l.4: `f_n` = random function from F (L-2).
  - l.5–6: replace one f_r instance by f_n; `fn_rs ← fn_rs − 1`. The new instance pays the cold-start
    delay of f_n before serving [INFERRED].
  - l.7–18: if `fn_rs = 0`, move every r_q in FRQ_rs to the node e_s' with the lowest `AET(r_q, e_k)`
    among nodes with f_r ∈ EWF_k. Append to the end of FRQ_rs'.
    - `AET` = input/output state transfer time of r_q to/from the node + actual service time considering
      the current requests waiting there [p.8].
  - l.19–26: for every e_s' in the vicinity of e_s (≤ k hops [MISSING A-08]) with f_n ∈ EWF_s', move
    each **ready-to-execute** r_q ∈ FRQ_ns' to e_s if `RG(r_q, e_s', e_s) = AET(r_q, e_s') − AET(r_q, e_s) > 0`
    (Eq. 8). Append to FRQ_ns (E-6).
- **EF(Sol_t) [p.8]:** sum of the relocation gains of **all** relocations of f_r and f_n requests in
  the transition. Negative values are possible.
- **DynamicAdjustment (Alg. 2):** `T ← T_max`; while `T > T_min`: neighbour → Δ = EF → acceptance (E-5:
  `prose`/`literal`) → decrease T "according to schedule" → **return `Sol_t` (last, L-1)**.
  - T_max, T_min and the cooling schedule [MISSING A-11: geometric cooling T ← 0.95·T, T_max and T_min
    set so one adjustment performs a fixed iteration budget (default 100), documented; sensitivity
    50/200].
- **Apply** the returned solution: placement changes (with cold starts) and moved requests (with their
  pending input states, [MISSING A-12]).

### 5.7 Cold starts, instances, lifecycle
- **SR/SG:** the initial placement is warm at t = 0; with no runtime changes, cold starts = 0
  [PAPER p.10 §5.2.1].
- **DFPS:** cold starts only for instances added by replacement.
- **No idle-timeout expiry is described** [INFERRED: instances persist until replaced].
- **Execution-time distribution in the simulator** [MISSING A-13]: exponential with mean μ_l. This
  matches the paper's own queueing assumption (p.7: "each instance … processes requests following an
  exponential distribution with an average execution time of μ_l"). Sensitivity: deterministic.

---

## 6. Simulator

The authors extended EdgeCloudSim (Java) [p.9]. Plan: a **Python discrete-event simulator that
implements exactly the model in §5** (easy to audit, easy to reuse). It must not add effects the
paper doesn't model (no link contention, no propagation delay, no keep-alive expiry) in primary runs.
Optional later: cross-check a few configurations against EdgeCloudSim.

**Events:**
- request arrival → scheduler;
- state arrival → when all inputs are in, the task is ready-to-execute and enqueued;
- instance free → next request;
- task done → send output states, delete consumed inputs;
- instance warm (after cold start);
- replacement tick (every 4 s);
- λ_lk update ("every few seconds" [p.7], [MISSING A-14: every 1 s over a 5 s window]).

**Package layout:**

```
dfps/
  config/paper_constants.yaml     every §4 value with page reference (read-only in code)
  config/assumptions.yaml         every A-xx default (logged into results)
  model.py, network.py, workload.py, queueing.py, nsga2.py, matching.py, sa.py, sim.py
  baselines/static.py (SR, SG), heu.py (Xu et al. 2023), rl.py (Yang et al. 2025)
  experiments/run.py, stats.py (AnovaRM), plots.py (Figs. 5–7 layout)
  tests/test_paper_constants.py, test_equations.py, test_alg1_lines.py, test_alg2_lines.py,
        test_matching_vs_bruteforce.py, test_invariants.py
  DEVIATIONS.md                   every E-x / Q-x / A-xx choice and why
```

---

## 7. Data and scenario pipeline

- **Workflows [p.9]:** Alibaba Cluster Trace [43] (Guo et al., IWQoS 2019, which analyses Alibaba's
  2018 trace). Keep applications with execution time **under one minute**; 15 workflows (5 → 40).
  - Which trace version and fields: [INFERRED: the 2018 `batch_task` table, where DAG dependencies are
    encoded in task names such as `M3_1_2`; verify against [43] before use].
  - How the 15 are sampled [MISSING A-15: uniformly at random among eligible jobs, seed-controlled;
    10 different draws = the 10 workloads].
- **Function types [MISSING A-16]:** the trace has no function identities. Default: a global pool F,
  and each task's type is drawn uniformly from F, so types can be shared across workflows (as F, EWF_k
  and the reference graph imply). |F| [MISSING A-17: 30]. Sensitivity: 15 / 60, and types unique per
  workflow.
- **Per-function values:** run-time and cold start within 2–10 s (Table 2), per function [MISSING
  A-01: uniform]. State sizes within 10–50 MB per workflow edge [A-01: uniform]. Request input size
  [MISSING A-18: same range].
- **Topology [p.9]:** GT-ITM [44], with node counts 20–160. Use the original GT-ITM tool if available;
  otherwise a documented transit-stub generator [MISSING A-19: parameters]. Per node: ecc_k within
  5–25, esc_k within 10–30 GB [A-01: uniform]. Base stations and request origins [MISSING A-20: one
  base station per edge node; the origin node is uniform].
- **Arrivals [p.9]:** exactly as in Q-7 (Poisson, per-app means as stated, scaling factors as stated).
  Run length and warm-up [MISSING A-21].

---

## 8. Baselines (same conditions for all, §0 rule 7)

| Name (exact) | What it is | Source to read before implementing |
|---|---|---|
| **SR** (Static-Random) | Random initial placement, no dynamic adjustment | DFPS p.9 |
| **SG** (Static-Genetic) | NSGA-II initial placement, no dynamic adjustment | DFPS p.9 |
| **Heu** | Placement and scheduling simultaneously per function request (incl. state placement) | [18] Z. Xu et al., "Stateful serverless application placement in MEC with function and state dependencies," IEEE Trans. Computers 72(9):2701–2716, 2023 |
| **RL** | DRL-based function offloading (multi-objective) | [28] Y. Yang et al., "Multi-objective deep reinforcement learning for function offloading in serverless edge computing," IEEE TSC 18(1):288–301, 2025 |

- SR and SG use the same request scheduler as DFPS [INFERRED from "static versions of the proposed
  algorithm", p.9].
- Heu and RL get their own spec (same two-source procedure) before any code. Use their own published
  settings unchanged.

---

## 9. Validation plan

1. **Constants:** `test_paper_constants.py` (§4) must pass at all times.
2. **Equations:** worked examples (§5.2, §5.3, plus Eq. 3/4 on a 2-node toy, Eq. 8 on a toy), with
   `literal` and `prose` values both asserted.
3. **Algorithms:** line-coverage tests for Alg. 1 (each branch: `fn_rs` hits zero or not, positive or
   non-positive RG, vicinity empty) and Alg. 2 (accept/revert paths for `literal` and `prose`).
4. **Reproduction targets (trends, [FIG≈], 80 nodes, 15 apps, Fig. 5, x = scaling 0.25…2.0):**
   - **Makespan, Uniform:** DFPS ≈ SR ≈ SG (about 10 → 60–70 s) ≪ RL (≈ 45 → 265 s) ≪ Heu (≈ 200 → 400 s).
   - **Makespan, Pareto:** DFPS lowest (≈ 30 → 155 s) < RL (≈ 150 → 280) ≈ Heu (≈ 160 → 295) ≈ SG
     (≈ 185 → 285) < SR (≈ 220 → 340).
   - **Utilization, Uniform:** DFPS ≈ 28% → peak ≈ 75% → ≈ 70%; RL ≈ 57 → 43%; SG ≈ 29 → 43 → 34%;
     SR ≈ 28 → 37 → 31%; Heu ≈ 20% flat.
   - **Utilization, Pareto:** DFPS ≈ 58 → 52%; RL ≈ 50 → 40%; Heu ≈ 35 → 33%; SR, SG ≈ 10–12%.
   - **Cold starts, Uniform:** RL ≈ 57k → 48k; Heu ≈ 50k; DFPS ≈ 8k → 1.5k; SR/SG 0.
     **Pareto:** RL ≈ 50k → 42k; Heu ≈ 35k → 38k; DFPS ≈ 5k → 1.5k; SR/SG 0.
   - **Fig. 6:** makespan falls with network size for all methods; SG ≈ DFPS under Uniform; DFPS best
     under Pareto; SG < SR.
   - **Fig. 7:** makespan rises with the number of applications.
   - **Acceptance:** same method ordering and trend direction. Absolute values will differ because of
     the A-xx defaults; report the differences, never tune toward them (§0 rule 8).
5. **Erratum impact:** run `literal` vs `prose` for E-1, E-2 and E-5, and report how much each changes
   DFPS's results.
6. **Sensitivity** to every A-xx default with plausible alternatives (§10).

---

## 10. Missing details: neutral defaults (each logged, each with a sensitivity run)

| ID | Missing detail | Neutral default | Sensitivity |
|---|---|---|---|
| A-01 | Distribution within Table 2 ranges | Uniform | Truncated normal |
| A-02 | Random initial chromosome | Uniform multinomial over F per node | — |
| A-03 | Proximity when F is never covered | Diameter + 1 | Large constant |
| A-04 | Crossover node-subset size | Each node with p = 0.5 | 0.2 / 0.8 |
| A-05 | Crossover/mutation probabilities | NSGA-II standard [38]: 0.9 / one move per mutated offspring with p = 1/Ne | ±50% |
| A-06 | Generations Ni | 250 | 100 / 500 |
| A-07 | Top-k and number of spanning trees in [39] | Per [39] once read; otherwise k = 10, 5 trees | 1 / 20 |
| A-08 | Vicinity radius k (Alg. 1 l.19) | 2 hops | 1 / 3 |
| A-09 | Root/input handling in the R-graph (Q-3) | Virtual source at the base station | No source term |
| A-10 | FST when λ = 0 or unstable (Q-4) | As in Q-4 | Large constant |
| A-11 | SA T_max, T_min, cooling | Geometric 0.95, 100 iterations per adjustment | 50 / 200 |
| A-12 | Moving pending input states with moved requests | Moved, with STT cost | Not moved |
| A-13 | Execution-time distribution in the simulator | Exponential, mean μ_l (paper's queueing assumption) | Deterministic |
| A-14 | λ_lk update | Every 1 s over a 5 s window | 1 s / 10 s windows |
| A-15 | Choice of 15 workflows | Uniform among eligible jobs; 10 draws | — |
| A-16 | Task → function type mapping | Global pool, uniform | Unique per workflow |
| A-17 | Pool size |F| | 30 | 15 / 60 |
| A-18 | Request input state size | Within 10–50 MB (A-01) | 0 MB |
| A-19 | GT-ITM parameters | Transit-stub, documented | Waxman |
| A-20 | Base stations and request origin | One per node; origin uniform | Clustered |
| A-21 | Run length and warm-up | 300 s of arrivals + drain; first 30 s excluded | 600 s; no warm-up |
| A-22 | Utilization definition | Busy instance-time / (Σ ecc_k × time) | Busy / placed instances |

---

## 11. References used by this plan (confirmed from the paper's reference list)

- [18] Xu et al., IEEE Trans. Computers 72(9), 2023: Heu baseline.
- [28] Yang et al., IEEE TSC 18(1), 2025: RL baseline.
- [38] Deb et al., "A fast and elitist multiobjective genetic algorithm: NSGA-II," IEEE TEVC 6(2), 2002.
- [39] Cheng, Zeng, Yu, "Top-k graph pattern matching over large graphs," ICDE 2013.
- [40] Medhi, *Stochastic Models in Queueing Theory*, 2002.
- [41] Aarts and Korst, *Simulated Annealing and Boltzmann Machines*, 1989.
- [42] Sonmez et al., "EdgeCloudSim," Trans. Emerging Telecom. Tech., 2018.
- [43] Guo et al., "Who limits the resource efficiency of my datacenter: an analysis of Alibaba datacenter traces," IWQoS 2019.
- [44] Zegura et al., "How to model an internetwork," INFOCOM 1996 (GT-ITM).
- [45] Shahrad et al., "Serverless in the wild," USENIX ATC 2020: source of the run-time and cold-start ranges.

---

## 12. Work plan

| Phase | Content | Exit criterion | Est. effort |
|---|---|---|---|
| 0 | Skeleton; `paper_constants.yaml` + test; `assumptions.yaml`; `DEVIATIONS.md` | Constants test green | 0.5 day |
| 1 | Network (GT-ITM), workload (Alibaba parsing, filter, function types, arrivals per Q-7) | Scenario stats logged (DAG sizes, per-app rates) | 1.5 days |
| 2 | Simulator core (§6), with SR using a trivial scheduler | Invariants pass (capacity, storage, conservation) | 2 days |
| 3 | Queueing (§5.3, both variants + Monte-Carlo check); read [39] → matching (§5.5) + brute-force oracle | Equation tests pass; matching report | 2–3 days |
| 4 | NSGA-II (§5.4, both E-1 variants) → SG | Toy cross-check vs pymoo; SG ≤ SR in sanity runs | 1.5 days |
| 5 | Alg. 1 + Alg. 2 line by line (§5.6, E-5 variants, L-1/L-2 literal) → DFPS | Line-coverage tests; second reading done | 2 days |
| 6 | Spec + implement Heu from [18] | Its own spec reviewed; runs | 2–3 days |
| 7 | Spec + implement RL from [28] | Its own spec reviewed; trained and evaluated | 3–4 days |
| 8 | Figs. 5–7, interval sweep, ANOVA, erratum impact, sensitivity | Report: matches and mismatches with causes | 2 days |

**Total:** about 3–4 weeks. Phases 0–5 give DFPS, SR and SG (about 10 working days).
