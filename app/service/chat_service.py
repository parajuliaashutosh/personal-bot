"""
Configuration-driven Chat Service for RAG-based chatbot.
Production-grade implementation with multi-source retrieval.
"""

from app.memory.vector import VectorStore
from app.config import get_llm
from app.config.intent_config import (
    get_intent_config,
    get_source_display_name,
    INTENT_CONFIGS,
)
from app.service.intent_classifier.intent_classifier import IntentClassifier


class ChatService:
    """
    Chat service using configuration-driven intent routing.
    Replaces hardcoded if/else with extensible config.
    """

    def __init__(self):
        self.memory = VectorStore()
        self.intent = IntentClassifier()
        self.llm = get_llm()

    def get_enhanced_context(self, query: str, k: int = 5) -> str:
        """
        Configuration-driven context retrieval.
        Searches multiple sources based on intent config.
        """
        intent = self.intent.classify_query_intent(query)
        config = get_intent_config(intent)

        print(f"🎯 Detected intent: {intent}")

        # If no specific sources, do general search
        if config["sources"] is None:
            return self.memory.search(query, k=k)

        # Search each configured source
        contexts = []
        sources = config["sources"]
        k_values = config["k_per_source"]

        # Ensure we have k values for all sources
        if len(k_values) < len(sources):
            k_values = k_values + [2] * (len(sources) - len(k_values))

        for source, source_k in zip(sources, k_values):
            result = self.memory.search(
                query,
                k=source_k,
                filter_metadata={"type": source}
            )

            if result and result.strip():
                display_name = get_source_display_name(source)
                contexts.append(f"## {display_name}\n{result}")

        combined = "\n\n".join(contexts)

        # Fallback if nothing found
        if not combined or len(combined.strip()) < 50:
            print(f"⚠️ Filtered search empty, falling back to general search")
            return self.memory.search(query, k=k)

        return combined

    def build_system_prompt(self, context: str, query: str) -> str:
        """Build system prompt from configuration."""
        intent = self.intent.classify_query_intent(query)
        config = get_intent_config(intent)

        instruction = config["instruction"]
        fallback = config["fallback_message"]

        return f"""You are Aashutosh's personal assistant AI.
            Your job is to represent Aashutosh professionally and accurately.

            {instruction}

            **Available Information:**
            {context}

            **Important Rules:**
            1. Answer ONLY based on the information provided above
            2. If the answer is not explicitly listed in the available information, say: "{fallback}" instead of guessing.
            3. Be concise and natural - avoid bullet points unless asked
            4. Speak in first person as if you ARE Aashutosh (use 'I' not 'he')
            5. Be professional but conversational
            6. When discussing skills, always reference actual projects/experience using that technology
            """

    def chat(self, query: str) -> str:
        """Main chat function to get response based on query"""
        context = self.get_enhanced_context(query)
        system_prompt = self.build_system_prompt(context, query)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query},
        ]

        reply = self.llm.chat(messages)
        return reply

    def stream_chat(self, query: str):
        """Stream Chat function to get response based on query"""
        context = self.get_enhanced_context(query)
        system_prompt = self.build_system_prompt(context, query)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query},
        ]

        async def generator():
            async for token in self.llm.stream(messages):
                yield f"data: {token}\n\n"

        return generator()

    def get_available_intents(self) -> list[str]:
        """Return list of available intent types for debugging"""
        return list(INTENT_CONFIGS.keys())

    def debug_search(self, query: str, k: int = 5) -> dict:
        """
        Debug method to see what's being retrieved.
        Returns detailed info about search results.
        """
        intent = self.intent.classify_query_intent(query)
        config = get_intent_config(intent)

        results = {
            "query": query,
            "detected_intent": intent,
            "config": {
                "sources": config["sources"],
                "k_per_source": config["k_per_source"],
            },
            "retrieved_chunks": [],
        }

        if config["sources"]:
            for source in config["sources"]:
                chunks = self.memory.search_with_scores(
                    query, k=3, filter_metadata={"type": source}
                )
                for doc, score, meta in chunks:
                    results["retrieved_chunks"].append({
                        "source": source,
                        "score": round(score, 4),
                        "metadata": meta,
                        "preview": doc[:200] + "..." if len(doc) > 200 else doc,
                    })
        else:
            chunks = self.memory.search_with_scores(query, k=k)
            for doc, score, meta in chunks:
                results["retrieved_chunks"].append({
                    "source": "general",
                    "score": round(score, 4),
                    "metadata": meta,
                    "preview": doc[:200] + "..." if len(doc) > 200 else doc,
                })

        return results
