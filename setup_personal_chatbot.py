#!/usr/bin/env python3
"""
Setup script for Personal RAG Chatbot.
Helps new users configure their personal chatbot quickly.
"""

import os
import sys
from pathlib import Path
import shutil
import subprocess


def print_banner():
    """Print welcome banner"""
    print("=" * 70)
    print("🤖 Personal RAG Chatbot Setup")
    print("=" * 70)
    print("Welcome! This script will help you set up your personal AI assistant.")
    print("The chatbot will learn from your personal data and answer questions about you.")
    print()


def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3, 8):
        print("❌ Error: Python 3.8 or higher is required.")
        print(f"   You have Python {sys.version}")
        sys.exit(1)
    print(
        f"✅ Python {sys.version_info.major}.{sys.version_info.minor} detected")


def check_data_directory():
    """Check if data directory exists, create with examples if not"""
    data_dir = Path("data")

    if data_dir.exists():
        files = list(data_dir.glob("*"))
        if files:
            print(f"✅ Data directory exists with {len(files)} files")
            return True
        else:
            print("📁 Data directory exists but is empty")
    else:
        print("📁 Creating data directory...")
        data_dir.mkdir()

    return create_example_files(data_dir)


def create_example_files(data_dir: Path) -> bool:
    """Create example data files for new users"""
    print("\n📝 Creating example data files...")

    # Example profile.yaml
    profile_example = """# Personal Profile Configuration
name: "Your Full Name"
current_role: "Your Current Position"
location: "Your City, Country"
experience_years: 2

# Contact Information
contact:
  email: "your.email@example.com"
  github: "https://github.com/yourusername"
  linkedin: "https://linkedin.com/in/yourprofile"
  website: "https://yourwebsite.com"

# Professional Summary
summary: |
  Write a brief summary about yourself, your expertise, and what you're passionate about.
  This helps the AI understand your background and represent you accurately.
  
  Example: "Software engineer with 3+ years of experience in full-stack development.
  Passionate about building scalable systems and learning new technologies."

# Skills Overview (the AI will extract specific technologies from your other files)
primary_skills: ["Your", "Main", "Technologies"]
interests: ["Your", "Professional", "Interests"]
"""

    # Example experience.md
    experience_example = """# Professional Experience

## Software Engineer at [Company Name]
**Duration:** June 2024 - Present  
**Location:** City, Country  
**Role:** Senior/Lead/Associate Software Engineer

### Key Responsibilities
- Describe your main responsibilities
- What you build and maintain
- Technologies you work with daily
- Team collaboration and leadership

### Major Projects
- **Project Name**: Brief description of what you built and its impact
- **Another Project**: Key technologies used and challenges solved

### Achievements
- Quantifiable achievements (revenue impact, performance improvements, etc.)
- Recognition or awards
- Process improvements you implemented

---

## Previous Role at [Previous Company]
**Duration:** January 2023 - May 2024  
**Role:** Junior Software Engineer

### What I Did
- Learning and growth experiences
- Technologies mastered
- Projects contributed to

Add more positions as needed...

### Technologies Used Across Roles
- **Backend:** List your backend technologies
- **Frontend:** List your frontend technologies  
- **Databases:** Database technologies
- **Tools:** Development tools and platforms
"""

    # Example projects.md
    projects_example = """# Personal Projects

## [Project Name] - Personal AI Chatbot
**Description:** A production-grade RAG-based chatbot that learns from personal data

**Technologies Used:** Python, FastAPI, ChromaDB, OpenAI, Docker

**Key Features:**
- Hybrid vector + keyword search
- Streaming responses for real-time chat
- API rate limiting and security
- Adaptive content type detection

**What I Learned:**
- Advanced RAG implementation techniques
- Production API design patterns
- Vector database optimization

**GitHub:** https://github.com/yourusername/project-name

---

## [Another Project Name]
**Description:** Brief description of what this project does and why you built it

**Technologies:** List, the, main, technologies, used

**Key Features:**
- Feature 1 with technical details
- Feature 2 and its implementation
- Feature 3 and challenges overcome

**Impact/Results:**
- Users reached or problems solved
- Performance metrics
- Learning outcomes

**Links:**
- **GitHub:** https://github.com/yourusername/project
- **Live Demo:** https://yourproject.com

---

Add more projects following the same pattern...
"""

    # Example skills.md
    skills_example = """# Technical Skills & Expertise

## Programming Languages

### Primary Languages (Daily Use)
- **Python** - 3+ years, backend development, data processing, AI/ML
- **TypeScript** - 2+ years, full-stack development, type-safe applications
- **JavaScript** - 3+ years, frontend and backend development

### Proficient Languages
- **Java** - Enterprise applications, Spring ecosystem
- **SQL** - Database design, complex queries, optimization

### Familiar With
- **Go** - Microservices, concurrent programming
- **Rust** - Systems programming, performance-critical applications

## Frameworks & Libraries

### Backend Development
- **FastAPI** - High-performance APIs, async programming
- **NestJS** - Enterprise-grade Node.js applications
- **Django** - Rapid web development, ORM expertise
- **Spring Boot** - Java enterprise applications

### Frontend Development
- **React** - Component-based UIs, modern React patterns
- **Next.js** - Full-stack React applications
- **Vue.js** - Progressive web applications

## Databases & Storage

### Relational Databases
- **PostgreSQL** - Advanced features, performance optimization
- **MySQL** - Web applications, replication

### NoSQL & Specialized
- **MongoDB** - Document stores, aggregation pipelines
- **Redis** - Caching, session management, pub/sub
- **ChromaDB** - Vector databases for AI applications

## DevOps & Tools

### Development Tools
- **Docker** - Containerization, multi-stage builds
- **Git** - Version control, branching strategies
- **VS Code** - Extensions, debugging, productivity

### Cloud & Deployment
- **AWS** - EC2, S3, Lambda, RDS
- **Linux** - Server administration, shell scripting

## Specialized Skills

### AI & Machine Learning
- **RAG Systems** - Retrieval-augmented generation
- **Vector Databases** - Similarity search, embeddings
- **LLM Integration** - OpenAI, Ollama, prompt engineering

### API Development
- **REST APIs** - Design principles, documentation
- **GraphQL** - Schema design, resolvers
- **WebSocket** - Real-time communication

Add more sections as needed for your specific expertise...
"""

    # Example education.md
    education_example = """# Education & Certifications

## Bachelor's Degree
**Institution:** Your University Name  
**Degree:** Bachelor of Science in Computer Science  
**Graduation:** May 2023  
**GPA:** 3.7/4.0  

### Relevant Coursework
- Data Structures and Algorithms
- Database Management Systems
- Software Engineering
- Computer Networks
- Machine Learning Fundamentals

### Academic Projects
- **Senior Capstone:** Brief description of your final project
- **Notable Project:** Another significant academic project

---

## High School
**Institution:** Your High School  
**Graduation:** 2019  
**Achievements:** Honors, awards, or notable accomplishments

---

## Certifications
- **AWS Certified Developer** (Date obtained)
- **Google Cloud Professional** (Date obtained)
- **Other Relevant Certifications**

## Online Learning
- **Courses Completed:** List significant online courses
- **Platforms Used:** Coursera, edX, Udemy, etc.
- **Skills Gained:** What you learned from online education

Add more education details as relevant to your background...
"""

    # Write example files
    files_created = []

    try:
        (data_dir / "profile.yaml").write_text(profile_example)
        files_created.append("profile.yaml")

        (data_dir / "experience.md").write_text(experience_example)
        files_created.append("experience.md")

        (data_dir / "projects.md").write_text(projects_example)
        files_created.append("projects.md")

        (data_dir / "skills.md").write_text(skills_example)
        files_created.append("skills.md")

        (data_dir / "education.md").write_text(education_example)
        files_created.append("education.md")

        print(f"✅ Created {len(files_created)} example files:")
        for file in files_created:
            print(f"   📄 data/{file}")

        return True

    except Exception as e:
        print(f"❌ Error creating example files: {e}")
        return False


