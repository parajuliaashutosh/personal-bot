"""
Adaptive intent configuration for RAG retrieval.
Auto-configures based on available data types in the vector store.
"""

from typing import TypedDict, Optional


class IntentConfig(TypedDict):
    """Configuration for each intent type"""
    sources: Optional[list[str]]  # None means no filtering (general search)
    k_per_source: list[int]       # Number of results per source
    instruction: str              # LLM instruction for this intent
    fallback_message: str         # Graceful fallback when info not found


def get_dynamic_intent_config():
    """
    Generate intent configuration based on what data types exist.
    Adapts automatically to user's data structure.
    """
    from app.memory.vector import VectorStore

    # Check what data types exist in the vector store
    existing_types = set()
    try:
        store = VectorStore()
        # Get sample of metadata to see what types exist
        all_docs = store.collection.get(limit=100)

        if all_docs and all_docs.get('metadatas'):
            for metadata in all_docs['metadatas']:
                if isinstance(metadata, dict) and 'type' in metadata:
                    existing_types.add(metadata['type'])

        print(f"🔍 Found data types: {sorted(existing_types)}")
    except Exception as e:
        print(f"⚠️ Could not check existing data types: {e}")
        # Fallback to common types
        existing_types = {'skills', 'professional_experience',
                          'personal_projects', 'education', 'general'}

    # Generate config based on existing types
    config = {}

    # Skills configuration - searches across multiple sources
    if any(t in existing_types for t in ['skills', 'professional_experience', 'personal_projects']):
        available_sources = []
        k_values = []

        if 'skills' in existing_types:
            available_sources.append('skills')
            k_values.append(3)
        if 'professional_experience' in existing_types:
            available_sources.append('professional_experience')
            k_values.append(2)
        if 'personal_projects' in existing_types:
            available_sources.append('personal_projects')
            k_values.append(2)

        config['skills'] = {
            "sources": available_sources,
            "k_per_source": k_values,
            "instruction": (
                "The user is asking about technical skills and expertise. "
                "When explaining skills in a specific technology:\n"
                "1. Mention the proficiency level if available\n"
                "2. Reference actual projects where this technology was used\n"
                "3. Describe specific features/systems built with it\n"
                "Format: 'I have [duration] of experience with [technology], primarily through "
                "[specific projects/work] where I [specific accomplishments]...'"
            ),
            "fallback_message": (
                "I don't have specific information about that technology, "
                "but I can tell you about my main technical skills and the projects I've worked on."
            ),
        }

    # Professional experience configuration
    if 'professional_experience' in existing_types:
        config['professional_experience'] = {
            "sources": ['professional_experience'],
            "k_per_source": [5],
            "instruction": (
                "The user is asking about professional work experience. "
                "Focus on:\n"
                "- Company names, roles, and duration\n"
                "- Key projects and responsibilities\n"
                "- Specific achievements and quantifiable impact\n"
                "- Technologies used in professional settings\n"
                "Avoid mentioning personal/side projects unless specifically asked."
            ),
            "fallback_message": (
                "I don't have that specific information about my work experience, "
                "but I can tell you about my professional background and roles."
            ),
        }

    # Personal projects configuration
    if 'personal_projects' in existing_types:
        config['personal_projects'] = {
            "sources": ['personal_projects'],
            "k_per_source": [5],
            "instruction": (
                "The user is asking about personal/side projects. "
                "Focus on:\n"
                "- Project names and descriptions\n"
                "- Technologies and frameworks used\n"
                "- Key features and innovations\n"
                "- Links to repositories or demos when available\n"
                "- Learning outcomes or challenges overcome"
            ),
            "fallback_message": (
                "I don't have information about that specific project, "
                "but I can tell you about my other personal projects and what I've built."
            ),
        }

    # Education configuration
    if 'education' in existing_types:
        config['education'] = {
            "sources": ['education'],
            "k_per_source": [5],
            "instruction": (
                "The user is asking about educational background. "
                "Provide details about:\n"
                "- Degrees and institutions\n"
                "- Academic achievements and grades\n"
                "- Relevant coursework or certifications\n"
                "- Graduation dates and academic focus"
            ),
            "fallback_message": (
                "I can share information about my educational background and qualifications."
            ),
        }

    # Contact/profile configuration
    if any(t in existing_types for t in ['contact', 'profile']):
        available_contact_sources = [t for t in [
            'contact', 'profile'] if t in existing_types]
        config['contact'] = {
            "sources": available_contact_sources,
            "k_per_source": [3] * len(available_contact_sources),
            "instruction": (
                "The user is asking about contact information or personal details. "
                "Provide available contact methods and profile information."
            ),
            "fallback_message": (
                "I don't have that specific contact information available."
            ),
        }

    # Always include general fallback
    config['general'] = {
        "sources": None,  # Search all types
        "k_per_source": [7],
        "instruction": "Provide helpful information based on available data.",
        "fallback_message": (
            "I don't have information about that specific topic. "
            "You can ask me about my skills, experience, projects, or education."
        ),
    }

    return config


# Cache the config to avoid repeated database calls
_cached_config = None
_cache_valid = False


def invalidate_cache():
    """Invalidate the cached configuration (call after data ingestion)"""
    global _cached_config, _cache_valid
    _cached_config = None
    _cache_valid = False


def get_intent_config(intent: str) -> IntentConfig:
    """Get configuration for specific intent, using cached config when possible"""
    global _cached_config, _cache_valid

    if not _cache_valid or _cached_config is None:
        _cached_config = get_dynamic_intent_config()
        _cache_valid = True

    return _cached_config.get(intent, _cached_config['general'])


# Legacy constants for backward compatibility
SOURCE_DISPLAY_NAMES = {
    "skills": "Technical Skills",
    "professional_experience": "Professional Experience",
    "personal_projects": "Personal Projects",
    "education": "Education",
    "contact": "Contact Information",
    "profile": "Profile",
    "general": "General Information",
}


def get_source_display_name(source: str) -> str:
    """Get display name for a source type."""
    return SOURCE_DISPLAY_NAMES.get(source, source.replace("_", " ").title())


# For backward compatibility, expose the dynamic config as INTENT_CONFIGS
def get_intent_configs():
    """Get all intent configurations"""
    global _cached_config, _cache_valid

    if not _cache_valid or _cached_config is None:
        _cached_config = get_dynamic_intent_config()
        _cache_valid = True

    return _cached_config


# Dynamic property that always returns current config
class IntentConfigProperty:
    def __getitem__(self, key):
        return get_intent_configs()[key]

    def get(self, key, default=None):
        return get_intent_configs().get(key, default)

    def keys(self):
        return get_intent_configs().keys()

    def items(self):
        return get_intent_configs().items()

    def values(self):
        return get_intent_configs().values()


INTENT_CONFIGS = IntentConfigProperty()
