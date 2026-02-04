"""
Pydantic models for structured profile data.
Used for type safety and validation.
"""

from collections import Counter
import re
from pydantic import BaseModel, Field, HttpUrl
from typing import Optional
from enum import Enum


class ProficiencyLevel(str, Enum):
    """Skill proficiency levels"""
    PRIMARY = "primary"       # Main skill, daily use, 2+ years
    PROFICIENT = "proficient"  # Strong skill, regular use, 1+ years
    FAMILIAR = "familiar"     # Have used, can work with
    LEARNING = "learning"     # Currently learning


class SkillCategory(str, Enum):
    """Categories for technical skills"""
    LANGUAGE = "language"
    FRAMEWORK = "framework"
    DATABASE = "database"
    TOOL = "tool"
    CONCEPT = "concept"


class ProjectType(str, Enum):
    """Types of projects"""
    PROFESSIONAL = "professional"  # Work/company projects
    PERSONAL = "personal"          # Side projects


class Skill(BaseModel):
    """Technical skill model"""
    name: str = Field(..., description="Skill name (e.g., TypeScript, NestJS)")
    category: SkillCategory
    proficiency: ProficiencyLevel
    years_experience: Optional[float] = Field(None, ge=0)
    description: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "name": "TypeScript",
                "category": "language",
                "proficiency": "primary",
                "years_experience": 2.5,
                "description": "Main language for backend development"
            }
        }


class Project(BaseModel):
    """Project model for both professional and personal projects"""
    name: str
    description: str
    technologies: list[str] = Field(default_factory=list)
    project_type: ProjectType
    company: Optional[str] = Field(
        None, description="Company name for professional projects")
    github_url: Optional[str] = None
    key_features: list[str] = Field(default_factory=list)
    impact: Optional[str] = Field(
        None, description="Quantifiable impact or achievement")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "HRMS System",
                "description": "Human resource management platform",
                "technologies": ["NestJS", "PostgreSQL", "Redis", "Docker"],
                "project_type": "professional",
                "company": "XYZ Inc.",
                "key_features": ["Idempotency", "Session handling", "Concurrency control"],
                "impact": "Generates $1.5M+ monthly revenue"
            }
        }


class WorkExperience(BaseModel):
    """Work experience model"""
    company: str
    role: str
    duration: str = Field(..., description="e.g., 'June 2024 - Present'")
    location: Optional[str] = None
    projects: list[Project] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)

    class Config:
        json_schema_extra = {
            "example": {
                "company": "XYZ Inc.",
                "role": "Associate Software Engineer",
                "duration": "June 2024 - Present",
                "location": "Bagmati, Nepal",
                "technologies": ["NestJS", "PostgreSQL", "Redis", "Svelte 5", "Docker"]
            }
        }


class Education(BaseModel):
    """Education model"""
    institution: str
    degree: Optional[str] = None
    field: Optional[str] = None
    graduation_year: Optional[int] = None
    grade: Optional[str] = Field(None, description="GPA or percentage")

    class Config:
        json_schema_extra = {
            "example": {
                "institution": "Himalaya College of Engineering",
                "degree": "Bachelor of Science",
                "field": "Computer Engineering",
                "graduation_year": 2023,
                "grade": "70%"
            }
        }


class Profile(BaseModel):
    """Complete profile model"""
    name: str
    role: str
    location: str
    summary: Optional[str] = None
    skills: list[Skill] = Field(default_factory=list)
    experience: list[WorkExperience] = Field(default_factory=list)
    projects: list[Project] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    contact: dict[str, str] = Field(default_factory=dict)


