from sentence_transformers import SentenceTransformer
import numpy as np


class IntentClassifier:
    def __init__(self):
        self.model = SentenceTransformer('all-MiniLM-L6-v2')

        # Define intent templates with multiple examples
        self.intent_templates = {
            "professional_experience": [
                "Tell me about your work experience",
                "What companies have you worked for?",
                "Describe your professional background",
                "What was your role at your last job?",
            ],
            "personal_projects": [
                "What projects have you built?",
                "Show me your personal work",
                "What have you created on your own?",
                "Tell me about your GitHub projects",
            ],
            "education": [
                "Where did you study?",
                "What's your educational background?",
                "What degree do you have?",
                "Tell me about your university",
            ],
            "skills": [
                "What technologies do you know?",
                "What programming languages can you use?",
                "What's your tech stack?",
                "What are your technical skills?",
            ]
        }

        # Pre-compute embeddings for all templates
        self.intent_embeddings = {}
        for intent, templates in self.intent_templates.items():
            embeddings = self.model.encode(templates)
            # Average embeddings for each intent
            self.intent_embeddings[intent] = np.mean(embeddings, axis=0)

    def classify_query_intent(self, query: str) -> str:
        query_embedding = self.model.encode([query])[0]

        # Calculate cosine similarity with each intent
        similarities = {}
        for intent, intent_emb in self.intent_embeddings.items():
            similarity = np.dot(query_embedding, intent_emb) / (
                np.linalg.norm(query_embedding) * np.linalg.norm(intent_emb)
            )
            similarities[intent] = similarity

        # Return intent with highest similarity (if above threshold)
        best_intent = max(similarities, key=similarities.get)
        if similarities[best_intent] > 0.5:  # Threshold
            return best_intent
        return "general"
