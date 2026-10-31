import pandas as pd
df = pd.read_csv("results.csv")
for metric in ["faults", "hit_ratio", "time_ms"]:
    t = df.groupby(["frames", "workload", "policy"])[metric].agg(["mean", "std"]).round(4)
    print("\n==", metric, "==")
    print(t.unstack("policy").to_string())