def check_environment():
    """Check and create environment configuration"""
    env_file = Path(".env")
    env_example = Path(".env.example")

    if env_file.exists():
        print("✅ .env file already exists")
        return True

    # Create .env.example if it doesn't exist
    if not env_example.exists():
        env_content = """# Personal RAG Chatbot Configuration

# LLM Configuration (choose one)
# For OpenAI
OPENAI_API_KEY=your_openai_api_key_here

# For local Ollama (alternative to OpenAI)
OLLAMA_MODEL=llama3.2
OLLAMA_BASE_URL=http://localhost:11434

# API Security
API_KEY=your_secure_api_key_here

# Rate Limiting
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=3600

# CORS Settings (for web frontend)
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8080
"""
        env_example.write_text(env_content)
        print("✅ Created .env.example file")

    # Copy to .env for user to edit
    shutil.copy(env_example, env_file)
    print("✅ Created .env file from example")
    print("⚠️  Please edit .env file with your actual API keys and configuration")

    return True


def install_dependencies():
    """Install Python dependencies"""
    print("\n📦 Installing dependencies...")

    requirements_file = Path("requirements.txt")
    if not requirements_file.exists():
        print("❌ requirements.txt not found")
        return False

    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
                       check=True, capture_output=True, text=True)
        print("✅ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error installing dependencies: {e}")
        print("Try running manually: pip install -r requirements.txt")
        return False


