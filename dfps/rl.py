"""RL baseline: MOSEC, Yang et al., "Multi-objective deep reinforcement learning for function offloading in serverless edge
computing", IEEE TSC 18(1), 2025, adapted to the DFPS system model (BASELINES_SPEC.md, AB-R1..AB-R7).

Kept from the paper (Sec.IV-V): MOMDP/DDQN formulation, state = (function features u_t, channel/transfer conditions g_t,
server capacity/state c_t), action = execution location, reward = negative increment of completion time (r^T), DDQN with two
identical networks, 2 hidden layers x 64 neurons, Tanh, Adam lr 0.001, gamma 0.99, replay buffer 5000, batch 64, and the
Neighbor-Experience-Replay (NER, Alg.1) sampling with lambda = 3 (draw lambda*b transitions, keep the b closest to the
current state). Loss: mean squared error (Alg.2 l.19).
Adaptations (not in the paper; labelled in BASELINES_SPEC.md):
* AB-R1 the action space is the 80 edge nodes; the Q-network scores ONE node from [task features, node features] (shared
  weights, so the same policy works for any node count/topology) and the action is the arg-max over the nodes;
* AB-R2 makespan only: the preference vector is the constant w = (1, 0, 0); the EF scheme and preference distances of NER
  vanish, NER uses the state distance only;
* AB-R3 the reward of a task is minus its response time (finish time - time it became ready), scaled by 1/10 s: the
  increment of the request's completion time that this task adds when it lies on the critical path;
* AB-R5 epsilon-greedy 1.0 -> 0.05 linearly over the first 40% of the training decisions; one gradient step per 4
  decisions; hard target-network copy every 500 gradient steps (the paper says both 'every N-step' and 'every N-episode');
  gradient-norm clip 10; learning across several training workloads, evaluated on separate test seeds with epsilon = 0."""
from __future__ import annotations

import numpy as np
import torch
from torch import nn

D_TASK, D_NODE = 4, 10
D = D_TASK + D_NODE


def squash(x, c):
    return x / (x + c)


class QNet(nn.Module):
    """Q(s, a) for every node a: shared MLP 2 x 64, Tanh, applied to [task features, node features of a]."""

    def __init__(self, d=D, hidden=64):
        super().__init__()
        self.net = nn.Sequential(nn.Linear(d, hidden), nn.Tanh(), nn.Linear(hidden, hidden), nn.Tanh(), nn.Linear(hidden, 1))

    def forward(self, x):                 # x: [..., N, d] -> [..., N]
        return self.net(x).squeeze(-1)


class Buffer:
    def __init__(self, cap, n, d):
        self.cap, self.n, self.size, self.pos = cap, n, 0, 0
        self.s = np.zeros((cap, n, d), np.float32)
        self.s2 = np.zeros((cap, n, d), np.float32)
        self.m = np.zeros((cap, n), bool)
        self.m2 = np.zeros((cap, n), bool)
        self.a = np.zeros(cap, np.int64)
        self.r = np.zeros(cap, np.float32)

    def add(self, s, m, a, r, s2, m2):
        i = self.pos
        self.s[i], self.m[i], self.a[i], self.r[i], self.s2[i], self.m2[i] = s, m, a, r, s2, m2
        self.pos = (self.pos + 1) % self.cap
        self.size = min(self.size + 1, self.cap)

    def ner_sample(self, cur, b, lam, rng):
        """NER (Alg.1): draw lam*b transitions uniformly, rank them by the Euclidean distance between their state and the
        current state (smaller = more similar; AB-R7), keep the b most similar."""
        k = min(self.size, int(lam * b))
        idx = rng.choice(self.size, k, replace=False)
        if k <= b:
            return idx
        dist = np.linalg.norm(self.s[idx].reshape(k, -1) - cur.reshape(1, -1), axis=1)
        return idx[np.argsort(dist, kind="stable")[:b]]


class Dec:
    __slots__ = ("s", "m", "a", "r", "s2", "m2", "has_r", "has_next")


