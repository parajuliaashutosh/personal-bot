# 🤖 Personal RAG Chatbot

A production-grade, **data-agnostic** Personal AI Assistant that learns from your data. Built with FastAPI, ChromaDB, and modern RAG techniques. Works with **any data structure** - just add your files and go!

## 🌟 Features

- **🎯 Data-Agnostic**: Works with any user's data automatically
- **🔄 Hybrid Search**: Vector similarity + BM25 keyword search
- **🚀 Production-Ready**: Rate limiting, streaming responses, proper error handling
- **🧠 Smart Intent Recognition**: Adapts to your data types automatically
- **🔌 Model-Agnostic**: OpenAI API or local Ollama support
- **📊 Semantic Chunking**: Intelligent content type detection
- **⚡ Fast Setup**: One-command setup script for new users

## 🚀 Quick Start

### Option 1: Automated Setup (Recommended)

```bash
# Clone and setup
git clone git@github.com:parajuliaashutosh/personal-bot.git
cd fastapi-personal-chatbot
python setup_personal_chatbot.py
```

The setup script will:

- Create example data files for you to customize
- Set up environment configuration
- Install dependencies
- Process your data
- Guide you through customization

### Option 2: Manual Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Create your data files (see examples below)
mkdir data
# Add your .md, .txt, .yaml, .json files to data/

# Set up environment
cp .env.example .env
# Edit .env with your API keys

# Process your data
python -m app.memory.ingest

# Start the server
uvicorn app.main:app --reload
```

## 📁 Data Structure

The system automatically adapts to any data structure. Here are recommended file types:

### Supported File Types

- **📝 Markdown (\*.md)**: Experience, projects, skills, any text content
- **📄 Text (\*.txt)**: Notes, documentation, articles
- **⚙️ YAML (\*.yaml)**: Structured data, configuration, profiles
- **🗂️ JSON (\*.json)**: Structured data, API responses

### Example Data Organization

```
data/
├── profile.yaml          # Basic info: name, role, contact
├── experience.md          # Work history and achievements
├── projects.md           # Personal and professional projects
├── skills.md             # Technical skills and expertise
├── education.md          # Education and certifications
└── any_other_files.*     # Blog posts, notes, anything!
```

### Sample Content Examples

**profile.yaml**:

```yaml
name: "Your Name"
current_role: "Your Position"
summary: |
  Brief description of yourself and expertise
```

**experience.md**:

```markdown
# Professional Experience

## Software Engineer at Company

- Built scalable APIs with Python/FastAPI
- Implemented ML models for recommendation systems
```

**projects.md**:

```markdown
# Personal Projects

## AI Chatbot

Technologies: Python, FastAPI, ChromaDB, LLMs
Built a personal assistant that learns from user data...
```

## ⚙️ Configuration

### Environment Variables (.env)

```bash
# LLM Provider (choose one)
OPENAI_API_KEY=your_openai_key_here
# OR
OLLAMA_MODEL=llama3.2

# Security
API_KEY=your_secure_api_key

```

## 🔧 Usage

### Start the Server

```bash
uvicorn app.main:app --reload
```

### API Documentation

Visit: `http://localhost:8000/docs`

### Example Requests

**Chat with your AI:**

```bash
curl -X POST "http://localhost:8000/chat" \
  -H "X-API-KEY: your_api_key" \
  -H "Content-Type: application/json" \
  -d '{"message": "Tell me about your Python experience"}'
```

**Refresh data after updates:**

```bash
python -m app.memory.ingest
```

## 🧠 How It Works

### 1. **Adaptive Data Ingestion**

- Automatically detects content types from file content (not filenames)
- Extracts technologies and skills dynamically using regex patterns
- Creates semantic chunks optimized for retrieval

### 2. **Hybrid Search Engine**

- **Vector Search**: Semantic similarity using embeddings
- **BM25 Search**: Keyword-based search for exact terms
- **Weighted Combination**: Best of both approaches

### 3. **Intent Classification**

- Dynamically configures based on available data types
- Routes queries to appropriate data sources
- Adapts to any user's data structure automatically

### 4. **Context Generation**

- Retrieves most relevant chunks for each query
- Provides proper context to the LLM
- Maintains conversation memory

## 🏗️ Architecture

```
Data Files → Chunker → Vector DB → Hybrid Search → Context → LLM → Response
     ↓           ↓          ↓           ↓          ↓        ↓
   Content   Semantic   ChromaDB    BM25 +     Relevant  OpenAI/
   Analysis  Chunking             Vector     Chunks    Ollama
```

### Key Components

- **`app/memory/chunker.py`**: Content-aware document processing
- **`app/memory/vector.py`**: Hybrid search implementation
- **`app/config/intent_config.py`**: Adaptive intent routing
- **`app/models/profile.py`**: Dynamic technology extraction
- **`app/service/chat_service.py`**: Configuration-driven chat logic

## 🔄 Updating Your Data

When you modify your data files:

1. **Edit your files** in the `data/` folder
2. **Re-run ingestion**: `python -m app.memory.ingest`
3. **Test immediately** - no server restart needed!

The system will:

- Clear old data automatically
- Re-process all files
- Update the intent configuration
- Maintain conversation context

## 🔍 Customization

### Adding New Data Types

The system automatically handles new file types:

- Drop any `.md`, `.txt`, `.yaml`, `.json` file in `data/`
- The chunker auto-detects content type and structure
- Intent configuration adapts automatically

### Technology Detection

The system recognizes any technology mentioned in your content:

- Programming languages: Python, TypeScript, Java, etc.
- Frameworks: FastAPI, React, NestJS, etc.
- Tools: Docker, Git, AWS, etc.
- No configuration needed - uses smart regex patterns

### Custom Intent Routing

Edit `app/config/intent_config.py` to customize how queries are routed:

```python
# Add custom intent categories
custom_intents = {
    "hobbies": {
        "keywords": ["hobby", "interest", "passion"],
        "data_types": ["personal_interests"]
    }
}
```

## 🐳 Docker Support

```bash
# Build and run
docker build -t personal-chatbot .
docker run -p 8000:8000 -v ./data:/app/data personal-chatbot
```

## 🔒 Security Features

- **API Key Authentication**: Secure your endpoints
- **Rate Limiting**: Prevent abuse with configurable limits
- **Input Validation**: Pydantic schemas for all requests
- **CORS Configuration**: Safe cross-origin requests

## 🤝 Contributing

This project is designed to be easily extensible:

1. **Add new LLM providers** in `app/llm/`
2. **Enhance chunking strategies** in `app/memory/chunker.py`
3. **Improve search algorithms** in `app/memory/vector.py`
4. **Extend intent recognition** in `app/config/intent_config.py`

## 📝 License

MIT License - feel free to customize for your needs!

## 🆘 Troubleshooting

### Common Issues

**"No data found" error:**

- Ensure files are in the `data/` folder
- Run `python -m app.memory.ingest` to process data
- Check that files contain actual content

**LLM connection errors:**

- Verify API keys in `.env` file
- For Ollama: ensure it's running on `http://localhost:11434`
- Check network connectivity

**Poor search results:**

- Add more specific content to your data files
- Include relevant keywords and technologies
- Re-run ingestion after content updates

### Getting Help

1. Check the FastAPI docs at `/docs` endpoint
2. Review error logs in the console
3. Ensure your data files have sufficient content
4. Test with simple queries first

---

🚀 **Ready to build your personal AI assistant?** Run the setup script and start chatting with your data!
