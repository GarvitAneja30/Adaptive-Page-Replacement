# Adaptive Page Replacement (BCSE303L, CS3)

Can an adaptive page-replacement policy select an appropriate strategy according to observed memory-reference locality?

This repository contains a trace-driven page-replacement simulator, five reference-pattern generators, an adaptive policy that switches between replacement strategies, and the raw results of the comparison.

**Author:** [Your name, registration number], VIT Vellore (individual submission)

## Contents

| File | Purpose |
|---|---|
| `pager.py` | Simulator: FIFO, LRU, LFU, Clock, Optimal, the adaptive policy, workload generators, main experiment |
| `sweep.py` | Window-size sensitivity experiment (and the LFU-hysteresis comparison) |
| `tables.py` | Prints mean and standard-deviation tables from `results.csv` |
| `results.csv` | Raw results: one row per (memory size, workload, seed, policy) |
| `summary.csv` | Mean and standard deviation per (memory size, workload, policy) |
| `window_sweep.csv` | Raw results of the window-size sweep |
| `hit_ratio.png` | Hit ratio by workload, policy and memory size |
| `window_sweep.png` | Adaptive faults against window size W |

## Requirements

- Python 3.13 (3.9+ should also work)
- `pandas`, `matplotlib` (and `numpy`, installed with them)

```
pip install pandas matplotlib
```

## How to run

```
python pager.py 5      # main experiment, 5 seeds (about 1-2 minutes)
python sweep.py 5      # window-size sweep, 5 seeds (under a minute)
python tables.py       # print the result tables
```

The number after the script name is the number of random seeds per workload (default 5).

`pager.py` first runs a validation check and prints:

```
validation (3 frames): {'fifo': 15, 'lru': 12, 'lfu': 11, 'clock': 14, 'opt': 9}
```

FIFO, LRU and Optimal (15, 12, 9) match the textbook values for the reference string
`7,0,1,2,0,3,0,4,2,3,0,3,2,1,2,0,1,7,0,1` with 3 frames. LFU and Clock were verified by hand-tracing (see the report). The script stops with an assertion error if the three textbook values do not match.

## What is implemented

- **Policies:** FIFO, LRU, LFU (ties broken by least recently used), Clock, and Optimal. Optimal needs the whole future reference string, so it is used only as an offline lower bound and is not available to the adaptive policy.
- **Workloads:** sequential loop, uniform random, drifting locality, Zipf (skewed), and a phased mix of the other four.
- **Adaptive policy:** every W = 500 references, it classifies the last window from four measures (sequentiality, short-range reuse, frequency concentration, hot-set stability) and picks FIFO, LRU, LFU or Clock for the next window. All policies share the same per-page metadata, so a switch keeps every resident page (no flush). Use counts are halved at each switch.
- **Metrics:** page faults, hit ratio, and execution time in milliseconds.

## Experimental configuration

| Frames | Pages | References |
|---|---|---|
| 8 | 32 | 20,000 |
| 16 | 64 | 40,000 |
| 32 | 128 | 80,000 |

- 5 workloads x 5 seeds (0-4) x 6 policies x 3 sizes = 450 runs.
- Every policy replays the identical reference string for a given workload and seed.
- Window size W = 500 (chosen from the sweep over W = 50, 100, 200, 500).
- Classification thresholds are fixed in `pick()` in `pager.py`.

## Reproducibility

Workload generation is seeded, so page-fault counts and hit ratios are exactly reproducible. Execution times depend on the machine and vary slightly between runs. All reported timings were measured on one machine: [CPU, RAM, OS, Python version].

## Headline results (mean faults over 5 seeds, 16 frames)

| Workload | Adaptive | LRU | LFU | Clock | FIFO | Optimal |
|---|---|---|---|---|---|---|
| Locality | 3,296 | 3,296 | 27,824 | 3,848 | 5,932 | 2,405 |
| Zipf | 9,667 | 11,680 | 9,067 | 12,395 | 14,174 | 6,352 |
| Phased | 20,859 | 21,239 | 26,716 | 21,564 | 22,527 | 14,118 |

Sequential and random workloads show no difference between policies (nothing to exploit). Full tables are in `summary.csv`, and the discussion is in the report.

## Individual contribution

[One or two sentences: what you designed, implemented, ran and analysed, and that AI assistance was used for code scaffolding and the results were verified by you, e.g. by the hand-traces and the textbook validation.]
