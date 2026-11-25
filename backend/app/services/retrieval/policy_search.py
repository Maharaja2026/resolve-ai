"""Hybrid policy retrieval with RRF."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.core.config import get_settings
from app.core.supabase_client import get_supabase_client
from app.services.embeddings.fastembed_service import get_embedding_service
from app.services.retrieval.rrf import reciprocal_rank_fusion


def search_policies(query: str, category: Optional[str] = None, top_k: Optional[int] = None) -> List[Dict[str, Any]]:
    settings = get_settings()
    final_k = top_k or settings.retrieval_top_k
    candidate_k = max(settings.retrieval_candidate_k, final_k)
    client = get_supabase_client()
    embedding = get_embedding_service().embed_query(query)

    semantic = (
        client.rpc(
            "resolveai_match_policy_chunks",
            {
                "p_query_embedding": embedding,
                "p_match_count": candidate_k,
                "p_category": category,
            },
        ).execute().data
        or []
    )
    keyword = (
        client.rpc(
            "resolveai_keyword_policy_chunks",
            {
                "p_query": query,
                "p_match_count": candidate_k,
                "p_category": category,
            },
        ).execute().data
        or []
    )

    fused = reciprocal_rank_fusion(
        [semantic, keyword],
        key_fn=lambda row: row["id"],
        k=settings.rrf_k,
    )
    results = []
    for row, score in fused[:final_k]:
        results.append(
            {
                "chunk_id": row["id"],
                "document_id": row["document_id"],
                "title": row.get("document_title"),
                "category": row.get("category"),
                "content": row.get("content"),
                "chunk_index": row.get("chunk_index"),
                "score": float(score),
                "metadata": row.get("metadata") or {},
            }
        )
    return results
