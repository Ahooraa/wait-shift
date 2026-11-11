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

## Experiments per application, cold-start counts (decided 2026-11-11)
Each SeBS-Flow application is its own experiment, so no application dominates (`sebs_scenario.build(apps=[...])`). Cold starts are counted
(`metrics.py`) as well as timed, because the measured cold starts are short and the count is what a controller can reduce at a real cost on an
edge node. Load per application is open (DEV-T7): the millisecond-scale applications need hundreds of requests per second for a realistic
load, and 1000Genome needs runs of over an hour. Both are decisions for the pre-registration.

## Calibration of the testbed (started 2026-11-11)
`calibrate.py` runs one application at increasing request rates in the plain simulator and in `LiveSim` on the agents, pairs the requests by id,
and reports what the testbed adds; the highest rate that keeps the overhead near its low-rate value, with the hub keeping up, is the sustainable
rate and sets the inclusion rule of the pre-registration (DEV-T7). Task durations are drawn with common random numbers (`Sim._exec_s` hook,
`CrnSampler`: the same task of the same request gets the same duration under every controller; event hashes of 8 reference runs unchanged).
Measurements so far (Trip Booking, 20 nodes, static placement, four laptops on Wi-Fi; six calibration runs over 2026-11-11, one run per rate):
- Timers: lateness p99 2 ms, max 3 to 5 ms on every laptop over about 140,000 tasks. Control round trip hub to agent 1 to 4 ms (worst 153 ms).
  Raw TCP connection setup between laptops: 600 connections, none over 0.5 s.
