"""Window-size sweep (and LFU-hysteresis comparison) for the adaptive policy."""
import random, sys
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pager import gen, simulate, SIZES

WINDOWS = [50, 100, 200, 500]
WORKLOADS = ["locality", "zipf", "phased"]
HYST = [1, 2]            # 1 = switch to LFU immediately, 2 = need two windows in a row


def sweep(reps=5, out="window_sweep.csv"):
    rows = []
    for k, P, n in SIZES:
        for w in WORKLOADS:
            for seed in range(reps):
                refs = gen(w, n, P, k, random.Random(seed))
                base = {p: simulate(refs, k, p)[0] for p in ("lru", "lfu")}
                for W in WINDOWS:
                    for h in HYST:
                        f = simulate(refs, k, "adaptive", W, h)[0]
                        rows.append(dict(frames=k, workload=w, seed=seed, W=W, hyst=h, faults=f, lru=base["lru"], lfu=base["lfu"]))
    df = pd.DataFrame(rows)
    df.to_csv(out, index=False)
    return df


def plot(df):
    fig, ax = plt.subplots(len(WORKLOADS), len(SIZES), figsize=(14, 9), sharex=True)
    for i, w in enumerate(WORKLOADS):
        for j, (k, _, _) in enumerate(SIZES):
            d = df[(df.workload == w) & (df.frames == k)]
            a = ax[i][j]
            for h in HYST:
                m = d[d.hyst == h].groupby("W").faults.mean()
                a.plot(m.index, m.values, marker="o", label=f"adaptive (hyst={h})")
            a.axhline(d.lru.mean(), ls="--", c="gray", label="LRU")
            if w == "zipf":  # LFU is far off the scale elsewhere and flattens the panel
                a.axhline(d.lfu.mean(), ls=":", c="k", label="LFU")
            a.set_xscale("log")
            a.set_xticks(WINDOWS)
            a.set_xticklabels(WINDOWS)
            a.minorticks_off()
            a.set_title(f"{w}, {k} frames")
            if j == 0: a.set_ylabel("page faults")
            if i == len(WORKLOADS) - 1: a.set_xlabel("window size W")
    ax[0][0].legend(fontsize=7)
    plt.tight_layout()
    plt.savefig("window_sweep.png", dpi=150)


if __name__ == "__main__":
    df = sweep(int(sys.argv[1]) if len(sys.argv) > 1 else 5)
    plot(df)
    t = df.groupby(["workload", "frames", "W", "hyst"]).faults.mean().unstack().round(0)
    t["lru"] = df.groupby(["workload", "frames", "W"]).lru.mean().round(0)
    t["lfu"] = df.groupby(["workload", "frames", "W"]).lfu.mean().round(0)
    print(t.to_string())