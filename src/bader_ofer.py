"""Knesset seat allocation: 3.25% threshold + Bader-Ofer (D'Hondt) with surplus-vote agreements.

Implements the procedure in the Knesset Elections Law (sections 81-82):
  1. Lists with at least `threshold_pct` of valid votes qualify.
  2. General quota = qualifying votes / seats; each list gets floor(votes / quota).
  3. Remaining seats go one at a time to the entity with the highest votes / (seats + 1),
     where a surplus agreement whose two lists BOTH qualified counts as one entity.
  4. An agreement's seats are split between its two lists by the same D'Hondt rule.

Works on vote counts or on vote shares (any non-negative numbers).
"""
from __future__ import annotations

import numpy as np


def _dhondt_split(votes: np.ndarray, total: int, start: np.ndarray) -> np.ndarray:
    """Hand out seats until each list's count sums to `total`, starting from `start`."""
    seats = start.astype(int).copy()
    while seats.sum() < total:
        i = int(np.argmax(votes / (seats + 1)))
        seats[i] += 1
    return seats


def allocate(votes, names, agreements=(), seats=120, threshold_pct=3.25) -> dict:
    """Return {name: seats} for a single result vector."""
    votes = np.asarray(votes, dtype=float)
    idx = {n: i for i, n in enumerate(names)}
    total_valid = votes.sum()
    qual = votes >= threshold_pct / 100.0 * total_valid
    out = np.zeros(len(votes), dtype=int)
    if not qual.any():
        return dict(zip(names, out))

    qv = votes[qual]
    qnames = [n for n, q in zip(names, qual) if q]
    quota = qv.sum() / seats
    initial = np.floor(qv / quota).astype(int)

    # Build entities: agreement pairs where both qualified, else single lists.
    qidx = {n: i for i, n in enumerate(qnames)}
    members, used = [], set()
    for a, b in agreements:
        if a in qidx and b in qidx:
            members.append([qidx[a], qidx[b]])
            used.update((a, b))
    for n in qnames:
        if n not in used:
            members.append([qidx[n]])

    ent_votes = np.array([qv[m].sum() for m in members])
    ent_seats = np.array([initial[m].sum() for m in members])
    ent_seats = _dhondt_split(ent_votes, seats, ent_seats)

    final = np.zeros(len(qv), dtype=int)
    for m, s in zip(members, ent_seats):
        if len(m) == 1:
            final[m[0]] = s
        else:
            # Split the agreement's seats between its two lists by D'Hondt from zero.
            final[m] = _dhondt_split(qv[m], int(s), np.zeros(2, dtype=int))
    for n, s in zip(qnames, final):
        out[idx[n]] = s
    return dict(zip(names, out))


def allocate_many(shares: np.ndarray, names, agreements=(), seats=120, threshold_pct=3.25) -> np.ndarray:
    """Vectorised over rows: shares is (n_sims, n_lists). Returns int array of seats."""
    res = np.zeros(shares.shape, dtype=int)
    for r in range(shares.shape[0]):
        a = allocate(shares[r], names, agreements, seats, threshold_pct)
        res[r] = [a[n] for n in names]
    return res
