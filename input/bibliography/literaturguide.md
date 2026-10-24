# Literaturguide: G0 novelty scan (D1 / D2 / D3), search only

Date: 2026-10-13. Plan: input/ideas/faas-edge-adaptation-plan.md, Task 2 (G0). Nothing downloaded. Databases: OpenAlex (title/abstract boolean, 2024+), arXiv API, Crossref, Semantic Scholar (abstracts only), WebSearch. Every DOI below resolved in Crossref or OpenAlex (arXiv DOIs via OpenAlex only).

Counts: A=5, B=16, C=5 (total 26). Access/status labels: abstract-only for all; no full text read in this pass. Abstracts of Sun 2026 and Lei 2026 (JPDC) could not be retrieved from Crossref/OpenAlex/Semantic Scholar/ScienceDirect (403), so their grade is provisional and carried by the plan, not by evidence.

## Weighted table

| Grade | Autor Jahr / Kurztitel | Richtung | OA/Zugang | DOI/Link | Befund (Abstract-Ebene) |
|---|---|---|---|---|---|
| A | Sun 2026 Hybrid scheduling for serverless function workflows at the edge | D1?/D3? | paywalled (VPN); abstract not retrievable | [10.1016/j.future.2026.108822](https://doi.org/10.1016/j.future.2026.108822) | G0-named in plan; content unverified until ingested (Task 2) |
| A | Lei 2026 Adaptive container scheduling for serverless workflows, cloud-edge | D1?/D3? | paywalled (VPN); abstract not retrievable | [10.1016/j.jpdc.2026.105308](https://doi.org/10.1016/j.jpdc.2026.105308) | G0-named in plan; content unverified until ingested |
| A | Liao 2025 Adaptive GNN-based scheduling of serverless workflows in dynamic edge (event-driven two-stage) | D1/D3 | closed; abstract via OpenAlex | [10.1109/iccc68654.2025.11437925](https://doi.org/10.1109/iccc68654.2025.11437925) | workflow + edge + event-driven re-scheduling under node churn; jointly encodes workflow, cold start |
| A | Jia 2025 FaaSPR placement and routing for serverless workflows | D3 | closed | [10.1109/ton.2025.3552407](https://doi.org/10.1109/ton.2025.3552407) | placement + routing coupled for workflows, avoids frequent migrations (not edge-specific) |
| A | Farahani 2026 ClusterLess deadline-aware workflow orchestration, federated edge | D2/D3 | OA (arXiv) | [10.48550/arxiv.2605.04310](https://doi.org/10.48550/arxiv.2605.04310) | E2E-deadline workflow placement + execution-mode selection on edge; check full text for admission/shedding |
| B | Tang 2025 Metis non-clairvoyant workflow-aware OS scheduler | D2 | hybrid OA | [10.1145/3772052.3772221](https://doi.org/10.1145/3772052.3772221) | critical-path estimation + workflow-level scheduling (OS level, no admission, mean WCT) |
| B | Nguyen 2025 Taming cold starts with MPC | D1 | OA (arXiv) | [10.48550/arxiv.2508.07640](https://doi.org/10.48550/arxiv.2508.07640) | forecast-based joint prewarm + dispatch; single functions, not workflows/edge, no worst-case guarantee |
| B | Lei 2026 Multi-agent time-critical FaaS scheduling (runtime architecture switching) | D1 | closed; abstract via S2 | [10.1109/ipdpsw71298.2026.00085](https://doi.org/10.1109/ipdpsw71298.2026.00085) | signal-triggered switching (p95/p50), negligible switch cost; functions not workflows |
| B | Xiao 2024 Making serverless not so cold in edge clouds (online) | D1/D3 | green OA | [10.1109/tmc.2024.3355118](https://doi.org/10.1109/tmc.2024.3355118) | online algorithm, caching + routing for function chains at edge; adjacent-slot coupling |
| B | Li 2024 Online container scheduling w/ fast startup, low memory (competitive ratio) | D1/D3 | closed | [10.1109/tc.2024.3441836](https://doi.org/10.1109/tc.2024.3441836) | competitive-ratio online algorithm; invocation distribution + caching; no predictions |
| B | Cao 2025 Dynamic container placement at serverless edge: online convex optimization | D1 | closed | [10.1109/wocc63563.2025.11082211](https://doi.org/10.1109/wocc63563.2025.11082211) | regret-guarantee placement, no workflows/predictions |
| B | Huang 2025 Online learning for function placement in serverless | D1 | closed | [10.1109/netsoft64993.2025.11080544](https://doi.org/10.1109/netsoft64993.2025.11080544) | bandit regret bounds for placement; not workflow/edge dispatch |
| B | Li 2024 Online layer-aware joint request scheduling, container placement, provisioning | D3 | closed | [10.1109/tsc.2024.3504237](https://doi.org/10.1109/tsc.2024.3504237) | joint scheduling+placement online at edge, not DAGs |
| B | Choupani 2025 Joint autoscaling and request scheduling for serverless edge | D3 | closed | [10.1007/s10586-024-04870-0](https://doi.org/10.1007/s10586-024-04870-0) | joint scaling+scheduling, not workflows |
| B | Peng 2025 Joint container orchestrating and request routing, serverless edge | D3 | closed | [10.1016/j.jnca.2025.104284](https://doi.org/10.1016/j.jnca.2025.104284) | joint orchestration + routing, not DAGs |
| B | Chen 2025 Dike DRL function scheduling SLO-targeted serverless edge | D2 | closed | [10.1109/iscc65549.2025.11326247](https://doi.org/10.1109/iscc65549.2025.11326247) | SLO-violation in reward; no admission control/workflows |
| B | Subedi 2025 Energy-aware latency optimization scheduling serverless at edge | D1 | hybrid OA | [10.1145/3773274.3774276](https://doi.org/10.1145/3773274.3774276) | scheduler + descheduler consolidation (periodic), IoT workflows |
| B | Marcelino 2025 Databelt state path serverless workflows 3D continuum | D1 | hybrid OA | [10.1016/j.sysarc.2025.103577](https://doi.org/10.1016/j.sysarc.2025.103577) | proactive SLO-aware state propagation for workflows (state, not placement) |
| B | Jayanthi 2026 Quantum-inspired bi-level scheduling serverless deployment edge | D3 | gold OA (PDF in library) | [10.1007/s10791-026-10504-3](https://doi.org/10.1007/s10791-026-10504-3) | cites DFPS; placement+scheduling bi-level; G0-named; verify by reading |
| B | Farhadi 2026 Chain-aware DRL real-time serverless smart-grid workflows | D2/D3 | closed; abstract via S2 | [10.1109/icccn69946.2026.11662819](https://doi.org/10.1109/icccn69946.2026.11662819) | chain/tail-latency aware dispatch, URLLC vs mMTC classes; no admission |
| B | Nan 2025 Data-locality-aware scheduling containerized workflows edge-cloud | D3 | closed | [10.1109/synasc69064.2025.00026](https://doi.org/10.1109/synasc69064.2025.00026) | placement with data locality, static weights |
| C | Zolfaghari 2025 DFPS (baseline) | D3 baseline | closed | [10.1109/tsc.2025.3592226](https://doi.org/10.1109/tsc.2025.3592226) | the baseline itself |
| C | Pusztai 2024 HyperDrive 3D continuum scheduling | - | OA (arXiv) | [10.48550/arxiv.2410.16026](https://doi.org/10.48550/arxiv.2410.16026) | background SLO-aware scheduling |
| C | Giagkos 2024 Darly QoS-aware scheduling video analytics edge | - | gold OA | [10.3390/info15080480](https://doi.org/10.3390/info15080480) | background |
| C | Xu 2026 Structure-aware serverless orchestration graph RL (fusion+placement) | D3 | closed | [10.1109/tsc.2026.3724938](https://doi.org/10.1109/tsc.2026.3724938) | background; workflow placement via GRL |
| C | Xu 2026 Adaptive two-timescale joint service placement and request scheduling (edge AIGC) | D1/D3 | closed | [10.1109/infocom59046.2026.11571701](https://doi.org/10.1109/infocom59046.2026.11571701) | two-timescale placement/scheduling, AIGC not serverless workflows |

## Search queries executed

- OpenAlex title_and_abstract: serverless AND workflow AND (admission OR load shedding OR overload) -> no workflow admission/shedding paper (only SafeLoad, data-warehouse queries, not serverless)
- OpenAlex: serverless AND (workflow OR DAG) AND edge AND (placement AND (scheduling OR dispatch))
- OpenAlex: serverless AND (learning-augmented OR algorithms with predictions OR competitive ratio OR prediction-augmented) -> only classic online/competitive-ratio work; no predictions-with-robustness paper for serverless found
- OpenAlex: serverless AND (event-triggered OR drift-triggered OR adaptive reconfiguration OR re-placement) -> noise; Liao 2025, Lei IPDPSW 2026 relevant
- OpenAlex: serverless AND workflow AND (goodput OR deadline-aware OR SLO-aware) AND (edge OR overload)
- OpenAlex: serverless AND (migration cost OR switching cost OR reconfiguration cost) AND (placement OR replacement) -> 0 hits
- OpenAlex: METIS AND serverless -> Tang 2025 (SoCC)
- arXiv API (10 boolean variants incl. load shedding, goodput, switching cost, learning-augmented): 0 relevant 2024+ hits beyond those listed; Multi-Event Triggers for Serverless (2505.21199) is a platform-trigger paper, not reconfiguration, C-level, omitted
- Crossref bibliographic: workflow overload SLO admission; periodic reconfiguration placement; autoscaling DAG burst; dispatch+placement joint; predictions robustness
- OpenAlex cited-by of 10.1109/TSC.2025.3592226 (W4412623589): 8 citing works (listed below)

## Papers citing DFPS (OpenAlex, 8)

Jayanthi 2026 (Discover Computing, 10.1007/s10791-026-10504-3); Lei et al. 2026 IPDPSW (10.1109/ipdpsw71298.2026.00085); Farhadi 2026 ICCCN (10.1109/icccn69946.2026.11662819); Cao 2026 TSC fault-tolerant function embedding (10.1109/tsc.2026.3670012); Xu 2026 WPPSO (10.3390/electronics15122519); Liang 2026 SECON (10.1109/secon68281.2026.11578991); Feng 2026 PIMRC (10.1109/pimrc69400.2026.11712039); Supraja 2025 service placement review (10.1007/s10586-025-05759-2). None of the citing works found shows D1-D3 content beyond rows above; Cao, Xu, Liang, Feng, Supraja are C (not graded into table).

## G0 pre-emption risk

### D1 (event/cost-triggered reconfiguration, switching cost, learning-augmented forecasts) - risk: PARTIAL, not pre-empted on abstract evidence
- A (provisional): Sun 2026 and Lei 2026 (JPDC): named G0-critical; abstracts unavailable, must be read for a trigger policy or switching cost.
- A: Liao 2025 ICCC: event-driven re-scheduling of workflows at the dynamic edge; no switching-cost model or forecast guarantee visible in the abstract.
- Closest guarantee-side work: Xiao 2024, Li 2024 (competitive ratio, no predictions), Cao 2025 and Huang 2025 (regret bounds, no workflows); Nguyen 2025 (forecast MPC, no guarantees, no workflows). No learning-augmented / algorithms-with-predictions serverless paper found. Lei IPDPSW 2026 switches architecture on a latency signal (event-triggered, cost negligible), but for functions, not DAG re-placement.

### D2 (admission control / load shedding with SLO-goodput + critical-path dispatch) - risk: LOW (looks clear)
- No A-grade threat. No serverless workflow admission-control or load-shedding paper found in any database. Closest: Metis 2025 (critical-path-aware workflow scheduling at OS level, mean completion time, no admission; B), Dike 2025 (SLO violations in reward, no admission), ClusterLess 2026 (deadline-aware; full text needed to confirm no admission; graded A for D2/D3 precaution).

### D3 (placement coupled with dispatch, placement scored by dispatch response) - risk: HIGHEST
- A: FaaSPR 2025 (Jia, ToN): joint placement + routing for serverless workflows, latency-oriented. A: ClusterLess 2026: workflow placement + execution mode under E2E deadlines on edge. A: Liao 2025: two-stage scheduling, jointly encodes workflow, cold start. A (provisional): Sun 2026, Lei 2026.
- Joint placement+scheduling exists widely for non-DAG settings (Li 2024 TSC, Choupani 2025, Peng 2025). The differentiator to test is placement scored by the dispatch response on upcoming requests (O3 simulation in the loop); not seen in any abstract, but DFPS itself already couples placement and request scheduling, so D3 must be framed against DFPS.

## Notes for reviewer
- Search is abstract-level; novelty is not inferred. Pre-emption verdict requires full-text ingestion of Sun, Lei, Liao, FaaSPR, ClusterLess, Jayanthi.
- Metis metadata: Tang, Yang, Wu; SoCC 2025; DOI 10.1145/3772052.3772221 (OpenAlex; Crossref ok).
- Not found: any 2024-2026 paper with load shedding/admission for serverless workflows; any serverless paper with prediction-augmented guarantees.
- Embedded-title anomalies: none. Unverified DOIs: 0.

## BibTeX candidates

```bibtex
@article{sun2026hybrid,
  author = {Sun, Mengyu and Lu, Gang and Huang, Zhilan and Quan, Shuo and Zhang, Yaqiang and Tan, Yukai},
  title = {Hybrid scheduling for serverless function workflows in edge computing system},
  journal = {Future Generation Computer Systems},
  year = {2026},
  pages = {108822},
  doi = {10.1016/j.future.2026.108822},
  note = {verified via Crossref; grade A}
}

@article{lei2026adaptive,
  author = {Lei, Yamin and Hou, Yucheng and Zhang, Yixin and Wang, Shuang},
  title = {Adaptive container scheduling for serverless workflows in cloud-edge collaborative computing},
  journal = {Journal of Parallel and Distributed Computing},
  year = {2026},
  volume = {216},
  pages = {105308},
  doi = {10.1016/j.jpdc.2026.105308},
  note = {verified via Crossref; grade A}
}

@inproceedings{liao2025adaptive,
  author = {Liao, Lecheng and Li, Zhengze and Liu, Shuyi and Lu, Hancheng},
  title = {Adaptive GNN-Based Scheduling of Serverless Workflows in Dynamic Edge Environments},
  booktitle = {2025 11th International Conference on Computer and Communications (ICCC)},
  year = {2025},
  pages = {117-122},
  doi = {10.1109/iccc68654.2025.11437925},
  note = {verified via Crossref; grade A}
}

@article{jia2025faaspr,
  author = {Jia, Yunshan and Jin, Chao and Li, Qing and Liu, Xuanzhe and Jin, Xin},
  title = {FaaSPR: Latency-Oriented Placement and Routing Optimization for Serverless Workflow Processing},
  journal = {IEEE Transactions on Networking},
  year = {2025},
  volume = {33},
  pages = {2063-2078},
  doi = {10.1109/ton.2025.3552407},
  note = {verified via Crossref; grade A}
}

@misc{farahani2026clusterless,
  author = {Reza Farahani and Mario Colosi and Ilir Murturi and Stefan Nastic and Massimo Villari and Schahram Dustdar and Radu Prodan},
  title = {ClusterLess: Deadline-Aware Serverless Workflow Orchestration on Federated Edge Clusters},
  year = {2026},
  doi = {10.48550/arxiv.2605.04310},
  note = {arXiv preprint; verified via OpenAlex; grade A}
}

@inproceedings{tang2025m,
  author = {Tang, Wenda and Yang, Yanan and Wu, Jie},
  title = {M
                    <scp>etis</scp>
                    : A Non-Clairvoyant, Workflow-Aware OS Scheduler for Serverless Applications},
  booktitle = {Proceedings of the 2025 ACM Symposium on Cloud Computing},
  year = {2025},
  pages = {149-162},
  doi = {10.1145/3772052.3772221},
  note = {verified via Crossref; grade B}
}

@misc{nguyen2025taming,
  author = {Chanh Le Tan Nguyen and Monowar H. Bhuyan and Erik Elmroth},
  title = {Taming Cold Starts: Proactive Serverless Scheduling with Model Predictive Control},
  year = {2025},
  doi = {10.48550/arxiv.2508.07640},
  note = {arXiv preprint; verified via OpenAlex; grade B}
}

@inproceedings{lei2026multiagent,
  author = {Lei, Yitao and Zhou, Mengbing and Daniëlse, Paul and Zhao, Zhiming},
  title = {Multi-Agent Based Time Critical FaaS Scheduling in Edge-Cloud Continuum},
  booktitle = {2026 IEEE International Parallel and Distributed Processing Symposium Workshops (IPDPSW)},
  year = {2026},
  pages = {498-505},
  doi = {10.1109/ipdpsw71298.2026.00085},
  note = {verified via Crossref; grade B}
}

@article{xiao2024making,
  author = {Xiao, Ke and Yang, Song and Li, Fan and Zhu, Liehuang and Chen, Xu and Fu, Xiaoming},
  title = {Making Serverless Not So Cold in Edge Clouds: A Cost-Effective Online Approach},
  journal = {IEEE Transactions on Mobile Computing},
  year = {2024},
  volume = {23},
  pages = {8789-8802},
  doi = {10.1109/tmc.2024.3355118},
  note = {verified via Crossref; grade B}
}

@article{li2024online,
  author = {Li, Zhenzheng and Lou, Jiong and Wu, Jianfei and Guo, Jianxiong and Tang, Zhiqing and Shen, Ping and Jia, Weijia and Zhao, Wei},
  title = {Online Container Scheduling With Fast Function Startup and Low Memory Cost in Edge Computing},
  journal = {IEEE Transactions on Computers},
  year = {2024},
  volume = {73},
  pages = {2747-2760},
  doi = {10.1109/tc.2024.3441836},
  note = {verified via Crossref; grade B}
}

@inproceedings{cao2025dynamic,
  author = {Cao, Shichen and Wang, Shaowei},
  title = {Dynamic Container Placement at Serverless Edge: An Online Convex Optimization Method},
  booktitle = {2025 IEEE 34th Wireless and Optical Communications Conference (WOCC)},
  year = {2025},
  pages = {66-70},
  doi = {10.1109/wocc63563.2025.11082211},
  note = {verified via Crossref; grade B}
}

@inproceedings{huang2025online,
  author = {Huang, Wei and Combes, Richard and Araldo, Andrea and Castel-Taleb, Hind and Jouaber, Badii},
  title = {Online Learning for Function Placement in Serverless Computing},
  booktitle = {2025 IEEE 11th International Conference on Network Softwarization (NetSoft)},
  year = {2025},
  pages = {294-302},
  doi = {10.1109/netsoft64993.2025.11080544},
  note = {verified via Crossref; grade B}
}

@article{li2025online,
  author = {Li, Zhenzheng and Lou, Jiong and Tang, Zhiqing and Guo, Jianxiong and Wang, Tian and Jia, Weijia and Zhao, Wei},
  title = {Online Layer-Aware Joint Request Scheduling, Container Placement, and Resource Provision in Edge Computing},
  journal = {IEEE Transactions on Services Computing},
  year = {2025},
  volume = {18},
  pages = {328-341},
  doi = {10.1109/tsc.2024.3504237},
  note = {verified via Crossref; grade B}
}

@article{choupani2025joint,
  author = {Choupani, Armin and Azizi, Sadoon and Aslanpour, Mohammad Sadegh},
  title = {Joint resource autoscaling and request scheduling for serverless edge computing},
  journal = {Cluster Computing},
  year = {2025},
  volume = {28},
  pages = {171},
  doi = {10.1007/s10586-024-04870-0},
  note = {verified via Crossref; grade B}
}

@article{peng2025joint,
  author = {Peng, Yong and Zhang, Miao and Zhou, Zhi and Huang, Hao},
  title = {Joint container orchestrating and request routing for serverless edge computing-based simulation applications},
  journal = {Journal of Network and Computer Applications},
  year = {2025},
  volume = {243},
  pages = {104284},
  doi = {10.1016/j.jnca.2025.104284},
  note = {verified via Crossref; grade B}
}

@inproceedings{chen2025dike,
  author = {Chen, Chen and Carlini, Emanuele and Mortier, Richard},
  title = {Dike: Deep Reinforcement Learning For Function Scheduling in SLO-targeted Serverless Edge Computing},
  booktitle = {2025 IEEE Symposium on Computers and Communications (ISCC)},
  year = {2025},
  pages = {1-6},
  doi = {10.1109/iscc65549.2025.11326247},
  note = {verified via Crossref; grade B}
}

@inproceedings{subedi2025energyaware,
  author = {Subedi, Shrijan and Kumar, Satish and Jawad, Nawar and Kor, Ah Lian},
  title = {Energy-Aware Latency Optimization for Scheduling Serverless Workload in Edge Computing Environment},
  booktitle = {Proceedings of the 18th IEEE/ACM International Conference on Utility and Cloud Computing},
  year = {2025},
  pages = {1-10},
  doi = {10.1145/3773274.3774276},
  note = {verified via Crossref; grade B}
}

@article{marcelino2025databelt,
  author = {Marcelino, Cynthia and Guelmino, Leonard and Pusztai, Thomas and Nastic, Stefan},
  title = {Databelt: A continuous data path for serverless workflows in the 3D compute continuum},
  journal = {Journal of Systems Architecture},
  year = {2025},
  volume = {168},
  pages = {103577},
  doi = {10.1016/j.sysarc.2025.103577},
  note = {verified via Crossref; grade B}
}

@article{jayanthi2026quantuminspired,
  author = {Jayanthi, M. and Shirisha, A. Sharada and Kovvur, Ram Mohan Rao},
  title = {Quantum-inspired bi-level scheduling for resource-aware serverless function deployment in edge computing},
  journal = {Discover Computing},
  year = {2026},
  volume = {29},
  pages = {582},
  doi = {10.1007/s10791-026-10504-3},
  note = {verified via Crossref; grade B}
}

@inproceedings{farhadi2026scheduling,
  author = {Farhadi, Vajiheh},
  title = {Scheduling Real-Time Serverless Smart Grid Workflows with Chain-Aware DRL},
  booktitle = {2026 35th International Conference on Computer Communications and Networks (ICCCN)},
  year = {2026},
  pages = {1-6},
  doi = {10.1109/icccn69946.2026.11662819},
  note = {verified via Crossref; grade B}
}

@inproceedings{nan2025datalocalityaware,
  author = {Nan, Andrei-David and Spătaru, Adrian Florin},
  title = {Data-Locality-Aware Scheduling for Serverless Containerized Workflows Across the Edge-Cloud Continuum},
  booktitle = {2025 27th International Symposium on Symbolic and Numeric Algorithms for Scientific Computing (SYNASC)},
  year = {2025},
  pages = {126-134},
  doi = {10.1109/synasc69064.2025.00026},
  note = {verified via Crossref; grade B}
}

@article{zolfaghari2025dynamic,
  author = {Zolfaghari, Behrooz and Abrishami, Saeid and Rasoolzadegan, Abbas and Javadi, Bahman},
  title = {Dynamic Function Placement and Request Scheduling of Serverless Workflows in Edge Environment},
  journal = {IEEE Transactions on Services Computing},
  year = {2025},
  volume = {18},
  pages = {2781-2793},
  doi = {10.1109/tsc.2025.3592226},
  note = {verified via Crossref; grade C}
}

@misc{pusztai2024hyperdrive,
  author = {Thomas Pusztai and Cynthia Marcelino and Stefan Nastić},
  title = {HyperDrive: Scheduling Serverless Functions in the Edge-Cloud-Space 3D Continuum},
  year = {2024},
  doi = {10.48550/arxiv.2410.16026},
  note = {arXiv preprint; verified via OpenAlex; grade C}
}

@article{giagkos2024aidriven,
  author = {Giagkos, Dimitrios and Tzenetopoulos, Achilleas and Masouros, Dimosthenis and Xydis, Sotirios and Catthoor, Francky and Soudris, Dimitrios},
  title = {AI-Driven QoS-Aware Scheduling for Serverless Video Analytics at the Edge},
  journal = {Information},
  year = {2024},
  volume = {15},
  pages = {480},
  doi = {10.3390/info15080480},
  note = {verified via Crossref; grade C}
}

@article{xu2026structureaware,
  author = {Xu, Donghong and Ding, Zhaoyan},
  title = {Structure-Aware Serverless Orchestration via Graph Reinforcement Learning: Joint Optimization of Function Fusion and Placement},
  journal = {IEEE Transactions on Services Computing},
  year = {2026},
  volume = {19},
  pages = {3648-3660},
  doi = {10.1109/tsc.2026.3724938},
  note = {verified via Crossref; grade C}
}

@inproceedings{xu2026adaptive,
  author = {Xu, Changfu and Mao, Xiao and Huang, Haiyang and Tang, Zhiqing and Zou, Haodong and Liang, Yuzhu},
  title = {Adaptive Two-timescale Joint Service Placement and Request Scheduling for Efficient Edge AIGC},
  booktitle = {IEEE INFOCOM 2026 - IEEE Conference on Computer Communications},
  year = {2026},
  pages = {1-6},
  doi = {10.1109/infocom59046.2026.11571701},
  note = {verified via Crossref; grade C}
}
```


---

# Update 2026-10-20: positioning of the look-ahead / hybrid direction (method-level queries, search only)

Why: after D1-D3, the RL/Heu comparison and RLLA, the candidate direction is a **hybrid**: on-demand placement when capacity is available, and **simulation-judged, look-ahead capacity re-planning** (O3S, "rollout"-style) when it is tight, triggered by predicted regime/burst signals, with a break-even rule for the look-ahead length. This pass asks what already exists around those ingredients. Nothing downloaded. Tools: web search (US-only index, weak for 2025-26) and OpenAlex lookup (**rate-limited, HTTP 429, for most of the session**). Metadata was machine-verified only where stated; everything else is **abstract/secondary-summary level and must be checked before citing**.

## 1. Weighted table (new candidates)

| Grade | Autor Jahr | Kurztitel | OA/Zugang | DOI/Link | Verification | Relation to our direction |
|---|---|---|---|---|---|---|
| A | Nguyen 2025 | taming-cold-starts-mpc | ● Bibliothek (in wiki, G0) | [10.1109/MASCOTS67699.2025.11283271](https://doi.org/10.1109/MASCOTS67699.2025.11283271) | verified (arXiv 2508.07640 title match) | closest prior art for "forecast + receding horizon + pre-warming"; OpenWhisk, single functions; no workflows, no node-level layout |
| A | Mahgoub 2022 | orion-three-rights | ○ USENIX (open) | [usenix.org/conference/osdi22/presentation/mahgoub](https://www.usenix.org/conference/osdi22/presentation/mahgoub) | **metadata not machine-verified** (lookup timed out) | workflow-level (DAG) sizing, bundling, **pre-warming with a look-ahead time for downstream functions**; cloud, trace-based, not forecast/edge |
| A | Daw et al. 2020 | xanadu-cascading-cold-start | ✗ original not located | not found (only secondary descriptions) | **unverified; primary source not found** | speculative pre-loading along the **most likely path of a workflow** using branch probabilities: prior art for "a burst at stage 1 predicts later stages" (our ablation C) |
| A | Gupta, Islam & Buyya 2025 | hybrid-reactive-proactive-edge | ✓ OA (arXiv) | [arXiv 2512.14290](https://arxiv.org/abs/2512.14290) | verified (title, authors, year) | hybrid reactive + ML-forecast autoscaling for SLA-bound edge (Kubernetes); regime-hybrid exists for scaling, not for workflow placement |
| B | Fuerst & Sharma 2021 | faascache-greedy-dual | hybrid | [10.1145/3445814.3446757](https://doi.org/10.1145/3445814.3446757) | verified (DOI resolves to this title) | keep-alive as caching (Greedy-Dual); amortization logic for warm containers |
| B | Roy, Patel & Tiwari 2022 | icebreaker | ✓ OA (author copy at par.nsf.gov) | par.nsf.gov purl 10355252 | **DOI not verified** | prediction-driven warm-up on heterogeneous nodes; savings depend on heterogeneity (per the MPC paper) |
| B | Shahrad 2020 | serverless-in-the-wild | ● Bibliothek | [arXiv 2003.03423](https://arxiv.org/abs/2003.03423) | in wiki (G0) | hybrid histogram keep-alive: regime-dependent policy per function |
| B | Purohit 2018; Wei 2020 | ski-rental-with-predictions | ● Bibliothek | in wiki (G0) | in wiki | theory for "act on a prediction, but keep a robustness guarantee": basis for a break-even rule |
| B | Bertsekas (rollout survey; Bertsekas, Tsitsiklis & Wu 1997; 2020 book) | rollout-policy-improvement | ○ MIT author page | [mit.edu/~dimitrib/Rollouts_Survey.pdf](https://www.mit.edu/~dimitrib/Rollouts_Survey.pdf) | **found as web hit only; bibliographic data to be fixed** | **O3S is a rollout algorithm** (base policy B*, simulation-based one-step lookahead); gives the known improvement property over the base policy and the right name for the method |
| B | Deng et al. 2022 | dependent-function-embedding | closed | TPDS 33(10):2346-2357 (cited by DFPS as [19]) | **not verified in this pass** | DAG function placement on edge with traffic splitting on an Alibaba trace: related placement baseline |
| C | Ray, Banerjee & Narendra 2020 | proactive-microservice-placement-migration | closed | IEEE SEC 2020 (details to verify) | **unverified** | learning-based proactive placement/migration for mobile edge; not serverless workflows |
| C | "Performance Optimization for Edge-Cloud Serverless Platforms via Dynamic Task Placement" | simulator-decision-engine | ✓ OA (arXiv) | [arXiv 2003.01310](https://arxiv.org/abs/2003.01310) | **hit not confirmed to be the simulator paper; check** | an event-driven simulator that predicts latency and cost per candidate configuration (a what-if evaluator), closest found to "judge by simulation" |
| C | Hybrid proactive-reactive autoscaling family (Chameleon; OptScaler) | proactive-reactive-autoscaling | mixed | via web search | **unverified** | evidence that proactive + reactive fallback is standard in autoscaling |

## 2. Findings (abstract/secondary-summary level)

1. **Not novel on their own:** predictive pre-warming, receding-horizon (MPC) control, hybrid reactive/proactive switching, break-even keep-alive rules, and workflow-aware pre-warming (ORION, Xanadu) all exist.
2. **O3S has a name:** it is a **rollout** policy (one-step lookahead by simulation over a base policy). Positioning the method as "rollout applied to edge serverless workflow placement" is more accurate than presenting the mechanism as new. No application of rollout to serverless placement was found, but this is a search-tool result, not a proven absence.
3. **Our "burst at stage 1 predicts later stages" idea (ablation C) is close to Xanadu** (most-likely-path speculation) and ORION's downstream pre-warming. It needs differentiation or should be cited as the basis.
4. **Not found (G0 conclusion confirmed, with tool caveats):** (a) layouts of containers for serverless workflows at the edge chosen by simulating the **real scheduler** over a predicted look-ahead window; (b) an explicit **switching/migration cost** for serverless DAG re-placement at the edge; (c) evidence of the **regime dependence** we measured (per-request RL wins with spare capacity, planned capacity wins under pressure) against both RL and DFPS-style baselines.
5. **Where novelty can rest:** the combination (workflow-level, edge, node-level layout re-planning, simulation-in-the-loop with the real scheduler, regime-aware trigger) plus the empirical headroom analysis against the best existing method. The risk is moderate: each ingredient has precedent.

## 3. Queries and which term produced which hit

- shared library (bib-search, aliases OR-ed): "model predictive"/"receding horizon"/MPC -> nguyen-2025 (9 pages); prewarm*/keep-alive/warm pool -> shahrad-2020, ma-2025, nguyen-2025; proactive AND (autoscal* OR placement) -> nguyen-2025, jayanthi-2026, ahmadpanah-2026; forecast* AND serverless -> nguyen-2025, jayanthi-2026; "ski rental"/break-even -> wei-2020, purohit-2018; hysteresis/cooldown/thrashing -> ahmadpanah-2026, guo-2026; oracle/clairvoyant/hindsight -> wei-2020, purohit-2018. **29 documents indexed; no new local gaps.**
- web search (standard): predictive autoscaling serverless workflows prewarm DAG -> Nguyen 2025, ORION; Xanadu speculative prewarm -> secondary descriptions only; IceBreaker/FaasCache keep-alive -> IceBreaker, FaasCache, Shahrad; MPC autoscaling microservices Kubernetes -> NeuroScaler (arXiv 2602.08191, container autoscaling MPC, energy), SLO-driven cost-aware autoscaler (arXiv 2512.23415); rollout/ADP scheduling -> Bertsekas survey, rollout in project scheduling and replicated-system recovery; hybrid reactive-proactive -> Gupta 2025, OptScaler, Chameleon; simulation lookahead / digital twin -> simulator-based configuration selection (see table), no serverless digital-twin lookahead; clairvoyant/learning-augmented keep-alive -> keep-alive for Hawkes processes, reusable-resource online allocation (no serverless learning-augmented paper); workflow-aware proactive placement edge -> Deng 2022, Ray 2020, FaaSEdge thesis, ORION.
- OpenAlex lookups (search_works, citation_neighbours): **failed (HTTP 429 / timeout)**; verification used arXiv and DOI lookups only.

## 4. Limits of this pass

- No full texts read; every statement is from abstracts or search summaries.
- The web index is US-only and thin for 2025-2026: a 2026 pre-emption could be missing. Repeat the OpenAlex queries (title/abstract boolean, 2025+) when the rate limit lifts, and read the Xanadu and ORION primary sources before the related-work section is written.
- Follow-up searches: "rollout" + serverless/edge; "switching cost" + serverless workflow; Xanadu primary source; learning-augmented keep-alive; cited-by lists of Nguyen 2025 and ORION.

## 5. Full titles of the four papers requested from the user (2026-10-20)

| Priority | Full reference | Status of the title |
|---|---|---|
| 1 | Y. Lei, M. Zhou, P. Daniëlse and Z. Zhao, "Multi-Agent Based Time Critical FaaS Scheduling in Edge-Cloud Continuum," IEEE International Parallel and Distributed Processing Symposium Workshops (IPDPSW), 2026. DOI 10.1109/ipdpsw71298.2026.00085. Suggested file: `lei-2026-multi-agent.pdf` | verified (OpenAlex lookup by DOI) |
| 2 | N. Daw, U. Bellur and P. Kulkarni, "Xanadu: Mitigating cascading cold starts in serverless function chain deployments," Proceedings of the 21st International Middleware Conference (Middleware '20), pp. 356-370, 2020. Suggested file: `daw-2020-xanadu.pdf` | from a web-search summary; ACM DOI not found, not machine-verified |
| 3 | S. Deng, H. Zhao, Z. Xiang, C. Zhang, R. Jiang, Y. Li, J. Yin, S. Dustdar and A. Y. Zomaya, "Dependent function embedding for distributed serverless edge computing," IEEE Transactions on Parallel and Distributed Systems, vol. 33, no. 10, pp. 2346-2357, 2022. Suggested file: `deng-2022-dependent-function-embedding.pdf` | taken from the DFPS paper's own reference list (its [19]) |
| 4 | K. Ray, A. Banerjee and N. C. Narendra, "Proactive Microservice Placement and Migration for Mobile Edge Computing," IEEE/ACM Symposium on Edge Computing (SEC), pp. 28-41, 2020. Suggested file: `ray-2020-proactive-placement.pdf`. Journal extension (may be easier to get): "Learning-Based Microservice Placement and Migration for Multi-Access Edge Computing," IEEE Transactions on Network and Service Management, vol. 21, no. 2, pp. 1969-1982, 2024, DOI 10.1109/TNSM.2023.3344192 | from DBLP via web search; DOI of the journal version from the same source, not machine-verified |

## 6. Full-text reads of the four papers supplied by the user (2026-10-20)

PDFs registered in the shared library as `lei-2026-multi-agent.pdf`, `daw-2020-xanadu.pdf`, `deng-2022-dependent-function-embedding.pdf`, `ray-2020-proactive-placement.pdf` (renamed from the user's own file names after checking title and authors on page 1). Reading depth: **Lei 2026 in full; Xanadu: abstract, introduction, key ideas (MLP, aggressiveness, JIT), implementation and future work; Deng 2022 and Ray 2020: abstract, introduction, problem model, algorithm outline, evaluation set-up and conclusion, not every proof or table.** No wiki source pages written yet (ingest not run).

| Paper | What it does | What it does not do (relative to our direction) | Pre-emption of our direction |
|---|---|---|---|
| **Lei et al. 2026** (IPDPSW) | Switches the **scheduling architecture** (centralized / federated / decentralized control) at runtime. Trigger: per-function **p95/p50 latency ratio** over a sliding window, mapped by soft/hard thresholds to a traffic split between architectures, exponentially smoothed (smoothing factor from the change of the query rate); thresholds fitted by grid search on testbed data. OpenFaaS on 6 VMs, matrix-multiplication function, 1000 requests per run, compared with its own static architectures. | No workflows (single functions), no container layout or capacity re-planning, no look-ahead or prediction (purely **reactive**, threshold + smoothing), no simulation, no comparison with DFPS-type placement or RL baselines. It cites DFPS only as placement within a fixed architecture. It states the switch is about the control structure, "not merely adjust placements or replica counts". | **Not pre-empted.** Related only in the idea of switching regime on a tail signal. Its reactive trigger is the kind our D1 heuristic result warns about for placement. |
| **Daw, Bellur & Kulkarni 2020** (Middleware '20, DOI 10.1145/3423211.3425690) | Cloud FaaS platform "Xanadu" against **cascading cold starts in function chains**. Estimates the **most likely path (MLP)** of a workflow from branch probabilities (exponentially averaged), plans a timeline from profiled cold-start and warm-run times and deploys each sandbox **just in time** for its expected invocation; a provider-side **speculation aggressiveness** parameter limits how far down the chain it provisions; stops speculating on a prediction miss; detects implicit chains. Linear and conditional chains; Node.js testbed; compared with Knative and OpenWhisk; reports about 18x lower platform overhead than Knative and 10x than OpenWhisk for short workflows. | Cloud platform, not edge: no multi-node layout, no placement across servers, no data-transfer cost, no re-planning of container counts. Predicts **which functions of one request** run next, not aggregate traffic bursts across requests. | **Closest prior art for ablation C.** "When stage 1 of a request starts, warm stage 2 just in time" is Xanadu's mechanism. Our version differs only if it forecasts **aggregate downstream load** to size container counts and layouts across edge nodes. Its **aggressiveness = fraction of the chain depth to look ahead** is the same trade-off as our look-ahead length. |
| **Deng et al. 2022** (TPDS 33(10), "Dependent Function Embedding", DPE) | **Offline** placement of one DAG on heterogeneous edge servers with **splitting of each data flow over several network paths**; dynamic programming, proved globally optimal for a given topological order; Alibaba cluster trace; beats FixDoc and HEFT by 43.2% and 40.7% in makespan. The authors state it is an **offline algorithm** and leave online scenarios to future work. | No online or dynamic re-placement, no traffic forecasting, no containers or cold starts, no queueing across concurrent requests, no baseline of the DFPS or RL type. | **Not pre-empted.** A related static DAG-placement baseline; supports the claim that online, load-aware re-planning is open. |
| **Ray, Banerjee & Narendra 2020** (SEC '20, DOI 10.1109/SEC50012.2020.00010) | **Proactive prefetching and migration of microservices** for a mobile user with a **linear** microservice workflow, using the workflow dependency structure and the user's mobility; MDP with unknown rewards solved with reinforcement learning; San Francisco taxi traces; compared with on-demand strategies. Accounts for state-migration cost of deployed but unused services. | One user's mobility, not aggregate request load; linear workflows only; microservices, not serverless containers with cold starts; no look-ahead simulation of a scheduler; no regime logic. | **Not pre-empted.** Prior art for "prefetch along the workflow before it is needed" and for counting migration cost. |

### Consequences for the positioning

1. **The stage-based prediction idea is not ours.** Prefetching or pre-warming downstream stages from workflow structure is established (Xanadu 2020 for serverless chains; Ray 2020 for microservice workflows; ORION 2022 for DAGs). If used, cite them and state the difference (aggregate load forecasts that size layouts across edge nodes).
2. **Regime switching with a reactive tail-latency trigger exists** (Lei 2026) but on the control-plane architecture, for single functions, without workflows or capacity re-planning. It does not cover our direction, and its purely reactive trigger gives no look-ahead.
3. **Deng 2022 and Lei 2026 both state their limits** (offline only; architecture-level only), which is consistent with the gap we found: online, look-ahead, simulation-judged layout re-planning for serverless workflows at the edge.
4. **Updated G0 reading:** still not pre-empted on the evidence read so far, but the novelty is the combination (workflow-level edge layouts + simulation-in-the-loop with the real scheduler + regime-aware trigger + evidence against RL and DFPS baselines), not any single ingredient.
5. **Open items:** read ORION and Gupta 2025 in full (open access); re-run the OpenAlex queries when the rate limit lifts; ingest the four sources into the wiki if a related-work section is planned.

## 7. Update 2026-10-20 (later): ORION and Gupta 2025 read, six sources ingested

- **ORION** (Mahgoub et al., OSDI 2022): read in full. Stage-wise pre-warming of serverless DAGs from latency CDFs with a utilisation target, plus sizing and bundling; unlimited-capacity cloud, no queueing, no edge, first-stage delay fixed at zero because arrivals are not predicted, no dynamic DAGs. Does not pre-empt.
- **Gupta, Islam & Buyya 2025** (arXiv 2512.14290): read in full. Hybrid autoscaler for edge microservices: replicas = larger of the forecast-based and the reactive count, small online LSTM, hyper-parameter feedback on SLA violations. No workflows, no placement, no oracle bound. Does not pre-empt; cite as hybrid reactive/proactive prior art.
- Wiki source pages: gupta-2025-hybrid-reactive-proactive, mahgoub-2022-orion, lei-2026-multi-agent, daw-2020-xanadu, deng-2022-dependent-function-embedding, ray-2020-proactive-placement. Section 6 reading-depth note ("no wiki source pages yet") is superseded.
- Open: re-run the OpenAlex queries when the rate limit lifts; Kraken (Bhasi et al., SoCC 2021, cascading cold starts in dynamic DAGs) is named by ORION and Xanadu-adjacent work and not yet in the library.

## 8. Update 2026-10-22: novelty and baseline search for the busiest-first rule

Scope: (a) is backlog-driven, per-function re-layout with a churn cap already published; (b) later papers that cite or extend DFPS; (c) baselines close to the rule that we should beat. Method: web search plus abstract pages (arXiv); Fifer and Kraken read from their PDFs (design sections). Limits: Springer papers (paywalled) seen only through search snippets; OpenAlex tools were not available; citing-paper lists could not be retrieved, only papers that mention DFPS in snippets.

### 8.1 Closest prior art for the *sizing* idea (cloud, chains or DAGs, no fixed edge capacity)

| Work | What it does (read) | What it does not do |
|---|---|---|
| **Fifer** (Gunasekaran et al., Middleware 2020, DOI 10.1145/3423211.3425683) | Per-stage container scaling for microservice **chains**. Reactive: Nc = pending queue length / batch size per stage, but a container is spawned only if the queuing delay of waiting exceeds the **cold start** (Df > Cd), i.e. a built-in cost check. Slack split over stages in proportion to execution time; request batching; LSTM load prediction for proactive spawning. Baselines Bline, SBatch, RScale. | Chains only; one Kubernetes cluster with containers added freely (no fixed total slots, no multi-node placement, no data-transfer cost); no re-layout of an existing placement; no churn cap. |
| **Kraken** (Bhasi et al., SoCC 2021, DOI 10.1145/3472883.3486992) | Per-function containers for **dynamic DAGs**: predicted load (EWMA) x invocation probability, plus Connectivity and Commonality weights (capped against over-provisioning); slack-aware batching; reactive correction. Compared with Archipelago, Fifer, Xanadu on OpenFaaS. | Cloud cluster; sizing only; no placement choice by data affinity; no capacity limit; no migration cost. |
| **Kubernetes HPA / Knative KPA** | desired = ceil(current x metric / target); KPA: per-revision concurrency target, 60 s stable window, 6 s panic window, panic at 2x. | Per service, not workflow-aware; no placement. |
| Xanadu (2020), ORION (2022), Gupta (2025) | Already in the wiki (stage-wise pre-warming; hybrid max(forecast, reactive) replica rule). | See their pages. |

**Consequence:** the idea "size each function's containers from its recent load and its queue backlog, with a utilisation margin" is **not new**. Fifer (2020) already derives container counts from queue length and checks the cold-start cost; Kraken (2021) sizes per DAG function. HPA's target utilisation is our 0.8. The rule's own ingredients cannot be the contribution.

### 8.2 What I did not find (gap, with the caveat that coverage is partial)

No paper found that combines: workflow DAGs at the edge, a **fixed** total of container slots across many edge nodes (so sizing is a reallocation), a whole-layout re-plan on top of DFPS's initial placement, data-affinity placement, and an explicit **churn / migration cap**. The nearest edge works: ESFF (Lou et al., ICC 2024, arXiv 2310.16475: single-function scheduling at the edge with cold-start limiting), ClusterLess (Farahani et al., ICDCS 2026, arXiv 2605.04310: deadline-aware DAG orchestration across edge clusters; scaling details not visible), Scale (Chen et al., arXiv 2605.15704, May 2026: request-level DRL container scheduling, no workflows).

### 8.3 Later papers that mention or extend DFPS (snippets only)

- arXiv 2610.15886 (Oct 2026), multi-objective workflow scheduling across IaaS/FaaS: lists DFPS in its references; named baselines are a genetic algorithm and greedy (no DFPS baseline visible).
- Quantum-inspired bi-level scheduling for serverless deployment at the edge (Springer 2026): cites Zolfaghari et al.; reports 20-29% lower cold-start latency against existing techniques; full text not accessible.
- arXiv 2608.14427 (Aug 2026, IEEE Access), large-scale workflow placement by integer nonlinear programming: static placement, baseline "simple deployment heuristic".
- No paper found that uses DFPS as an experimental baseline or reports dynamic re-layout above it. Re-check full texts of the two Springer papers and ClusterLess before claiming this.

### 8.4 Baselines to add if we want to claim "beats the state of the art"

1. **HPA/KPA-style target-concurrency scaler** per function (load / 0.8, stable window): equals our rule without the backlog term; shows what backlog adds.
2. **Fifer-style reactive scaler**: containers from queue length / batch size, with the cold-start check Df > Cd; adapted to a fixed slot budget by proportional shrinking.
3. **Kraken-style proactive scaler**: EWMA load x invocation probability (+ connectivity/commonality weights).
4. Already available: B* (DFPS), RL (MOSEC), Heu (Xu et al.).
Without 1-3 the claim is only "better than DFPS-B* and our RL/Heu reimplementations". Fifer's cold-start check is also the "is it worth it" test our rule lacks, so it doubles as a churn-control baseline.

### 8.5 Related critique

arXiv 2502.14320 ("It Takes Two to Tango", 2025) argues Fifer, Kraken and Xanadu assume low execution-time variance and under-provision under high-variance production traces. Useful framing, not yet read.

Verification status: Fifer and Kraken metadata checked on their PDFs and ACM landing pages; Scale, ClusterLess and the INLP paper checked on arXiv abstract pages; ESFF, 2610.15886, SFSO and the Springer papers seen only in search results (unverified, not added to BibTeX).
