from app.memory.vector import VectorStore
from app.config import get_llm
from app.service.intent_classifier.intent_classifier import IntentClassifier


class ChatService:
    def __init__(self):
        self.memory = VectorStore()
        self.intent = IntentClassifier()
        self.llm = get_llm()

    def get_enhanced_context(self, query: str, k: int = 5) -> str:
        """Get context with intent-based filtering using the internal memory"""
        intent = self.intent.classify_query_intent(query)

        print(f"🎯 Detected intent: {intent}")

        # For skills queries, search across multiple sources
        # to find projects/experience using that technology
        if intent == "skills":
            # First get skills info
            skills_context = self.memory.search(
                query,
                k=3,
                filter_metadata={"type": "skills"}
            )

            # Then search professional experience for practical usage
            experience_context = self.memory.search(
                query,
                k=2,
                filter_metadata={"type": "professional_experience"}
            )

            # Then search personal projects for practical usage
            projects_context = self.memory.search(
                query,
                k=2,
                filter_metadata={"type": "personal_projects"}
            )

            # Combine all contexts
            all_contexts = []
            if skills_context and skills_context.strip():
                all_contexts.append(f"## Technical Skills\n{skills_context}")
            if experience_context and experience_context.strip():
                all_contexts.append(
                    f"## Professional Experience Using This Technology\n{experience_context}")
            if projects_context and projects_context.strip():
                all_contexts.append(
                    f"## Personal Projects Using This Technology\n{projects_context}")

            context = "\n\n".join(all_contexts) if all_contexts else ""

            # If still nothing, do general search
            if not context or len(context.strip()) < 50:
                print(f"⚠️  Skills search empty, falling back to general search")
                context = self.memory.search(query, k=k)

            return context

        # Try filtered search first for other intents
        if intent != "general":
            context = self.memory.search(
                query,
                k=k,
                filter_metadata={"type": intent}
            )

            # If filtered search returns nothing, fall back to general search
            if not context or len(context.strip()) < 50:
                print(f"⚠️  Filtered search empty, falling back to general search")
                context = self.memory.search(query, k=k)
        else:
            context = self.memory.search(query, k=k)

        return context

    def build_system_prompt(self, context: str, query: str) -> str:
        """Build a better system prompt based on query type"""
        intent = self.intent.classify_query_intent(query)

        base_prompt = (
            "You are Aashutosh's personal assistant AI. "
            "Your job is to represent Aashutosh professionally and accurately.\n\n"
        )

        # Intent-specific instructions
        if intent == "professional_experience":
            specific_instruction = (
                "The user is asking about Aashutosh's professional work experience. "
                "Focus on his roles at companies (HamroPatro Inc., Information Care Pvt. Ltd.), "
                "his responsibilities, achievements, and technologies used in professional settings. "
                "Do NOT mention personal/side projects unless specifically asked.\n\n"
            )
        elif intent == "personal_projects":
            specific_instruction = (
                "The user is asking about Aashutosh's personal projects. "
                "Focus on side projects like FastAPI Chatbot, International Money Order, Charitable, Discuss Forum, etc. "
                "Include GitHub links and technologies used.\n\n"
            )
        elif intent == "education":
            specific_instruction = (
                "The user is asking about Aashutosh's educational background. "
                "Provide details about his schools, college, degrees, and grades.\n\n"
            )
        elif intent == "skills":
            specific_instruction = (
                "The user is asking about Aashutosh's technical skills. "
                "When explaining skills in a specific technology:\n"
                "1. First mention the proficiency level if available\n"
                "2. Then describe projects built using that technology (from professional experience OR personal projects)\n"
                "3. Include specific features/systems built with that technology\n"
                "Example: 'I have experience with Python through my FastAPI Personal Chatbot project where I built RAG-based retrieval...'\n\n"
            )
        else:
            specific_instruction = ""

        return (
            f"{base_prompt}"
            f"{specific_instruction}"
            f"**Available Information:**\n{context}\n\n"
            f"**Important Rules:**\n"
            f"1. Answer ONLY based on the information provided above\n"
            f"2. If the answer is not in the information, say: 'I don't have that information'\n"
            f"3. Be concise and natural - avoid bullet points unless asked\n"
            f"4. Speak in first person as if you ARE Aashutosh (use 'I' not 'he')\n"
            f"5. Be professional but conversational\n"
        )

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

    def stream_chat(self, query: str) -> str:
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
