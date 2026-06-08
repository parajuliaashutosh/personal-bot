from __future__ import annotations

import asyncio
from typing import Any, Callable

from asyncpg import Pool

from retrieval.memory.chat_history import fetch_last_3
from retrieval.pipeline.context_builder import build_context
from retrieval.pipeline.merger import merge
from retrieval.pipeline.prompt_builder import build_prompt
from retrieval.pipeline.query_expansion import expand_query
from retrieval.pipeline.query_understanding import understand_query
from retrieval.pipeline.ranker import rank
from retrieval.pipeline.reranker import rerank
from retrieval.pipeline.searchers.keyword_search import keyword_search
from retrieval.pipeline.searchers.memory_search import memory_search
from retrieval.pipeline.searchers.vector_search import vector_search
from shared.config.settings import settings


async def build_chat_pipeline(
    clean_query: str,
    session_id: str,
    pool: Pool,
    generate_fn: Callable,
    embed_fn: Callable,
    persona_text: str,
) -> tuple[list[dict[str, Any]], list[tuple[str, str]], str]:
    """Run the full retrieval pipeline. Returns (reranked_chunks, history, prompt)."""

    # Step 1: Understand query — extract intent, entities, keywords
    query_ctx, _ = await understand_query(clean_query)

    # Step 2: Expand query — generate semantic variations for broader recall
    variations = await expand_query(clean_query, query_ctx, generate_fn)

    # Step 3: Embed original + first variation for multi-vector search
    all_queries = [clean_query] + variations
    embeddings = await embed_fn(all_queries[:2])

    # Step 4: Search — vector, keyword, and session memory in parallel
    vector_batches = await asyncio.gather(
        *[vector_search(emb, 20, pool) for emb in embeddings]
    )
    vector_results = [chunk for batch in vector_batches for chunk in batch]

    kw_results, mem_results = await asyncio.gather(
        keyword_search(query_ctx["keywords"], 20, pool),
        memory_search(session_id, pool),
    )

    # Step 5: Merge duplicates, rank by relevance, then rerank with LLM
    candidates = merge(vector_results + kw_results + mem_results)
    ranked = rank(candidates, query_ctx)
    reranked = await rerank(clean_query, ranked[:20], generate_fn)

    # Step 6: Build context string, fetch history, assemble final prompt
    context_str = build_context(reranked, settings.context_token_limit)
    history = await fetch_last_3(session_id, pool)
    prompt = build_prompt(clean_query, context_str, persona_text)

    return reranked, history, prompt
