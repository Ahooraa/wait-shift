# Real testbed on 4 laptops: design (draft, 2026-11-11)

Status (2026-11-11): **phase 1 done** (preflight, bootstrap, pinned environment, setup guide, hub-side connect tool and `fleet.py`; all four
laptops enrolled and set up for measured runs except text boot). **Phase 2 built, not yet run on the laptops:** `agent.py` (node agent:
container slots with cold starts, task timers, per-node storage, real state transfers paced to the nominal Eq.1-2 time, JSONL log),
`agentclient.py` (hub side), `agentcheck.py` + `fleet.py agents start|stop|status|check` (acceptance run on the real laptops), 12
loopback tests including four agents transferring between every pair. Found and fixed during testing: a background task that Python
could garbage-collect (a transfer then hung silently with no event), and errors that were not reported.
**Phase 3 built, tested on loopback only:** `livesim.py` (`LiveSim` for `Sim`, `LiveOnDemandSim` for `OnDemandSim`) runs the simulators' own logic on a
real clock; the controller, dispatchers and baselines are unchanged. Time is the wall clock since the run started; the cold start, task run,
state transfer and relocation the simulator only models are done by the agents and come back as the simulator's own events, so real network
delays and the controller's real computing time show up in the makespans. The only change to the simulators is a hook `Sim._stt(...)`
at the 7 places that schedule a state move (8 of 8 event hashes identical before and after: static, SA, join-bind, Heu on two seeds).
Tests: static, DFPS-style reconfiguration (the agents' containers equal the simulator's at the end), Heu on demand, a broken agent
connection is fatal, and (slow) six seeds against the plain simulator: mean p50 makespan ratio 1.035, p99 1.079. Limits: speed above 1
is a test option (the controller's real planning time then looks `speed` times longer in simulated time); the simulator's own capacity and
storage accounting is authoritative (the agents are told not to enforce either); the agents on the laptops must be synced and restarted to
get the new `store` option; not yet run on the laptops; the workload is still the old mixed one, the SeBS-only generator is not built.
Phases 4-6 not started.
Written against the code at commit a41144a plus the commits on this branch.

## Goal
Run DFPS (B*), its variants and the baselines (SR, SG, Heu, RL, ...) on real machines and measure real makespan, cold starts,
data movement and controller overhead, under the same scenarios and seeds as the simulator, so that simulator and testbed can
be compared point by point.

## What the simulator gives us
- `Scenario` (dfps/model.py): functions (runtime 2-10 s, cold start 2-10 s), workflow DAGs (state sizes 10-50 MB), network
  (80 edge nodes, ~50 MB/s), per-node container capacity `ecc` (5-25) and storage `esc`, and an arrival list `(t, workflow, origin)`.
- `Sim` (dfps/sim.py): the whole system state (instances, queues, lambda estimates, storage) and the hooks every controller uses:
  `adjuster` (periodic re-layout, every 4 s), `dispatcher` (per-request placement), `relocate`, `add_instance`,
  `remove_instance`, `apply_placement`.
- Controllers (dfps/o3s.py, controllers.py, dispatchers.py, heu.py, rl.py, ondemand.py) act only through those hooks.

## Architecture: hybrid, control plane unchanged, data plane real
```
laptop A (coordinator + node agent)      laptops B, C, D (node agents)
  LiveSim(Sim)  <--- TCP/msgpack --->      agent: hosts ~20 logical edge nodes
  controllers (unchanged)                  container slots, real state transfers,
  workload driver, logger                  real execution timing, local logs
```
- **`LiveSim(Sim)`** (new, testbed/livesim.py): same state and controller hooks, but the event loop runs on the wall clock
  and the two things the simulator fakes are delegated to agents: *start a task on (node, instance)* and *move a state of S MB
  from node i to node j*. Completion events come back from agents. Controllers need no change, which is what makes the
  comparison against the simulator meaningful. Risk: `Sim` is 900 lines with many extensions; the subclass must override only
  `_start`, the transfer accounting in `relocate`/`_ev_state`, and the clock. To be confirmed by reading `_start`, `_ev_done`,
  `_ev_state`, `relocate` line by line before coding.
- **Node agent** (testbed/agent.py): hosts the logical edge nodes assigned to its laptop (80 nodes over 4 laptops = 20 each).
  Per node: `ecc_k` container slots, a storage budget, and a bandwidth/latency shaper for links to other logical nodes,
  using the Eq.1-2 path model. Transfers are real bytes over the real LAN, rate-limited per link, so contention is real.
- **Container emulation.** A "cold start" occupies a slot for `cold_start` seconds (real wait plus a real process/thread spawn);
  a task runs for the sampled execution time. Default: wall-clock wait (sleep), not CPU burn, because ~300 concurrent
  containers per laptop would otherwise turn the laptop's CPU into the bottleneck and distort every method differently.
  The agent records its own scheduling lateness so distortion is measured, not assumed.
- **Time: real time only (k = 1)**, decided 2026-11-11 because it is the most defensible choice for a journal paper. A run is
  300 s + 30 s warm-up + drain, about 7 min; 3 load levels x 6 methods x 10 workloads is about 21 h. No time compression.
- **Payload scaling (WiFi).** The 4 laptops share one WiFi channel, which cannot carry the roughly 100 MB of intermediate state per
  request the scenarios imply. Transfers therefore send real bytes at 1/s of the nominal size (s to be chosen, e.g. 100) while the
  shaper delays each transfer as if the full size crossed a 50 MB/s link (Eq.1-2). Real network jitter and serialization stay in
  the loop; WiFi capacity does not become the bottleneck. s is reported with every result and WiFi RTT/throughput is logged per run.

## Reproducibility and environment control (check, don't change)
`testbed/preflight.py`, run on every laptop, prints a JSON report and exits non-zero on any mismatch against the first machine:
kernel version, CPU model and governor, swap state, chrony offset and source, boot target, auto-update state, Python and
package versions (numpy 1.26.4, numba 0.60.0, ...), repo commit and a checksum of `input/data` and `results` inputs, free disk,
NIC speed, measured pairwise round-trip time and bandwidth between laptops. It never changes a system setting; a separate
list of the commands you run yourself goes in `testbed/SETUP.md`.

## Measurement and outputs
- Per-task records (request id, task, node, enqueue/start/finish, cold flag, bytes moved) written locally by each agent and merged
  by the coordinator using chrony-synced timestamps; clock offsets recorded per run.
- Result files use the existing schema (`mover_impl`, `event_hash` where meaningful) plus `testbed: {speed, laptops, preflight_hash}`.
- Real runs are not deterministic, so `event_hash` equality is not expected; validation compares distributions (makespan
  percentiles, cold starts, MB moved) against the simulator over repeated seeds.

## Phases
1. **Preflight + inventory** (small): `preflight.py`, `SETUP.md`, pairwise network measurement.
2. **Agent and transport** (medium): agent, shaper, real transfer, local logging; loopback test with 4 agents on one machine.
3. **LiveSim with simple methods** (medium): SR, SG (static) and Heu / RL (on-demand) through `LiveSim`; first end-to-end run, 1 laptop.
4. **DFPS B\*** (medium): `adjuster` path; controller overhead measured for real.
5. **Experiment driver** (small): grid over seeds/loads/methods, scheduling across laptops, resume, merge.
6. **Validation** (medium): testbed vs simulator on a small grid; report the gap before any claim.
Each phase ends with tests that run without the laptops (loopback) and a short real run.

## Decisions (2026-11-11)
1. **Coordinator** = the process that runs the controllers (what `Sim` plus the controllers are in the simulator). It runs on one
   of the 4 machines next to that machine's logical nodes. Because NSGA-II and annealing are CPU-heavy, the coordinator gets
   reserved cores (taskset) and its machine hosts the same number of logical nodes as the others; controller wall time is
   measured and reported, so any interference is visible. Open: which machine (the one with most cores/RAM).
2. **Network: WiFi.** Mitigated by payload scaling above; per-run RTT/throughput logged; repeat runs; wired Ethernet preferred
   if any machine has a port (not required).
3. **Logical nodes: 20 (5 per machine)**, the smallest node count the paper itself tests (range 20-160), about 300 container slots
   in total, emulated as lightweight tasks, not processes (fits 8 GB machines). 80 nodes is a possible later extension. The
   simulator scenario for the comparison is regenerated with 20 nodes and the same rates as the paper's scenario 2.
4. **Time: real time, k = 1.**
5. **RAM 8 or 16 GB, mixed.** Slots per logical node are identical on all machines (fairness); a machine's memory is not what
   limits emulated containers. `preflight.py` reports cores and RAM; the coordinator goes on the strongest machine.

## Control strategy: everything from the hub (decided 2026-11-11)
User strategy: keep the experiment simple and automated, control all devices from this laptop (the hub, `edge-1`, the one with
Claude), and avoid commands run by hand on the others. Consequences for the plan:
- **Enrollment is the only manual part**, once per laptop: connect to the 5 GHz house network (tick "Make available to other users" so Wi-Fi
  survives text mode), set the hostname, paste ONE line. That line (an extended `join.sh`) installs `openssh-server`, authorises the
  hub's dedicated SSH key (a new ed25519 key on the hub, private half never leaves it), and installs a root helper (below).
- **Reach by name, not address:** `edge-N.local` (mDNS, avahi runs on Ubuntu, also in text mode) with the registry's IP as fallback,
  so a changed DHCP address does not break control.
- **Fleet controller on the hub: `testbed/fleet.py` + `testbed/cluster.json` (built 2026-11-11; the real file with addresses and hardware addresses is local and git-ignored because the repository is public, `cluster.example.json` shows the format).** Commands, run in parallel with
  per-laptop results over a dedicated SSH key (`~/.ssh/testbed_ed25519`): `list`, `status` (preflight on all plus the
  cross-machine comparison), `run -- CMD`, `sync` (code to the hub's commit via a git bundle), `env [--fix]` (check packages, copy the
  hub's venv), `reboot --yes` (waits until each is back), `discover [--write]` (re-find laptops when addresses change).
  Verified on the real four laptops: `list`, `status`, `run`, `env`, `discover`. Not yet run for real: `sync` (needs a commit
  first), `reboot`, `env --fix`, `discover --write`; these have unit tests (tests/test_fleet.py). Still to build: `apply-settings`,
  `text-mode`, `agents start/stop`, `collect`.
- **Enrolment as done (2026-11-11):** instead of the extended `join.sh`, the three laptops were enrolled by hand once:
  `openssh-server` installed, the hub's key installed with `ssh-copy-id`, SSH password login turned off, hostnames set, passwordless
  `sudo` for the user. The Python environment was copied from the hub over SSH because `files.pythonhosted.org` did not resolve
  on the network (queries for that one name time out on every DNS server, from every laptop).
- **One clock for all laptops (2026-11-11):** with each laptop on its own internet time servers the laptops differed by 11 to 14 ms
  (the servers disagree by tens of ms). `fleet.py clock setup` makes the hub serve time to the LAN and the other three follow only the hub
  (their pools are commented out, original config kept as `chrony.conf.testbed-orig`); measured by `agents check`, the offsets fell to
  0.4 to 0.7 ms (the method's own resolution is about 1 ms over Wi-Fi). Absolute time follows the hub's upstream, which does not matter for
  relative timestamps. If the hub's address changes the others lose their source: reserve its address in the router. `clock undo` reverts.
- **Two interfaces on edge-2:** Ethernet (used for control) and Wi-Fi (used by experiments) are both
  connected; the experiment traffic could take the wired path. Unplug Ethernet before Wi-Fi experiments and set `ssh` in
  `cluster.json` to the Wi-Fi address (`discover --write`). `cluster.json` keeps both addresses.
- **Root on the other laptops:** the three laptops have passwordless `sudo`, so system settings can be applied over SSH directly;
  the restricted-helper option stays open for later hardening. Settings still need the user's approval of the exact list first
  (`SETUP.md` Part 2 is the list).
- **No GitHub login on the others:** code reaches them from the hub (bundle now, rsync later).
- `SETUP.md` is the fallback and the record of what the automation does; new steps are added to the controller first.

## Workload: SeBS-Flow only (decided 2026-11-11)
All workflows in testbed runs, and in the simulator runs they are compared with, are the 6 SeBS-Flow applications at the paper's
Table 4 configuration (`dfps/sebsflow.py`: Video Analysis 4 functions, Trip Booking 7, MapReduce 10, ExCamera 16, Machine
Learning 3, 1000Genome 19). No Alibaba DAGs and no DFPS Fig. 1 workflow. Container sizes come from each workflow's `memory`
setting (config.json), a single source and unit. Arrivals repeat the six applications at fixed total load (rho = 0.5, 0.7, 0.85);
a "workload" is a seed (arrival times, origins, popularity weights). (Superseded the same day: per-function durations, cold starts, state sizes and memory now
come from the measured SeBS-Flow replication data, see DEV-T4 in `DEVIATIONS.md`, `sebs_scenario.py` and `sebs_profiles.json`.) Because the mean task count is about 9.8
instead of 4.5, the arrival rate for a given load is lower than in the earlier scenarios. Logged as DEV-T1 to DEV-T3 in
`DEVIATIONS.md`, since it departs from the frozen plan's workflow list.

## Still to do before measured runs
- Build the SeBS-only scenario generator for the simulator first (same seeds), and run it there before any laptop run.
- Freeze the experiment grid, metrics and stop rule in the plan (project methodology is `quantitative`: pre-registration required).
- Tag results with `capacity_model`, `mover_impl`, `place_impl` and controller version as the project conventions require.
- Read `_start`, `_ev_done`, `_ev_state`, `relocate` in `dfps/sim.py` line by line to confirm `LiveSim` only has to override
  task start, transfer accounting and the clock.

## Measured SeBS-Flow data (decided 2026-11-11)
The SeBS-Flow replication package (Zenodo 10.5281/zenodo.14907321, CC BY 4.0) holds one measured row per function invocation. The testbed
uses it for everything the workload needs: `derive_sebs_profile.py` makes the small committed table `sebs_profiles.json` (the 622 MB dataset
stays outside the repository), `sebs_scenario.py` builds the scenario (DAGs from `dfps/sebsflow.py`, whose task counts match the measured
invocations for five of six applications) and a duration sampler from the measured quantiles. Open points are DEV-T4 limits and DEV-T5
(request mix, timing resolution) in `DEVIATIONS.md`. The DFPS paper's 2-10 s ranges are a later sensitivity run.
