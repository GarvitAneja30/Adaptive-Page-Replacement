"""Adaptive page replacement: FIFO, LRU, LFU, Clock, Optimal + adaptive selector."""
import random, time, csv, sys
from collections import Counter
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

INF = float("inf")
POLICIES = ["fifo", "lru", "lfu", "clock", "opt"]
KEY = {"fifo": lambda e: e[0], "lru": lambda e: e[1],
       "lfu": lambda e: (e[2], e[1]), "opt": lambda e: -e[4]}


def next_uses(refs):
    nxt, seen = [INF] * len(refs), {}
    for i in range(len(refs) - 1, -1, -1):
        nxt[i] = seen.get(refs[i], INF)
        seen[refs[i]] = i
    return nxt


class Memory:
    """Shared frame state: every policy reads the same per-page metadata,
    so switching policy mid-run carries all resident pages over.
    meta = [load_time, last_used, freq, ref_bit, next_use]"""

    def __init__(s, k):
        s.k, s.meta, s.ring, s.hand = k, {}, [], 0

    def victim(s, pol):
        if pol == "clock":
            while True:
                e = s.meta[s.ring[s.hand]]
                if e[3]:
                    e[3] = 0
                    s.hand = (s.hand + 1) % s.k
                else:
                    return s.hand
        return min(range(s.k), key=lambda i: KEY[pol](s.meta[s.ring[i]]))

    def access(s, t, p, nu, pol):
        """Returns 1 on page fault, 0 on hit."""
        e = s.meta.get(p)
        if e:
            e[1], e[2], e[3], e[4] = t, e[2] + 1, 1, nu
            return 0
        new = [t, t, 1, 1, nu]
        if len(s.ring) < s.k:
            s.ring.append(p)
        else:
            i = s.victim(pol)
            del s.meta[s.ring[i]]
            s.ring[i] = p
            if pol == "clock":
                s.hand = (i + 1) % s.k
        s.meta[p] = new
        return 1


def pick(win, k, prev):
    """Classify the last window; return (policy, hot_set)."""
    n, last, short, seq = len(win), {}, 0, 0
    for j, p in enumerate(win):
        if p in last and j - last[p] <= k:
            short += 1
        last[p] = j
        if j and p == win[j - 1] + 1:
            seq += 1
    c = Counter(win)
    hot = {p for p, _ in c.most_common(k)}
    share = sum(c[p] for p in hot) / n
    stable = len(hot & prev) / k > 0.7          # hot set unchanged since last window
    if seq / n > 0.5:
        pol = "fifo"                            # sequential / looping scan
    elif share > 0.6 and stable:
        pol = "lfu"                             # skewed, stable frequencies
    elif short / n > 0.6:
        pol = "lru"                             # strong, drifting temporal locality
    else:
        pol = "clock"                           # weak locality: cheap LRU approximation
    return pol, hot


def simulate(refs, k, pol, W=500, hyst=1):
    nxt, mem = next_uses(refs), Memory(k)
    cur, faults, log, prev, streak = ("lru" if pol == "adaptive" else pol), 0, [], set(), 0
    t0 = time.perf_counter()
    for t, p in enumerate(refs):
        if pol == "adaptive" and t and t % W == 0:
            new, prev = pick(refs[t - W:t], k, prev)
            streak = streak + 1 if new == "lfu" else 0
            if new != "lfu" or streak >= hyst:  # LFU needs `hyst` windows in a row
                cur = new
            log.append(cur)
            for e in mem.meta.values():         # age frequencies so stale counts fade
                e[2] = (e[2] + 1) // 2
        faults += mem.access(t, p, nxt[t], cur)
    ms = (time.perf_counter() - t0) * 1000
    return faults, 1 - faults / len(refs), ms, log


# ---------- workload generators ----------
def gen(kind, n, P, k, rng):
    if kind == "sequential":
        return [i % P for i in range(n)]
    if kind == "random":
        return [rng.randrange(P) for _ in range(n)]
    if kind == "locality":  # drifting working set of 3/4 of the frames
        ws, off, out = max(2, k * 3 // 4), 0, []
        for i in range(n):
            if i % 25 == 0:
                off += 1
            out.append((off + rng.randrange(ws)) % P if rng.random() < .95 else rng.randrange(P))
        return out
    if kind == "zipf":
        w = [1 / (i + 1) ** 1.2 for i in range(P)]
        return rng.choices(range(P), w, k=n)
    if kind == "phased":
        kinds, seg = ["locality", "sequential", "zipf", "random"], n // 8
        out = []
        for i in range(8):
            out += gen(kinds[i % 4], seg, P, k, rng)
        return out
    raise ValueError(kind)


WORKLOADS = ["sequential", "random", "locality", "zipf", "phased"]
SIZES = [(8, 32, 20000), (16, 64, 40000), (32, 128, 80000)]  # (frames, pages, refs)


def validate():
    r = [7, 0, 1, 2, 0, 3, 0, 4, 2, 3, 0, 3, 2, 1, 2, 0, 1, 7, 0, 1]
    got = {p: simulate(r, 3, p)[0] for p in POLICIES}
    print("validation (3 frames):", got)
    assert got["fifo"] == 15 and got["lru"] == 12 and got["opt"] == 9


def experiment(reps=5, out="results.csv"):
    rows = []
    for k, P, n in SIZES:
        for w in WORKLOADS:
            for seed in range(reps):
                refs = gen(w, n, P, k, random.Random(seed))
                for pol in POLICIES + ["adaptive"]:
                    f, h, ms, _ = simulate(refs, k, pol)
                    rows.append(dict(frames=k, pages=P, refs=n, workload=w, seed=seed,
                                     policy=pol, faults=f, hit_ratio=h, time_ms=ms))
    df = pd.DataFrame(rows)
    df.to_csv(out, index=False)
    return df


def report(df):
    g = df.groupby(["frames", "workload", "policy"])[["faults", "hit_ratio", "time_ms"]]
    summ = g.agg(["mean", "std"]).round(4)
    summ.to_csv("summary.csv")
    fig, ax = plt.subplots(1, len(SIZES), figsize=(6 * len(SIZES), 4), sharey=True)
    for a, (k, _, _) in zip(ax, SIZES):
        d = df[df.frames == k].groupby(["workload", "policy"]).hit_ratio.mean().unstack()
        d[POLICIES + ["adaptive"]].loc[WORKLOADS].plot.bar(ax=a, title=f"{k} frames", rot=30)
        a.set_ylabel("hit ratio")
    plt.tight_layout()
    plt.savefig("hit_ratio.png", dpi=150)


if __name__ == "__main__":
    validate()
    df = experiment(reps=int(sys.argv[1]) if len(sys.argv) > 1 else 5)
    report(df)
    print(df[df.frames == 16].groupby(["workload", "policy"]).faults.mean().unstack().round(0))