class MosecPolicy:
    mode = "ready"
    name = "RL"

    def __init__(self, seed=0, train=False, qnet=None, total_train_decisions=200000, gamma=0.99, lr=1e-3, batch=64,
                 lam=3, buffer=5000, eps=(1.0, 0.05), eps_frac=0.4, train_every=4, target_every=500, clip=10.0,
                 reward_scale=10.0):
        self.rng = np.random.default_rng(seed)
        torch.manual_seed(seed)
        self.train, self.q = train, qnet if qnet is not None else QNet()
        self.gamma, self.batch, self.lam, self.reward_scale = gamma, batch, lam, reward_scale
        self.train_every, self.target_every, self.clip = train_every, target_every, clip
        self.eps0, self.eps1 = eps
        self.eps_steps = max(1, int(eps_frac * total_train_decisions))
        self.n_dec = 0
        self.n_grad = 0
        self.buf_cap = buffer
        self.buf = None
        self.last = None
        self.losses = []
        if train:
            self.target = QNet()
            self.target.load_state_dict(self.q.state_dict())
            self.opt = torch.optim.Adam(self.q.parameters(), lr=lr)

    def attach(self, sim):
        self.sim = sim
        self.last = None
        if self.train and self.buf is None:
            self.buf = Buffer(self.buf_cap, sim.N, D)

    # --- state ----------------------------------------------------------------------------------------------
    def features(self, sim, r, t):
        """[N, D] feature matrix and the feasibility mask (a node needs room for the task's input states)."""
        wf, f, N = r.wf, r.wf.ft[t], sim.N
        total = wf.input_total(t)
        out_mb = sum(wf.ss[(t, c)] for c in wf.children[t])
        u = np.array([squash(total, 30.0), squash(sim.exec_time[f], 6.0), squash(sim.cold_start[f], 6.0), squash(out_mb, 30.0)])
        if wf.parents[t]:
            xfer = np.stack([sim.net.h[r.plan[p]] * (wf.ss[(p, t)] / sim.net.bw) for p in wf.parents[t]])
        else:
            xfer = (sim.net.h[r.origin] * (wf.input_size / sim.net.bw))[None]
        ecc = sim.ecc
        qlen = np.array([len(q) for q in sim.nq])
        resid = ecc - sim.occ - qlen
        g = np.stack([
            (sim.idle[f] > 0).astype(float),                         # warm container of f here
            sim.idle[f] / ecc,
            sim.occ / ecc,
            squash(qlen / ecc, 1.0),
            np.clip(resid / ecc, -1.0, 1.0),
            (sim.tot < ecc).astype(float),                           # a free slot
            np.clip((sim.esc - sim.storage_used) / sim.esc, 0.0, 1.0),
            squash(xfer.max(axis=0), 2.0),
            squash(xfer.sum(axis=0), 2.0),
            squash(sim.qcnt[f] / ecc, 1.0),
        ], axis=1)
        x = np.concatenate([np.broadcast_to(u, (N, D_TASK)), g], axis=1).astype(np.float32)
        mask = (sim.esc - sim.storage_used) >= total
        return x, mask

    # --- decisions ------------------------------------------------------------------------------------------
    def epsilon(self):
        if not self.train:
            return 0.0
        return max(self.eps1, self.eps0 - (self.eps0 - self.eps1) * self.n_dec / self.eps_steps)

    def choose(self, sim, r, t):
        x, mask = self.features(sim, r, t)
        if not mask.any():
            return None
        if self.rng.random() < self.epsilon():
            a = int(self.rng.choice(np.flatnonzero(mask)))
        else:
            with torch.no_grad():
                q = self.q(torch.from_numpy(x)).numpy()
            a = int(np.where(mask, q, -np.inf).argmax())
        self.n_dec += 1
        if self.train:
            d = Dec()
            d.s, d.m, d.a, d.has_r, d.has_next = x, mask, a, False, False
            if self.last is not None:
                self.last.s2, self.last.m2, self.last.has_next = x, mask, True
                self._maybe_push(self.last)
            self.last = d
            r.dec[t] = d
            if self.buf.size >= self.batch and self.n_dec % self.train_every == 0:
                self.update(x)
        return a

    def on_task_done(self, sim, run):
        d = run.dec
        if not self.train or d is None:
            return
        d.r = -(sim.now - run.t_ready) / self.reward_scale
        d.has_r = True
        self._maybe_push(d)

    def _maybe_push(self, d):
        if d.has_r and d.has_next and d.s is not None:
            self.buf.add(d.s, d.m, d.a, d.r, d.s2, d.m2)
            d.s = None                                              # pushed

    # --- learning -------------------------------------------------------------------------------------------
    def update(self, cur):
        b = self.buf
        idx = b.ner_sample(cur, self.batch, self.lam, self.rng)
        loss = self.ddqn_loss(torch.from_numpy(b.s[idx]), torch.from_numpy(b.m[idx]), torch.from_numpy(b.a[idx]),
                              torch.from_numpy(b.r[idx]), torch.from_numpy(b.s2[idx]), torch.from_numpy(b.m2[idx]))
        self.opt.zero_grad()
        loss.backward()
        nn.utils.clip_grad_norm_(self.q.parameters(), self.clip)
        self.opt.step()
        self.n_grad += 1
        self.losses.append(loss.item())
        if self.n_grad % self.target_every == 0:
            self.target.load_state_dict(self.q.state_dict())

    def ddqn_loss(self, s, m, a, r, s2, m2):
        """Double DQN: y = r + gamma * Q_target(s', argmax_a' Q(s', a')); loss = mean squared error (Alg.2 l.19)."""
        qsa = self.q(s).gather(1, a[:, None]).squeeze(1)
        with torch.no_grad():
            q2 = self.q(s2).masked_fill(~m2, -1e9)
            a2 = q2.argmax(dim=1, keepdim=True)
            y = r + self.gamma * self.target(s2).gather(1, a2).squeeze(1)
        return nn.functional.mse_loss(qsa, y)
