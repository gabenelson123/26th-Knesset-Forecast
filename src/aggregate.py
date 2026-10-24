"""Poll aggregation: seat projections -> vote shares -> house-effect-adjusted, recency-weighted average."""
from __future__ import annotations

import numpy as np
import pandas as pd


def load_polls(paths, parties, firm_aliases, start_date) -> pd.DataFrame:
    """Read poll CSVs into long format: one row per (poll, party) with seats or pct."""
    frames = [pd.read_csv(p, dtype=str) for p in paths]
    df = pd.concat(frames, ignore_index=True)
    df["date"] = pd.to_datetime(df["date"])
    df = df[df["date"] >= pd.Timestamp(start_date)].copy()
    df["firm"] = df["firm"].replace(firm_aliases)
    df["sample"] = pd.to_numeric(df["sample"], errors="coerce")
    df = df.drop_duplicates(subset=["date", "firm", "publisher"], keep="last").reset_index(drop=True)
    df["poll_id"] = np.arange(len(df))
    return df


def poll_shares(df: pd.DataFrame, parties: list[str], other_pct: float) -> pd.DataFrame:
    """Convert each poll's published numbers to implied vote shares (%).

    Lists below the threshold are published as a percentage ("2.8%") -> used directly.
    Lists with seats: share = seats / 120 * (100 - W), where W is the vote share wasted on
    below-threshold lists in that poll (published %, or the party's window mean when the
    poll does not report it) plus a constant for the long tail of tiny lists.
    Missing cells (party not reported) stay NaN and are simply not used.
    """
    seats = pd.DataFrame(index=df.index, columns=parties, dtype=float)
    pct = pd.DataFrame(index=df.index, columns=parties, dtype=float)
    for p in parties:
        col = df[p].fillna("").astype(str).str.strip()
        is_pct = col.str.endswith("%")
        pct.loc[is_pct, p] = col[is_pct].str.rstrip("%").astype(float)
        num = pd.to_numeric(col.where(~is_pct), errors="coerce")
        seats[p] = num

    # Typical sub-threshold share for each party (used when a 0-seat party has no % reported).
    sub_mean = pct.mean()

    shares = pd.DataFrame(index=df.index, columns=parties, dtype=float)
    for i in df.index:
        passing = seats.loc[i].fillna(0) > 0
        below = [p for p in parties if not passing[p]]
        wasted = 0.0
        for p in below:
            v = pct.at[i, p]
            if np.isnan(v):
                # Not reported. Only impute if the party was clearly running in this poll window.
                v = sub_mean.get(p, np.nan)
                v = 0.0 if np.isnan(v) else v
            else:
                shares.at[i, p] = v
            wasted += v
        wasted += other_pct
        for p in parties:
            if passing[p]:
                shares.at[i, p] = seats.at[i, p] / 120.0 * (100.0 - wasted)
    return shares


def house_effect_average(df: pd.DataFrame, shares: pd.DataFrame, election_date, half_life_days: float):
    """Per party: weighted least squares  share_k = mu + h_firm(k) + e_k.

    Weights = sqrt(sample/500) * 0.5 ** (days_before_last_poll / half_life).
    House effects are identified by constraining their unweighted mean over firms to 0
    (each polling house counts once, however often it polls), so a prolific outlier house
    cannot drag the anchor toward itself.
    Returns (mu: Series of election-day shares, house: DataFrame firm x party, se: Series).
    """
    firms = sorted(df["firm"].unique())
    F = len(firms)
    fidx = df["firm"].map({f: j for j, f in enumerate(firms)}).to_numpy()
    last = df["date"].max()
    age = (last - df["date"]).dt.days.to_numpy()
    n = df["sample"].fillna(df["sample"].median()).to_numpy()
    w_all = np.sqrt(n / 500.0) * 0.5 ** (age / half_life_days)

    mu, se = {}, {}
    house = pd.DataFrame(0.0, index=firms, columns=shares.columns)
    for p in shares.columns:
        y = shares[p].to_numpy(dtype=float)
        ok = ~np.isnan(y)
        if ok.sum() < 3:
            mu[p] = np.nanmean(y) if ok.any() else 0.0
            se[p] = np.nan
            continue
        # Design: intercept + F-1 free house effects, last one = -(sum of others).
        X = np.zeros((ok.sum(), F))
        X[:, 0] = 1.0
        fj = fidx[ok]
        for r, j in enumerate(fj):
            if j < F - 1:
                X[r, 1 + j] = 1.0
            else:
                X[r, 1:] = -1.0
        # Firms with no data for this party: their columns are all-zero except via the
        # constraint row; use lstsq which handles rank deficiency.
        w = w_all[ok]
        W = np.sqrt(w)
        beta, *_ = np.linalg.lstsq(X * W[:, None], y[ok] * W, rcond=None)
        resid = y[ok] - X @ beta
        dof = max(ok.sum() - F, 1)
        s2 = np.sum(w * resid ** 2) / np.sum(w) * ok.sum() / dof
        cov = s2 * np.linalg.pinv((X * w[:, None]).T @ X)
        mu[p] = beta[0]
        se[p] = float(np.sqrt(cov[0, 0]))
        h = np.append(beta[1:], -beta[1:].sum())
        house[p] = h
    return pd.Series(mu), house, pd.Series(se)
