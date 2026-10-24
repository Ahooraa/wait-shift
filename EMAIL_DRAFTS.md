# Email drafts (fill in names/affiliation; addresses are on the papers' first pages)

## 1. To the DFPS authors (Zolfaghari et al.)

**Subject:** Questions about reproducing "Dynamic Function Placement and Request Scheduling of Serverless Workflows in Edge Environment" (IEEE TSC 2025)

Dear Dr. Zolfaghari and co-authors,

I am [name], a [position] at [affiliation]. I am re-implementing DFPS as a baseline for my own research on serverless workflow placement, and I found the paper very clear and useful. I would like to follow your setup as closely as possible, and a few details were not specified in the paper. If you could spare a few minutes to clarify any of the following, I would be very grateful (short answers are fine):

1. Workflows: how were the 15 workflows chosen from the Alibaba cluster-trace-v2018 batch_task table (random sampling, size limits, any filtering beyond execution time under one minute)? How was the one-minute duration measured?
2. Function types: how are the tasks of a workflow mapped to function types, and how many distinct function types (f_l) are in the pool?
3. Random parameters: are the values in Table 2 (runtimes, cold starts, state sizes, node capacities) drawn uniformly from the stated ranges? Are the request origin nodes chosen uniformly?
4. Simulated annealing: what are the initial and final temperature, the cooling schedule, and the number of iterations per 4-second replacement step?
5. Pattern matching: the scheduling step builds on reference [39]. Did you use the algorithm exactly as published there, or a modified version (for example regarding K-best tree matching and node-storage handling)?
6. Metrics: how exactly is "utilization" computed, and over which time window (warm-up and measurement period) are makespan and cold starts measured? How long was each run?
7. Baselines: how were Heu [18] and RL [28] adapted to your system model (resources, cost versus delay objective, per-request handling, container keep-alive or idle time-out)? For RL, what were the training budget, epsilon schedule, and state/action definition?
8. Network: which GT-ITM parameters were used for the topology?
9. Two equations: I may be misreading them, but Equation 3 (proportionality) seems to evaluate to zero for any placement as printed, and Equation 6 seems to lack the P0 (empty-system probability) term of the M/M/c queue. Could you confirm the intended forms?

If it is possible to share the simulation configuration or code, even partially, that would help me reproduce your results faithfully and cite your work correctly. I will of course acknowledge your help in any resulting publication.

Thank you very much for your time.

Kind regards,
[name, affiliation, email]

## 2. To the MOSEC authors (Yang et al.)

**Subject:** Request for Appendices A and B of "Multi-Objective Deep Reinforcement Learning for Function Offloading in Serverless Edge Computing" (IEEE TSC 2025)

Dear Dr. Yang and co-authors,

I am [name], a [position] at [affiliation]. I am using MOSEC as a baseline in my research on serverless workflow placement, and I want to implement it faithfully. The paper refers to Appendices A (network structure) and B (learning process), which I could not access in the version I have. Could you please send them, or point me to where they can be downloaded?

I would also be grateful for a short clarification of these points:
1. How are the state s_t = (u_t, g_t, c_t) encoded as network input, and how is the preference vector w fed to the network? What is the output layout?
2. The epsilon schedule, the number of training episodes, and the sampling space of the preference vectors.
3. The target network update: Algorithm 2 (line 22) says "each N-step" while the text says "every N-episode". Which is correct, and what is N?
4. Equations 20-22 write the loss with absolute values, while Algorithm 2 (line 19) uses mean squared errors. Which form was used?
5. The paper defines a priority sequence of the functions of an application. How is this order computed (for example by upward rank or topological order)?
6. If a public implementation is available, could you share the link?

Thank you very much for your time; I will cite your work and acknowledge your help.

Kind regards,
[name, affiliation, email]