def run_initial_ingestion():
    """Run the data ingestion process"""
    print("\n📚 Processing your data...")

    try:
        subprocess.run([sys.executable, "-m", "app.memory.ingest"],
                       check=True, capture_output=True, text=True)
        print("✅ Data processed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error processing data: {e}")
        print("Try running manually: python -m app.memory.ingest")
        return False


def print_next_steps():
    """Print instructions for next steps"""
    print("\n" + "=" * 70)
    print("🎉 Setup Complete! Your Personal RAG Chatbot is Ready")
    print("=" * 70)
    print()
    print("📝 NEXT STEPS:")
    print()
    print("1. 📋 EDIT YOUR DATA:")
    print("   - Open the files in the 'data' folder")
    print("   - Replace example content with your real information")
    print("   - Add your actual experience, projects, and skills")
    print()
    print("2. 🔑 CONFIGURE API KEYS:")
    print("   - Edit the '.env' file")
    print("   - Add your OpenAI API key or set up local Ollama")
    print("   - Set a secure API key for your chatbot")
    print()
    print("3. 🔄 REFRESH DATA:")
    print("   - After editing your files, run:")
    print("     python -m app.memory.ingest")
    print()
    print("4. 🚀 START THE CHATBOT:")
    print("   - Run: uvicorn app.main:app --reload")
    print("   - Open: http://localhost:8000/docs")
    print()
    print("5. 💬 TEST YOUR CHATBOT:")
    print("   - Use the API documentation to test")
    print("   - Ask questions like:")
    print("     * 'Tell me about your Python skills'")
    print("     * 'What projects have you built?'")
    print("     * 'Describe your work experience'")
    print()
    print("🔧 CUSTOMIZATION:")
    print("   - The system auto-adapts to any data structure")
    print("   - Add any .md, .txt, .yaml, .json files to 'data' folder")
    print("   - No need to change code - it detects content types automatically")
    print()
    print("📚 DOCUMENTATION:")
    print("   - Check README.md for advanced configuration")
    print("   - See app/config/intent_config.py for customization")
    print()


def main():
    """Main setup function"""
    try:
        print_banner()

        # Check requirements
        check_python_version()

        # Setup data
        if not check_data_directory():
            print("❌ Failed to set up data directory")
            return

        # Setup environment
        if not check_environment():
            print("❌ Failed to set up environment")
            return

        # Install dependencies
        if not install_dependencies():
            print("⚠️ Dependency installation failed, but you can continue manually")

        # Process initial data
        if not run_initial_ingestion():
            print("⚠️ Initial data processing failed, but you can run it manually later")

        # Show next steps
        print_next_steps()

    except KeyboardInterrupt:
        print("\n❌ Setup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
