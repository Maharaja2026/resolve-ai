"""Reciprocal Rank Fusion helper."""

from __future__ import annotations

from typing import Dict, List, Sequence, TypeVar

T = TypeVar("T")


def reciprocal_rank_fusion(
    ranked_lists: Sequence[Sequence[T]],
    *,
    key_fn,
    k: int = 60,
    weights: Sequence[float] | None = None,
) -> List[tuple[T, float]]:
    if not ranked_lists:
        return []
    weights = weights or [1.0] * len(ranked_lists)
    scores: Dict[str, float] = {}
    items: Dict[str, T] = {}
    for list_index, ranked in enumerate(ranked_lists):
        weight = float(weights[list_index])
        for rank, item in enumerate(ranked, start=1):
            key = str(key_fn(item))
            items[key] = item
            scores[key] = scores.get(key, 0.0) + weight * (1.0 / (k + rank))
    return [(items[key], score) for key, score in sorted(scores.items(), key=lambda p: p[1], reverse=True)]