- Hub limit: at 100 requests/s (700 tasks/s) the hub keeps up (CPU 81%, no late events, live p99 makespan 0.99 times the simulator's). At 150 requests/s
  (1,050 tasks/s) it saturates (about 24,700 late events, CPU 91%). Before pooled connections 100 requests/s collapsed (median overhead 23 s).
  So a rate above about 700 tasks/s cannot be driven by the single hub process; the sustainable rate must be taken from repeated runs.
- The paired request-by-request makespan difference is NOT a valid overhead measure under queueing: with heavy-tailed durations the same long task
  blocks different requests in the two systems. Example (50 requests/s): the "2 s p99 overhead" was a long `confirm` task (the stand-in has rare
  multi-second calls) blocking a node with one `confirm` container in both systems; the simulator's own p99 was 2,098 ms, the live system's 2,151 ms.
  The calibration therefore compares only requests that did not queue in either system, plus the ratio of the two makespan distributions.
- Wi-Fi stall episodes: intermittently, for a stretch of time, agent-to-agent transfers take 0.5 to 3.7 s (in one run about 630 transfers over 0.5 s,
  about 345 over 1 s), independent of load: runs at 100 to 200 requests/s had none. Seen in about 4 of 19 runs. Cause not identified (house Wi-Fi
  interference, access point behaviour and others are candidates). The same rate therefore gives very different tails in different runs, and a
  single run per rate cannot define a sustainable rate. Consequences for the protocol: repeat and interleave runs, log per-run network health
  (to be built: per-second Wi-Fi counters and a background latency probe), and pre-register how runs with a stall episode are reported
  (never silently dropped).
- Pooled connections opened at configure time (4 per peer) remove the cost of fresh connections; each new connection is timed in the agent log.
- Also fixed on the way: an earlier run's event readers stole the next run's events (each run now stops its readers).

## Network monitor (built 2026-11-11, not yet run on the laptops)
`netmon.py` runs next to the agents on every laptop and writes one JSON line per second to `~/testbed-logs/netmon-<time>.jsonl`: the Wi-Fi link
state from `iw station dump` (signal, bit rates, and the per-second change of tx retries, tx failures, beacon losses and dropped frames), the change in
TCP retransmitted segments, the load, and a UDP round-trip probe from every laptop to every other (10 per second, independent of the agents and the hub).
The probe separates the two explanations of a stall: if it is clean while the agents' transfers stall, the cause is in our software; if it stalls
too, the network. `fleet.py monitor start|stop|status|collect|report` runs it from the hub; `report` copies the newest monitor and agent logs of every
laptop to a local results folder, merges the impaired seconds into episodes (probe lost or above 100 ms, tx retries above 25% of packets, 3 or more TCP
retransmits, beacon loss, signal below -75 dBm) and counts how many slow agent transfers (over 0.5 s) fall inside an episode of the sender or of any
laptop. Peers are named by laptop, so the logs hold no addresses. The thresholds are initial values, to be checked against the first real data.

### Calibration with the monitors running (2026-11-11, nine runs: 5, 20, 50 requests/s, three times each, interleaved; Trip Booking, 20 nodes)
- Hub and agents: all requests completed in all nine runs; no late hub events, hub CPU 3 to 51%, at most 29 events queued. Queue-free requests were
  slower than in the simulator by a median of 34 to 76 ms (4.7 to 12.6 ms per task; p95 48 to 305 ms); live and simulated p99 makespan agreed within 2 to 4%
  in eight runs (ratio 1.02 to 1.04) and in one run (50 requests/s, the sixth) the live p99 was 2.83 times the simulated one, not explained. So the
  testbed adds roughly 5 to 13 ms per task, which is more than the work of Trip Booking's tasks (milliseconds): for that application it measures
  orchestration as much as work. 350 tasks/s was sustained with margin; 700 tasks/s once, at 81% hub CPU (earlier run).
- Wi-Fi, from the monitors (about 450 s per laptop): impaired seconds 46 (edge-1), 38 (edge-2), 35 (edge-3) and 157 (edge-4, 35% of the time); the monitor's
  thresholds (probe above 100 ms) flag 8 to 10% of seconds even on the good laptops, so "impaired" is not "a problem for the experiment" and severity
  levels are needed. One laptop is chronically worse: edge-4, impaired in 11 to 23 s of every run, signal median -58 dBm (min -62), link 390 Mbit/s median,
  mostly TCP retransmits. Three or more of the four laptops were impaired in the same second for 31 s of 432 (7%), 11 s of them in the first run,
  at identical clock times: a disturbance of the shared medium. It was not driven by load (the first, lowest-load run had the most).
- The 7 agent transfers over 0.5 s in the window were all inside a monitor episode of the sender (7 of 7): the stalls coincide with network impairment seen
  by an independent probe, not with our software. A small sample.
- Consequences: R_max for the inclusion rule can be set at 350 tasks/s (conservative, nine runs); the placement of edge-4 should be improved or its
  weakness logged and accepted; runs are repeated and interleaved with the monitors on, and their per-run impaired seconds reported with the results.

### After moving the router and edge-4 (2026-11-11, about 21:40): worse, and not explained by signal or neighbours
- The same three calibration runs (5, 20, 50 requests/s) after the move: impaired seconds per laptop rose from 2 to 27% of a run (before: nine runs) to
  28 to 67% (after: three runs). Over the monitored periods (about 560 s before, 330 s after): edge-1 12 to 32%, edge-2 9 to 23%, edge-3 9 to 20%,
  edge-4 35 to 49%; probes above 500 ms or lost went from 1 to 2% to about 9% on all four laptops; TCP retransmits per second rose three to four times.
  Calibration after the move: the 5 requests/s run had a p95 queue-free overhead of 7 s (p99 ratio 4.8) and the 50 requests/s run a p99 ratio of 2.3, with
  no late hub events (the hub was fine).
- Signal strength is not the driver: edge-4's signal and link improved (-58 to -54 dBm, 390 to 585 Mbit/s) and its impairment did not; edge-1's signal
  improved (-34 to -28 dBm) and its impairment rose from 12 to 32%.
- Not a channel change (all laptops on 5745 MHz before and after) and not neighbouring networks: a fresh scan from the hub heard 3 networks, only ours on
  5 GHz and none on the channels that overlap our 80 MHz block. What remains is the access point (an ISP router) and non-Wi-Fi interference; the
  simultaneous multi-laptop stalls at identical clock times point at the single common element, the access point.
- Not conclusive: one before/after comparison, confounded with the time of day. A fair test alternates the placements (A, B, A, B) with the same load.

### Isolated router, and the cause of the periodic stalls (2026-11-11, 22:13 to 22:21)
- All four laptops joined the isolated router on 2.4 GHz (channel 10; link 58 to 144 Mbit/s). End-to-end calibration was steady (live p99 makespan 1.02 to 1.08
  times the simulator's in all nine runs, hub CPU at most 38%, no late events) but the queue-free p95 overhead was 374 to 490 ms in every run, and the
  monitors showed 39 to 50% of seconds impaired, mostly all four laptops at once.
- Timing of the stalls (484 s of monitor data): strictly periodic. 26 of 37 gaps between episodes are exactly 15 s; the autocorrelation peaks at 15, 30, 45,
  60 and 75 s (0.69 to 0.79); episodes start at fixed offsets within the minute (5, 20, 35, 50 s); each lasts about 5 s (median 5, max 10); 71 to 85% of
  the stall seconds are shared between any two laptops; the share is the same before the first run (38%) and during the runs (38%): not load-dependent.
- Mechanism found with `iw event -t` for 50 s: edge-2, edge-3 and edge-4 each ran a full scan of all twelve 2.4 GHz channels every 15 s (edge-2 and edge-3 in
  the same second, edge-4 one second later), each taking 1.2 to 6.3 s with the radio off the channel; edge-1 ran none. `gnome-control-center` (GNOME Settings,
  whose Wi-Fi panel makes NetworkManager rescan every 15 s while it is open) was running on exactly those three laptops (open 16 to 20 minutes) and not on edge-1.
  So the stalls seen here are caused by the laptops' own scans, not by the router. Not yet confirmed by closing the windows and measuring again.
- Open: whether the earlier stalls on the household network had the same cause (the pattern there was irregular); preflight should refuse a measured run while a
  Wi-Fi settings window or any other scan source is active; text boot mode (SETUP.md Part 5) removes GNOME and with it this source.

### Confirmed: after closing GNOME Settings on edge-2, 3 and 4 (isolated router, 2.4 GHz; 22:29 to 22:37, nine runs)
- Scan events over 50 s on every laptop: 0 (before: a 12-channel scan every 15 s on three laptops).
- Calibration: all requests completed; live p99 makespan 1.02 to 1.04 times the simulator's in all nine runs; queue-free p95 overhead 58 to 119 ms (before the fix
  374 to 490 ms); extra time per task 5.4 to 9.9 ms (before 11 to 19 ms); no late hub events; hub CPU at most 39%; 0 agent transfers over 0.5 s (before 11).
- Monitors (491 to 495 s each): impaired seconds edge-1 15%, edge-2 8%, edge-3 12%, edge-4 34% (before 39 to 50% on all). Seconds with 3 or more laptops impaired:
  23 of 496 (5%; before about 38%); 8 shared episodes of 1 to 4 s with gaps of 43 to 203 s, no 15 s cycle.
- Remaining: edge-4 is still the weakest (median signal -52 dBm, min -68; link median 72 Mbit/s, min 29); stalls on paths to or from edge-4 are 7 to 12% of seconds
  against 2 to 4% elsewhere. The monitor's 100 ms threshold also flags ordinary jitter.
- Conclusion: the stalls were caused by the laptops' own scans, not by the router or the 2.4 GHz band. The earlier household-network stalls may have had the same cause
  (not established; the pattern there was irregular). Guard needed: preflight must refuse a measured run while gnome-control-center or any other scan source is active.

### edge-4 moved into the room (2026-11-11, about 22:44; isolated router, 2.4 GHz, Settings closed) - provisional, 160 s and three runs
- edge-4's link: median signal -52 dBm (min -68) and link 72 Mbit/s (min 29) before, -36 dBm (min -37) and 144 Mbit/s (min 130) after. The laptop had rebooted for the move
  (its agent and monitor had to be restarted; its settings survived).
- Impaired seconds (monitor thresholds unchanged): edge-4 7 of 160 s (4%, before 34%); edge-1 1, edge-2 2, edge-3 1 of about 157 s (at most 1%, before 8 to 15%). No second with
  3 or more laptops impaired except one. 0 agent transfers over 0.5 s. Calibration (5, 20, 50 requests/s, one run each): queue-free p95 overhead 52 to 75 ms, extra time per
  task 4.9 to 7.3 ms, live p99 makespan 1.02 times the simulator's, no late hub events, hub CPU at most 39%.
- Plausible reading, not tested: a weak client at 29 to 72 Mbit/s holds the channel longer per frame (airtime), so fixing it improved every laptop. Needs a longer series
  (the nine-run design) before it goes into any result.

### The guard before a measured run (built 2026-11-11)
`fleet.py guard [--seconds N]` checks every laptop in parallel and exits 1 if any is not ready; `calibrate.py` runs it first and refuses to start unless it
passes (`--no-guard` for a trial). It uses the preflight's `--measured` checks and four new Wi-Fi checks in `preflight.py` (`wifi_guard`): (1) no program that makes
NetworkManager scan is running (GNOME Settings `gnome-control-center`, `nm-connection-editor`, `nm-applet`, `iwgtk`, `wpa_gui`), (2) no Wi-Fi scan seen by the driver during
a watch of N seconds (default 20), (3) link quality now: signal at least -60 dBm and a transmit rate of at least 100 Mbit/s (the weak edge-4 link of 72 Mbit/s would have
failed), (4) at most 10% of the last 60 s impaired according to the running monitor (a warning when no monitor runs). The guard also requires the settings and software
checks (power save, clock, governor, swap, packages), a reachable agent and a fresh monitor. The thresholds are first values to be checked against more data. It changes
nothing: it only reports. Tested with 59 tests; tried on the hub (ready, then NOT ready with a stand-in process named like GNOME Settings, then ready again); not yet run on the
other three laptops (they need the new code: commit and `fleet.py sync`).


### Guard run on the real laptops: edge-4's snapd, and what the guard sees (2026-11-11, about 23:00 to 23:15)
- First guard runs failed all four laptops (52 to 62% of the last 60 s impaired): the sync's own traffic. After a quiet minute three laptops passed and edge-4 failed at 13% (limit 10%).
- Cause on edge-4, not Wi-Fi: its signal was -35 dBm, and the impaired seconds were TCP retransmits (3 to 5 per second, about 60 a minute for the whole 10 minutes; 61 impaired seconds
  of 600 against 0 to 5 on the others). 13 to 14 outbound connections to the Snap Store were stuck in SYN-SENT: the isolated router has no internet, and snapd's first-boot task
  "Initialize device" had never finished on edge-4 (it finished on edge-3 earlier, on the house network), so snapd retried for hours. `snap refresh --hold` does not stop this.
  The monitor counts SYN retransmits as TCP retransmits, so the guard saw "impairment" that had nothing to do with the radio.
- Runtime fix on edge-4: `systemctl stop snapd.socket snapd.service` (not disabled, not masked): retransmits 0 in 30 s afterwards. A reboot starts snapd again and the retries
  return. Lasting options: register edge-4 once on a network with internet, or stop snapd on every laptop at the start of a measurement session (preferred: the experiments then do not
  depend on snapd's state; to be added to the fleet environment step).
- Guard changes (commit 4ef9080): new check "no half-open outbound connections" (SYN-SENT sockets, with the owning program; fails above 2, because the hub also runs Claude and
  makes stray connections); the link-quality check uses the median signal and transmit rate of the last minute from the monitor log (one sample of an idle link's rate bounces:
  edge-2 reported 58 to 65 Mbit/s in 9% of seconds while its median is 130, which failed it at random), with the single sample as fallback when no monitor runs.
- Also seen in those 10 minutes: one 30 s stretch with about 32 slow-probe seconds on all four laptops at once, a disturbance of the shared medium; not explained.

### The nine-run series through the guard (2026-11-11, 23:17 to 23:30; isolated router, 2.4 GHz, edge-4 in the room, snapd stopped on edge-4)
Design: Trip Booking, 20 nodes, 5 / 20 / 50 requests per second, three passes (pass = 5, 20, 50), static placement, common random numbers, monitors running, `calibrate.py` gated by
`fleet.py guard` before each pass. Logs: `~/testbed-results/netmon-20261111-233041` and `calibration-20261111-232019/232512/233013.json` (local, not in the repository).
- Testbed (all nine runs): all requests completed (168/168, 638/638, 1644/1644 at 5, 20, 50 requests/s); no late hub events; no agent transfer over 0.5 s; live p99 makespan
  1.01 to 1.03 times the simulator's; p50 makespan 1.26 to 1.44 times (the added 5 to 8 ms is large next to Trip Booking's millisecond tasks). Queue-free p95 overhead 45 to 60 ms
  (5/s), 54 to 57 ms (20/s), 78 to 88 ms (50/s); extra time per task 4.5 to 5.3, 5.2 to 5.6, 7.3 to 8.2 ms; hub CPU 3 to 5%, 10 to 18%, 24 to 45%. Every pass sustained 350 tasks/s:
  R_max = 350 tasks/s stands. Earlier nine runs (22:29 to 22:37, edge-4 far away): p95 overhead 58 to 119 ms, extra time per task 5.4 to 9.9 ms.
- Wi-Fi, impaired seconds inside the nine runs' own 50 s windows (440 s): edge-1 42 (10%), edge-2 33 (8%), edge-3 33 (8%), edge-4 40 (9%); three or more laptops impaired in the same
  second: 33 s (8%). (The report command's per-run table runs to the next configure event and includes the idle time between passes: runs 6, 9, 12 of its table; use the 50 s windows.)
  Over the whole series (764 s): impaired 6 to 8% per laptop; signal median -34 to -40 dBm (min -44); link median 130 to 144 Mbit/s (min 58 on edge-2 and edge-4). Nearly all impairment is
  "probe slow" (above 100 ms); edge-1 also had 8 TCP-retransmit seconds, edge-4 5 retry seconds. Edge-4, impaired 34% of the time before it was moved, is now level with the others.
- Impairment rises with load: 4 to 9 of 50 s at 50 requests/s, 0 to 4 at 5 requests/s (20/s: 2 to 6). Shared by 3+ laptops in nearly all those seconds. Plausible reading, not tested:
  the testbed's own traffic slows the probes on the shared 2.4 GHz channel, so part of the "impairment" is self-induced.
- Guard: 5 checks, 2 refusals, both directly after a 50 requests/s run (15 to 18% of the last 60 s impaired on all four laptops before pass 3; edge-1 12% and edge-4 13% before pass 2),
  because its 60 s window contained that run's own traffic. Waiting 90 s cleared both. Consequence for the pre-registration: a cooldown of at least 90 s after every run before the guard
  looks, or a guard that leaves our own runs out of its window; otherwise it measures our load rather than the environment.
- Cooldown added to the guard (2026-11-11): every `LiveSim` run stamps its end time on the hub (`testbed/runmark.py`, `~/testbed-logs/last-run-end`, local); `fleet.py guard`
  (default 90 s, `--cooldown S`, 0 = none) and `calibrate.py` wait until 90 s have passed since that stamp before they look at the monitor, longer than its 60 s window, so a run's
  own traffic is not counted as impairment. No stamp, or an older one, means no wait; a stamp from the future never waits more than the cooldown. Tried on the hub: guard right after a
  stamped run end printed "cooling down 75 s", then all four laptops passed. A test now starts `fleet.py` and `calibrate.py` as scripts, because the first version imported a module
  in a way that only works under pytest.
- Not established: whether 5 GHz changes any of this; the cause of the 30 s shared disturbance; whether the load-dependent impairment is self-induced. Trip Booking's timing-resolution limits (DEV-T5) apply.

### The nine-run series again, with the cooldown (2026-11-11, 23:45 to 23:57; same setup as the first series, laptops synced to 0bd70ac, 90 s settle after the sync)
Logs: `~/testbed-results/netmon-20261111-235805`, `calibration-20261111-234841/235311/235742.json` (local, not in the repository).
- Guard: 3 checks, 0 refusals; before passes 2 and 3 it waited 82 s and 81 s (cooldown since the last run's end), then all four laptops passed all 10 checks. The first series had 2 refusals in 5 checks,
  both straight after a 50 requests/s run. So the refusals came from our own traffic, and the cooldown removes them.
- Testbed (nine runs): all requests completed (168/168, 638/638, 1644/1644 at 5, 20, 50 requests/s); no late hub events; no agent transfer over 0.5 s; live p99 makespan 1.01 to 1.04 times
  the simulator's; p50 1.26 to 1.44 times. Queue-free p95 overhead 46 to 48 ms (5/s), 55 to 58 ms (20/s), 81 to 88 ms (50/s); extra time per task 4.8, 5.4 to 5.7, 7.6 to 8.1 ms;
  hub CPU 4%, 15 to 16%, 33 to 40%. The first series gave 78 to 88 ms and 7.3 to 8.2 ms at 50 requests/s: the numbers repeat across series. R_max = 350 tasks/s stands.
- Wi-Fi, impaired seconds inside the nine runs' 50 s windows (450 s): edge-1 39 (9%), edge-2 34 (8%), edge-3 34 (8%), edge-4 36 (8%); three or more laptops impaired in the same second 32 s (7%).
  Whole series (725 s): impaired 8 to 9% per laptop; signal median -35 to -42 dBm (min -47); link median 130 to 144 Mbit/s (min 58 on edge-2 and edge-4); almost all "probe slow"
  (above 100 ms), 1 to 2 TCP-retransmit seconds on edge-1 and edge-2, 2 retry seconds on edge-4. Edge-4 is level with the others (snapd still stopped on it).
- Load dependence, second observation: impaired laptop-seconds by rate 3% (5/s), 9% (20/s), 12% (50/s); first series 5%, 7%, 13%. The 5 requests/s level is close to the idle level
  (about 2 to 3% outside the one 30 s shared disturbance in the idle window before). Still not tested whether it is the testbed's own traffic slowing the probes on the shared 2.4 GHz
  channel; a run with the monitors' probes on and a laptop pair sending a controlled load would separate the two.
- Not established: 5 GHz; the cause of the 30 s shared disturbance in the idle window; whether the load-dependent impairment is self-induced.

## Phase 4: the paper's controller (FROZEN-4) on the testbed (2026-11-12)
Code: `testbed/frozen_live.py` (the controller built once for `Sim` and `LiveSim`: B* annealer wrapped in `O3SimAdjuster`, `cand_mode="nosim"`, blind forecast, `transfer_only`
dispatcher, criticality queue order; configurations from `output/data-analysis/frozen2.py`; arms `frozen4`, `frozen4_mv3`, `frozen4_p8`, `frozen3`), `testbed/controller_check.py` (the check on the
laptops), `tests/test_frozen_live.py`. Results: `~/testbed-results/controller-frozen4-*.json` (local).
- Equivalence with the paper's pipeline: on the stored scenario F1, load 0.5, seed 1 (900 s) the builder gives the stored event hash of the `fill1` arm (= FROZEN-4),
  `7974387182b98e5c2c21bb068e4cbbb3`, and the same P99 (88.9296 s): same controller, event for event. It is a test (`-m slow`, skipped when the local stored results are absent).
  The builder is deterministic (two runs, same hash) and leaves the initial layout untouched.
- Loopback, three agent processes at speed 10 (MapReduce, 6 nodes, load 0.1): all requests completed, cold starts 32 in both, live P50 1.12 s against 0.99 s, no late events, hub CPU 41%,
  re-layout moves reached the agents (37 relocation transfers). The same scenario at load 0.4 (1,850 tasks per wall second at speed 10) overloaded the hub (CPU 115%): a test-load error, not a controller one.
- On the four laptops (guard first; MapReduce, 10 logical nodes, 240 s of load, warm-up 60 s, random initial layout, CAP-U, common random numbers; the simulator run is the reference):

  | load (seed) | req/s = tasks/s | completed live / sim | P50 live/sim | P99 live/sim | cold starts live / sim | moved live / sim | late events | queued events max | hub CPU | adjust p95 live (sim) |
  |---|---|---|---|---|---|---|---|---|---|---|
  | 0.3 (1) | 19.8 = 198 | 3543/3543 / 3543 | 1.04 | 1.03 | 54 / 54 | 3572 / 3426 | 0 | 91 | 18% | 2.2 (1.5) ms |
  | 0.5 (1) | 33.0 = 330 | 5929/5929 / 5929 | 1.04 | 1.12 | 56 / 55 | 14568 / 14045 | 0 | 409 | 25% | 2.9 (2.2) ms |
  | 0.5 (2) | 33.6 = 336 | 6075/6075 / 6075 | 1.07 | 1.03 | 54 / 54 | 14867 / 14135 | 0 | 173 | 23% | 1.9 (1.0) ms |

  Plan time (p95) 1.1 to 1.3 ms. The controller's own compute is milliseconds, small against the 4 s move period, so it does not stall the hub: no late events, hub CPU 18 to 25% at up to 336 tasks/s
  (the static-placement calibration gave 24 to 45% at 350 tasks/s). R_max = 350 tasks/s is not lowered by the controller on this application and size. Live runs move 3 to 5% more requests than the simulator.
- The P99 ratio of 1.12 (load 0.5, seed 1) is not a testbed fault by itself: the controller is chaotic. The simulator with the move clock shifted by 1 to 3 ms (placebo runs) gives P99 between 5.29 and
  5.84 s on that seed (spread 1.105x, six runs) and 6.27 to 6.44 s on seed 2 (1.027x). The live ratios (1.12, 1.03) are at the edge of and inside those spreads. Consequence: judge the live
  system against the simulator on several seeds and against the simulator's own run-to-run spread, never against one reference run. The mean ratio of P99 over seeds is the quantity to report.
- Two defects found on the way, both mine, both fixed: (1) an agent keeps ONE control connection and a new one closes the old one, so the guard's reachability check closed the link the check had opened
  before it (`ping: connection_lost`); the link is now opened after the guard, as `calibrate.py` does; (2) the first attempt at load 0.5 was refused by the guard (all four laptops 7 of 60 s impaired,
  12%, a shared episode, after the cooldown had passed). The idle baseline is already 7 to 8% impaired, so a limit of 10% over 60 s refuses by chance fairly often. `controller_check.py` now retries a refused
  guard up to twice, 60 s apart, and stores the number of refusals in each result row (`guard_refusals_before`). The window and limit are first values and should be set from a longer quiet series.
- Planning input for the pre-registration (load rates at 20 nodes, SeBS-Flow measured profile): tasks per second needed for load 0.5 / 0.85: Video 15 / 26, Trip Booking 6,137 / 10,433, MapReduce 708 / 1,203,
  ExCamera 12 / 21, ML 570 / 970, 1000Genome 2 / 4. Against R_max = 350, Trip Booking, MapReduce and ML cannot be driven at those loads on 20 nodes: they need a smaller cluster or a rate cap
  (`rho_effective` records what was offered); Video, ExCamera and 1000Genome are light on the hub but their requests are long, so run length decides how many requests a run contains.
- Limits of this step: one application (MapReduce), CAP-U, 10 nodes, 240 s runs (re-layouts at 60, 120, 180 s), random initial layout, three live runs, the monitors' impaired seconds for these runs not yet analysed.
  Not yet done: the B* (annealer) path and the baselines (SR, SG, Heu, RL) through `LiveSim`, the experiment driver (phase 5), and the validation against the simulator over many seeds (phase 6).

### Housekeeping and the pre-registration draft (2026-11-12)
- Laptops synced to 9eea770. New `fleet.py quiet on|off|status` stops (starts again) snapd on every laptop for a measurement session (its retries without internet fail the guard, see edge-4); applied to all four,
  0 half-open connections. It stops the service and socket, it does not disable them; `quiet off` restores.
- Text boot mode (SETUP Part 5) is NOT automated, on purpose: step 5.1 types the Wi-Fi password into NetworkManager (not something the automation does), and a laptop that fails to rejoin the Wi-Fi after the reboot cannot
  be reached again from the hub (edge-3 has no Ethernet fallback). Its purpose (no program that triggers Wi-Fi scans) is already enforced by the guard. It stays an optional manual step.
- The pre-registration is drafted in `knowledge/synthesis/testbed-preregistration.md` (status draft). It fixes the systems, the per-application load rule with the 300 tasks/s cap, seeds 7-10, randomised blocks, validity rules, the
  analysis and the stopping rule, and lists seven decisions for the freeze. Build items before the first confirmatory run: live B*, SR, SG, Heu, RL; the plan's initial layout for SeBS scenarios; the experiment driver; simulator twins.
