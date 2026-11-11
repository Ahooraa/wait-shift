"""Agents as separate processes (as on the laptops), so the controller and the agents do not share Python's global lock."""
import asyncio
import multiprocessing as mp

from testbed.agent import Agent

TOKEN = "t0k3n"


def _serve(speed, q):
    agent = Agent(TOKEN, None, speed)
    asyncio.run(agent.serve("127.0.0.1", 0, ready=q.put))


def start_agent_processes(n, speed):
    ctx = mp.get_context("spawn")
    q, procs, ports = ctx.Queue(), [], []
    for _ in range(n):
        p = ctx.Process(target=_serve, args=(speed, q), daemon=True)
        p.start()
        procs.append(p)
    for _ in range(n):
        ports.append(q.get(timeout=20))
    return procs, ports


def stop(procs):
    for p in procs:
        p.terminate()
