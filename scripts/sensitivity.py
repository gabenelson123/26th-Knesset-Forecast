"""Re-run the forecast under alternative assumptions and compare the seat forecasts.

python -m scripts.sensitivity
"""
import json
from pathlib import Path

import pandas as pd

import forecast

CFG = Path(forecast.DATA / "config.json")


def run(label, mutate=None, exclude=()):
    base = CFG.read_text()
    try:
        if mutate:
            cfg = json.loads(base)
            mutate(cfg)
            CFG.write_text(json.dumps(cfg, indent=2))
        t = forecast.main(exclude_firms=exclude, tag=label)
    finally:
        CFG.write_text(base)
    return t.set_index("key")["FORECAST"].rename(label)


def main():
    def small(c):
        c["simulation"]["n_sims"] = 6000

    cols = [
        run("baseline", small),
        run("no_channel14", small, exclude=("SF+ND",)),
        run("no_ch14_no_i24", small, exclude=("SF+ND", "Direct Polls")),
        run("half_life_5d", lambda c: (small(c), c["aggregation"].__setitem__("half_life_days", 5))),
        run("half_life_20d", lambda c: (small(c), c["aggregation"].__setitem__("half_life_days", 20))),
        run("errors_x1.5", lambda c: (small(c), c["simulation"].__setitem__("party_sd_coef", 0.375))),
    ]
    df = pd.concat(cols, axis=1)
    out = forecast.OUT / "sensitivity.csv"
    df.to_csv(out)
    print(df.to_string())


if __name__ == "__main__":
    main()
