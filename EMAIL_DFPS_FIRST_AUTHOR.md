**To:** [first author's email, from the paper's first page]
**Subject:** Questions about reproducing "Dynamic Function Placement and Request Scheduling of Serverless Workflows in Edge Environment" (IEEE TSC 2025)

Dear Dr. Zolfaghari,

My name is Ahoora Amini, and I am a Master's student at Iran University of Science and Technology (IUST). I am re-implementing DFPS as a baseline for my research on serverless workflow placement. I found your paper very clear and useful, and I would like to follow your experimental setup as closely as possible. A few details were not specified in the paper, so I would be very grateful if you could clarify any of the following (short answers are fine):

1. Workflows: how were the 15 workflows chosen from the Alibaba cluster trace (random sampling, size limits, any filtering beyond execution time under one minute)? How was the one-minute execution time measured?
2. Function types: how are the tasks of a workflow mapped to function types, and how many distinct function types (N_f) are used?
3. Random parameters: Table 2 gives ranges only. Were the values (runtimes, cold starts, state sizes, node capacities) drawn uniformly from these ranges, and how is the edge node at which each request arrives chosen?
4. Simulated annealing: what are the initial and final temperatures, the cooling schedule, and the number of iterations per 4-second replacement step?
5. Pattern matching: Section 4.2 outlines the method of [39] (several spanning trees, missing paths replaced by shortest paths). How many spanning trees or candidate matches were kept, and how were storage and function-capacity constraints handled during matching?
6. Metrics: how exactly is "resource utilization" computed, and over which time window (warm-up and measurement period) are makespan and cold starts measured? How long was each simulation run?
7. Baselines: how were Heu [18] and RL [28] adapted to your system model (resources, cost versus delay objective, per-request handling, container keep-alive or idle time-out)? For RL, what were the training budget, epsilon schedule, and the state and action definitions?
8. Network: which GT-ITM parameters were used to generate the topologies?
9. Two equations: I may be misreading them, but Equation 3 (proportionality) seems to evaluate to zero for any placement as printed, and Equation 6 seems to lack the P0 (empty-system probability) term of the M/M/c queue. Could you confirm the intended forms?

If it is possible to share the simulation configuration or code (even partially), it would help me reproduce your results faithfully and cite your work correctly. I will of course acknowledge your help in any resulting publication.

Thank you very much for your time.

Kind regards,
Ahoora Amini
Master's student, Iran University of Science and Technology (IUST)
ahoora_amini@cmps2.iust.ac.ir