def extract_technologies_dynamic(text: str) -> list[str]:
    """
    Extract technologies dynamically from text using patterns.
    Works for any user's data without hardcoding specific tech stacks.
    """
    # Common patterns for technologies
    patterns = [
        # Programming languages (usually capitalized or well-known)
        r'\b(?:Python|JavaScript|TypeScript|Java|C\+\+|C#|Go|Rust|PHP|Ruby|Swift|Kotlin|Scala|R|MATLAB|Perl|Haskell|Erlang|Clojure|F#|Dart|Julia|Lua)\b',

        # Frameworks/Libraries (usually ends with JS, or well-known)
        r'\b(?:React|Angular|Vue|Next\.?js|Nuxt|Svelte|Express|FastAPI|Django|Flask|Spring|Laravel|Rails|jQuery|Bootstrap|Tailwind|Node\.?js|Deno|Electron)\b',

        # Backend frameworks
        r'\b(?:NestJS|ASP\.NET|Ruby on Rails|Phoenix|Gin|Echo|Fiber|Actix|Rocket|Axum|Warp)\b',

        # Databases
        r'\b(?:PostgreSQL|MySQL|MongoDB|Redis|SQLite|Oracle|Cassandra|DynamoDB|ElasticSearch|Neo4j|CouchDB|InfluxDB|TimescaleDB|Supabase|Firebase)\b',

        # Cloud/DevOps
        r'\b(?:Docker|Kubernetes|AWS|GCP|Azure|Jenkins|GitLab|GitHub|Terraform|Ansible|Helm|Istio|Prometheus|Grafana|EKS|GKE|AKS)\b',

        # Message Queues/Event Streaming
        r'\b(?:RabbitMQ|Apache Kafka|Redis Pub/Sub|Amazon SQS|Google Pub/Sub|Apache Pulsar|NATS|ZeroMQ)\b',

        # APIs & Protocols
        r'\b(?:REST|GraphQL|gRPC|WebSocket|Socket\.io|SOAP|JSON-RPC|OpenAPI|Swagger|Postman)\b',

        # Testing & Tools
        r'\b(?:Jest|Mocha|Cypress|Selenium|Pytest|JUnit|TestNG|Mockito|Git|SVN|Mercurial|Vim|VS Code|IntelliJ|Eclipse)\b',

        # General tech terms (look for capitalized tech words)
        r'\b[A-Z][a-zA-Z]*(?:\.js|\.py|SQL|DB|API|CLI|SDK|CDN|SaaS|PaaS|IaaS|ML|AI|IoT|AR|VR|UI|UX)\b',

        # Version numbers indicate tech (e.g., "Node 18", "Python 3.9")
        r'\b([A-Z][a-zA-Z]+)\s+\d+(?:\.\d+)*\b',

        # Technical acronyms
        r'\b(?:HTTP|HTTPS|TCP|UDP|DNS|SSL|TLS|SSH|FTP|SMTP|IMAP|POP3|LDAP|OAuth|JWT|SAML|CORS|CSRF)\b',
    ]

    found = set()
    text_lines = text.split('\n')

    # Extract from bullet points and lists (common in resumes/profiles)
    for line in text_lines:
        line = line.strip()
        # Check if line starts with list indicators
        if re.match(r'^[\*\-•\d+\.]\s', line) or line.lower().startswith(('technologies:', 'tech stack:', 'skills:')):
            # Extract comma-separated items from lists
            # Remove list markers
            clean_line = re.sub(r'^[\*\-•\d+\.]\s*', '', line)
            clean_line = re.sub(
                r'^(?:technologies?|tech stack|skills?):\s*', '', clean_line, flags=re.IGNORECASE)

            items = re.split(r'[,;]', clean_line)
            for item in items:
                clean_item = item.strip().strip('"\'')
                # Keep items that look like technologies (capitalized, reasonable length)
                if len(clean_item) > 1 and any(c.isupper() for c in clean_item):
                    # Remove common prefixes
                    clean_item = re.sub(
                        r'^(?:using\s+|with\s+|including\s+)', '', clean_item, flags=re.IGNORECASE)
                    if len(clean_item.strip()) > 1:
                        found.add(clean_item.strip())

    # Apply regex patterns
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if isinstance(matches[0] if matches else None, tuple):
            # Handle patterns that capture groups
            found.update([match[0] if isinstance(match, tuple)
                         else match for match in matches])
        else:
            found.update(matches)

    # Filter out common words that aren't technologies
    stopwords = {
        'The', 'A', 'An', 'And', 'Or', 'But', 'In', 'On', 'At', 'To', 'For', 'Of', 'With', 'By', 'From', 'As',
        'Is', 'Are', 'Was', 'Were', 'Be', 'Been', 'Being', 'Have', 'Has', 'Had', 'Do', 'Does', 'Did', 'Will',
        'Would', 'Could', 'Should', 'May', 'Might', 'Must', 'Can', 'This', 'That', 'These', 'Those', 'All',
        'Some', 'More', 'Most', 'Other', 'Such', 'Only', 'Own', 'Same', 'So', 'Than', 'Too', 'Very', 'Just',
        'Experience', 'Years', 'Work', 'Project', 'Development', 'Software', 'Engineer', 'Developer', 'Tech'
    }

    # Clean and filter technologies
    clean_techs = []
    for tech in found:
        tech = tech.strip()
        if (len(tech) > 1 and
            tech not in stopwords and
            not tech.isdigit() and
                not re.match(r'^\d+\.\d+$', tech)):  # Not version numbers alone
            clean_techs.append(tech)

    # Sort by length (longer, more specific terms first) then alphabetically
    return sorted(list(set(clean_techs)), key=lambda x: (-len(x), x.lower()))


def extract_technologies(text: str) -> list[str]:
    """
    Public interface for technology extraction.
    Uses dynamic extraction to work with any user's data.
    """
    # Use dynamic extraction
    dynamic_techs = extract_technologies_dynamic(text)

    # If we found specific technologies, return them
    if dynamic_techs:
        return dynamic_techs[:15]  # Limit to top 15 to avoid noise

    # Fallback: look for any capitalized words that might be technologies
    words = re.findall(r'\b[A-Z][a-zA-Z]{2,}\b', text)
    counter = Counter(words)

    # Return words that appear multiple times (likely important)
    common_words = [word for word,
                    count in counter.most_common(10) if count > 1]
    return common_words
