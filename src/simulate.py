"""Monte Carlo over election-day vote shares, then seats via Bader-Ofer.

Error model (all in percentage points of the valid vote):
  * party-level polling error   e_p ~ N(0, (coef * sqrt(share_p))^2 + se_p^2)
      coef = 0.25 gives ~1.1 pts (~1.4 seats) for an 18% party and ~0.45 pts for a 3% party,
      in line with typical final-poll-average errors in recent Israeli elections.
  * bloc swing                  z ~ N(0, bloc_sd^2) moved from the Jewish opposition parties to
      the right-wing parties (proportionally to size); captures correlated polling misses.
  * Arab turnout shock          Joint List and Ra'am multiplied by exp(N(0, arab_sd^2)), common to both.
Shares are clipped at 0 and renormalised to 100 before allocation.
"""
from __future__ import annotations

import numpy as np

from .bader_ofer import allocate_many


def simulate(mu: dict, se: dict, blocs: dict, agreements, cfg_sim: dict, other_pct: float,
             seats=120, threshold_pct=3.25):
    rng = np.random.default_rng(cfg_sim["seed"])
    names = list(mu.keys())
    m = np.array([mu[p] for p in names], dtype=float)
    s = np.array([0.0 if np.isnan(se.get(p, np.nan)) else se[p] for p in names])
    N = cfg_sim["n_sims"]

    sd = np.sqrt((cfg_sim["party_sd_coef"] * np.sqrt(np.clip(m, 0.05, None))) ** 2 + s ** 2)
    draws = m + rng.standard_normal((N, len(names))) * sd

    right = np.array([blocs[p] == "right" for p in names])
    opp = np.array([blocs[p] == "opp" for p in names])
    arab = np.array([blocs[p] == "arab" for p in names])
    z = rng.standard_normal(N) * cfg_sim["bloc_shock_sd_pts"]
    draws[:, right] += z[:, None] * (m[right] / m[right].sum())
    draws[:, opp] -= z[:, None] * (m[opp] / m[opp].sum())
    draws[:, arab] *= np.exp(rng.standard_normal(N) * cfg_sim["arab_turnout_log_sd"])[:, None]

    draws = np.clip(draws, 0.0, None)
    # Append the long tail of tiny lists as one never-qualifying "other" column.
    other = np.full((N, 1), other_pct)
    full = np.hstack([draws, other])
    full = full / full.sum(axis=1, keepdims=True) * 100.0
    seats_sim = allocate_many(full, names + ["_other"], agreements, seats, threshold_pct)[:, :-1]
    return names, full[:, :-1], seats_sim


def l1_point_forecast(seats_sim: np.ndarray, total=120):
    """Per-party median minimises E|error| party by party (the competition's loss).

    If the medians don't sum to `total`, greedily apply the +/-1 moves with the smallest
    increase in expected absolute error until they do. Returns (unconstrained, constrained,
    expected_l1_unconstrained, expected_l1_constrained).
    """
    med = np.median(seats_sim, axis=0).round().astype(int)
    # For an integer m: E|X-m| changes by P(X<=m) - P(X>m) when m -> m+1, and by
    # P(X>=m) - P(X<m) when m -> m-1.
    def el1(pt):
        return np.abs(seats_sim - pt).mean(axis=0).sum()

    pt = med.copy()
    while pt.sum() != total:
        best, best_cost = None, np.inf
        step = 1 if pt.sum() < total else -1
        for j in range(len(pt)):
            cand = pt[j] + step
            if cand < 0:
                continue
            delta = (np.abs(seats_sim[:, j] - cand).mean() - np.abs(seats_sim[:, j] - pt[j]).mean())
            if delta < best_cost:
                best, best_cost = j, delta
        pt[best] += step
    return med, pt, el1(med), el1(pt)
