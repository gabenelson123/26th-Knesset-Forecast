"""Knesset 26 forecast — run:  python forecast.py

Pipeline: polls -> implied vote shares -> house-effect-adjusted recency-weighted average
-> Monte Carlo of election-day shares -> Bader-Ofer seat allocation with surplus agreements
-> per-party L1-optimal (median) seat forecast that sums to 120, plus a turnout forecast.
Outputs land in output/.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.aggregate import house_effect_average, load_polls, poll_shares
from src.simulate import l1_point_forecast, simulate
from src.turnout import predict_turnout

ROOT = Path(__file__).parent
DATA, OUT = ROOT / "data", ROOT / "output"


def main(exclude_firms: tuple[str, ...] = (), tag: str = "") -> pd.DataFrame:
    cfg = json.loads((DATA / "config.json").read_text())
    parties = list(cfg["parties"].keys())
    modelled = [p for p in parties if p != "blue_white"]  # withdrew 19 Oct; fixed small share
    blocs = {p: v["bloc"] for p, v in cfg["parties"].items()}

    polls = load_polls([DATA / "polls_snapshot.csv", DATA / "polls_manual.csv"], parties,
                       cfg["firm_aliases"], cfg["poll_window_start"])
    if exclude_firms:
        polls = polls[~polls["firm"].isin(exclude_firms)].reset_index(drop=True)
    shares = poll_shares(polls, parties, cfg["other_lists_pct"])
    mu, house, se = house_effect_average(polls, shares[modelled], cfg["election_date"],
                                         cfg["aggregation"]["half_life_days"])

    # Blue and White withdrew on 19 Oct: residual share (ballots already printed, some
    # confused/loyal voters), never near the threshold.
    mu_all = mu.to_dict()
    mu_all["blue_white"] = cfg["simulation"]["blue_white_share_pct"]
    se_all = se.to_dict()
    se_all["blue_white"] = 0.0

    names, sim_shares, sim_seats = simulate(
        mu_all, se_all, blocs, [tuple(a) for a in cfg["surplus_agreements"]], cfg["simulation"],
        cfg["other_lists_pct"], cfg["seats"], cfg["threshold_pct"])

    med, pt, el1_med, el1_pt = l1_point_forecast(sim_seats, cfg["seats"])
    q = np.percentile(sim_seats, [5, 25, 75, 95], axis=0)
    p_pass = (sim_seats > 0).mean(axis=0)

    table = pd.DataFrame({
        "party": [cfg["parties"][n]["name"] for n in names],
        "key": names,
        "poll_avg_share_pct": [round(mu_all[n], 2) for n in names],
        "mean_seats": sim_seats.mean(axis=0).round(2),
        "p5": q[0].astype(int), "p25": q[1].astype(int), "p75": q[2].astype(int), "p95": q[3].astype(int),
        "p_pass_threshold": p_pass.round(3),
        "median_seats": med,
        "FORECAST": pt,
    }).sort_values("FORECAST", ascending=False)

    turnout, t_sigma, _ = predict_turnout(DATA / "turnout_history.csv", joint_list_united=1)

    if not tag:
        OUT.mkdir(exist_ok=True)
        table.to_csv(OUT / "forecast.csv", index=False)
        house.round(2).to_csv(OUT / "house_effects_pct.csv")
        np.save(OUT / "sim_seats.npy", sim_seats)
        right = [n for n in names if blocs[n] == "right"]
        bloc_right = sim_seats[:, [names.index(n) for n in right]].sum(axis=1)
        summary = {
            "n_polls": int(len(polls)),
            "poll_dates": [str(polls["date"].min().date()), str(polls["date"].max().date())],
            "firms": sorted(polls["firm"].unique().tolist()),
            "expected_abs_error_median_forecast": round(float(el1_med), 2),
            "expected_abs_error_final_forecast": round(float(el1_pt), 2),
            "forecast_sum": int(pt.sum()),
            "turnout_forecast_pct": round(turnout, 1),
            "turnout_resid_sd": round(t_sigma, 2),
            "p_right_bloc_61": round(float((bloc_right >= 61).mean()), 3),
        }
        (OUT / "summary.json").write_text(json.dumps(summary, indent=2))
        print(table.to_string(index=False))
        print(json.dumps(summary, indent=2))
    return table


if __name__ == "__main__":
    main()
