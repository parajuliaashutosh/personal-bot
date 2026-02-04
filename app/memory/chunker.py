"""
Semantic Chunker for Markdown files.
Splits documents by logical sections rather than arbitrary line breaks.
Extracts metadata like technologies mentioned for better retrieval.
"""

import re
from pathlib import Path
from typing import Generator, Optional
from dataclasses import dataclass
from app.models.profile import extract_technologies


@dataclass
class Chunk:
    """Represents a semantic chunk of content"""
    content: str
    metadata: dict


class SemanticChunker:
    """
    Data-agnostic chunker that adapts to any user's data structure.
    Auto-detects content types regardless of file names.
    """

    def __init__(self, min_chunk_size: int = 100, max_chunk_size: int = 2000):
        """
        Args:
            min_chunk_size: Minimum characters for a chunk
            max_chunk_size: Maximum characters before splitting
        """
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size

        # Content type indicators - works for any user's data
        self.type_indicators = {
            'skills': [
                'skill', 'proficiency', 'technology', 'programming', 'framework', 'language',
                'database', 'tool', 'expertise', 'competency', 'technical', 'tech stack',
                'technologies used', 'experience with', 'proficient in', 'familiar with'
            ],
            'professional_experience': [
                'company', 'role', 'position', 'job', 'work', 'employment', 'career',
                'professional', 'employer', 'workplace', 'responsibilities', 'duties',
                'achievements', 'accomplishments', 'duration', 'tenure'
            ],
            'personal_projects': [
                'project', 'built', 'developed', 'created', 'github', 'repository',
                'personal', 'side project', 'hobby', 'open source', 'portfolio',
                'demo', 'prototype', 'experiment', 'hackathon'
            ],
            'education': [
                'university', 'college', 'degree', 'graduation', 'bachelor', 'master',
                'school', 'education', 'academic', 'study', 'course', 'curriculum',
                'gpa', 'grade', 'diploma', 'certificate', 'qualification'
            ],
            'contact': [
                'email', 'phone', 'linkedin', 'github', 'website', 'contact',
                'reach', 'connect', 'social', 'profile', 'portfolio site'
            ],
            'profile': [
                'name', 'summary', 'about', 'bio', 'overview', 'introduction',
                'background', 'who am i', 'about me', 'personal statement'
            ],
        }

    def detect_content_type(self, content: str, filename: str = "") -> str:
        """
        Auto-detect what type of information this content contains.
        Works for any user's data structure.
        """
        content_lower = content.lower()
        filename_lower = filename.lower()

        # Check filename first for obvious indicators
        for data_type, indicators in self.type_indicators.items():
            if any(indicator in filename_lower for indicator in indicators):
                return data_type

        # Analyze content for type indicators with weighted scoring
        type_scores = {}
        content_words = content_lower.split()

        for data_type, indicators in self.type_indicators.items():
            score = 0
            for indicator in indicators:
                if ' ' in indicator:
                    # Multi-word indicators get higher weight
                    if indicator in content_lower:
                        score += 3
                else:
                    # Single word indicators
                    if indicator in content_words:
                        score += 1
                    # Partial matches in compound words
                    elif any(indicator in word for word in content_words):
                        score += 0.5

            type_scores[data_type] = score

        # Return the type with highest score, or 'general' if unclear
        # Minimum confidence threshold
        if type_scores and max(type_scores.values()) > 2:
            return max(type_scores, key=type_scores.get)

        return 'general'

    def _infer_type(self, filename: str, content: str = "") -> str:
        """Infer content type from filename and content"""
        return self.detect_content_type(content, filename)

    def _split_by_headers(self, content: str) -> list[dict]:
        """
        Split markdown content by headers (## or ###).
        Keeps header with its content.
        """
        # Pattern to match markdown headers (## or ###)
        header_pattern = r'^(#{2,3})\s+(.+)$'

        lines = content.split('\n')
        sections = []
        current_section = {"header": "Introduction", "level": 1, "content": []}

        for line in lines:
            header_match = re.match(header_pattern, line)

            if header_match:
                # Save previous section if it has content
                if current_section["content"]:
                    section_content = '\n'.join(
                        current_section["content"]).strip()
                    if section_content:
                        sections.append({
                            "header": current_section["header"],
                            "level": current_section["level"],
                            "content": section_content
                        })

                # Start new section
                level = len(header_match.group(1))
                header_text = header_match.group(2).strip()
                current_section = {"header": header_text,
                                   "level": level, "content": [line]}
            else:
                current_section["content"].append(line)

        # Don't forget the last section
        if current_section["content"]:
            section_content = '\n'.join(current_section["content"]).strip()
            if section_content:
                sections.append({
                    "header": current_section["header"],
                    "level": current_section["level"],
                    "content": section_content
                })

        return sections

    def _merge_small_sections(self, sections: list[dict]) -> list[dict]:
        """Merge sections that are too small"""
        if not sections:
            return []

        merged = []
        current = None

        for section in sections:
            content_len = len(section["content"])

            if current is None:
                current = section.copy()
            elif content_len < self.min_chunk_size:
                # Merge with current
                current["content"] += f"\n\n{section['header']}\n{section['content']}"
                current["header"] = f"{current['header']} & {section['header']}"
            else:
                # Save current and start new
                if len(current["content"]) >= self.min_chunk_size:
                    merged.append(current)
                current = section.copy()

        # Don't forget the last one
        if current and len(current["content"]) >= self.min_chunk_size // 2:
            merged.append(current)

        return merged

    def _split_large_section(self, section: dict) -> list[dict]:
        """Split sections that are too large"""
        content = section["content"]

        if len(content) <= self.max_chunk_size:
            return [section]

        # Split by paragraphs (double newline)
        paragraphs = content.split('\n\n')
        chunks = []
        current_chunk = []
        current_size = 0

        for para in paragraphs:
            para_size = len(para)

            if current_size + para_size > self.max_chunk_size and current_chunk:
                # Save current chunk
                chunks.append({
                    "header": section["header"],
                    "level": section["level"],
                    "content": '\n\n'.join(current_chunk)
                })
                current_chunk = [para]
                current_size = para_size
            else:
                current_chunk.append(para)
                current_size += para_size

        # Last chunk
        if current_chunk:
            chunks.append({
                "header": section["header"],
                "level": section["level"],
                "content": '\n\n'.join(current_chunk)
            })

        return chunks

    def chunk_file(self, file_path: Path) -> Generator[Chunk, None, None]:
        """
        Process a file and yield semantic chunks.
        Works with any file format and auto-detects content type.

        Args:
            file_path: Path to any text file

        Yields:
            Chunk objects with content and metadata
        """
        try:
            content = file_path.read_text(encoding='utf-8').strip()
        except Exception as e:
            print(f"⚠️ Error reading {file_path}: {e}")
            return

        filename = file_path.name

        # Auto-detect content type from both filename and content
        content_type = self.detect_content_type(content, filename)

        # Handle different file formats
        if filename.endswith(('.yaml', '.yml')):
            yield from self._chunk_yaml(content, content_type, filename)
        elif filename.endswith('.json'):
            yield from self._chunk_json(content, content_type, filename)
        else:
            # Handle .md, .txt, and any other text files
            yield from self._chunk_text(content, content_type, filename)

    def _chunk_yaml(self, content: str, content_type: str, filename: str) -> Generator[Chunk, None, None]:
        """Handle YAML/YML files"""
        technologies = extract_technologies(content)
        yield Chunk(
            content=content,
            metadata={
                "type": content_type,
                "source": filename,
                "section": "profile_data",
                "technologies": ",".join(technologies) if technologies else "",
            }
        )

    def _chunk_json(self, content: str, content_type: str, filename: str) -> Generator[Chunk, None, None]:
        """Handle JSON files"""
        technologies = extract_technologies(content)
        yield Chunk(
            content=content,
            metadata={
                "type": content_type,
                "source": filename,
                "section": "structured_data",
                "technologies": ",".join(technologies) if technologies else "",
            }
        )

    def _chunk_text(self, content: str, content_type: str, filename: str) -> Generator[Chunk, None, None]:
        """Handle markdown, text, and other text-based files"""
        # Try to split by headers first
        sections = self._split_by_headers(content)

        if not sections:
            # No headers found, treat as single chunk or split by paragraphs
            if len(content) <= self.max_chunk_size:
                technologies = extract_technologies(content)
                yield Chunk(
                    content=content,
                    metadata={
                        "type": content_type,
                        "source": filename,
                        "section": "main_content",
                        "technologies": ",".join(technologies) if technologies else "",
                    }
                )
            else:
                # Split large content by paragraphs
                paragraphs = content.split('\n\n')
                current_chunk = []
                current_size = 0
                chunk_num = 1

                for para in paragraphs:
                    para_size = len(para)

                    if current_size + para_size > self.max_chunk_size and current_chunk:
                        # Yield current chunk
                        chunk_content = '\n\n'.join(current_chunk)
                        technologies = extract_technologies(chunk_content)
                        yield Chunk(
                            content=chunk_content,
                            metadata={
                                "type": content_type,
                                "source": filename,
                                "section": f"content_part_{chunk_num}",
                                "technologies": ",".join(technologies) if technologies else "",
                            }
                        )
                        current_chunk = [para]
                        current_size = para_size
                        chunk_num += 1
                    else:
                        current_chunk.append(para)
                        current_size += para_size

                # Last chunk
                if current_chunk:
                    chunk_content = '\n\n'.join(current_chunk)
                    technologies = extract_technologies(chunk_content)
                    yield Chunk(
                        content=chunk_content,
                        metadata={
                            "type": content_type,
                            "source": filename,
                            "section": f"content_part_{chunk_num}",
                            "technologies": ",".join(technologies) if technologies else "",
                        }
                    )
            return

        # Process sections normally
        sections = self._merge_small_sections(sections)

        final_sections = []
        for section in sections:
            final_sections.extend(self._split_large_section(section))

        # Yield chunks with metadata
        for section in final_sections:
            technologies = extract_technologies(section["content"])

            yield Chunk(
                content=section["content"],
                metadata={
                    "type": content_type,
                    "source": filename,
                    "section": section["header"],
                    "technologies": ",".join(technologies) if technologies else "",
                }
            )

    def chunk_directory(self, directory: Path) -> Generator[Chunk, None, None]:
        """
        Process all files in a directory recursively.
        Works with any file structure and adapts to user's organization.

        Args:
            directory: Path to directory containing any text files

        Yields:
            Chunk objects
        """
        if not directory.exists():
            print(f"❌ Error: Directory {directory} does not exist!")
            return

        # Support many text file types
        text_extensions = {'.md', '.txt', '.yaml',
                           '.yml', '.json', '.rst', '.org'}

        print(f"📁 Scanning directory: {directory.absolute()}")

        # Process files recursively
        processed_count = 0
        for file_path in directory.rglob('*'):
            if file_path.is_file() and file_path.suffix.lower() in text_extensions:
                # Skip hidden files and common non-data files
                if (not file_path.name.startswith('.') and
                        file_path.name.lower() not in {'readme.md', 'license', 'changelog.md', 'contributing.md'}):

                    print(f"📄 Processing: {file_path.relative_to(directory)}")
                    try:
                        yield from self.chunk_file(file_path)
                        processed_count += 1
                    except Exception as e:
                        print(f"⚠️ Error processing {file_path.name}: {e}")

        if processed_count == 0:
            print(f"⚠️ No suitable files found in {directory}")
            print(
                f"   Supported extensions: {', '.join(sorted(text_extensions))}")
            print(
                f"   Make sure your data files are in the directory and have supported extensions.")


def chunk_text_simple(content: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """
    Simple character-based chunking with overlap.
    Use as fallback when semantic chunking isn't applicable.
    """
    chunks = []
    start = 0

    while start < len(content):
        end = start + chunk_size
        chunk = content[start:end]

        # Try to break at sentence boundary
        if end < len(content):
            last_period = chunk.rfind('.')
            last_newline = chunk.rfind('\n')
            break_point = max(last_period, last_newline)

            if break_point > chunk_size // 2:
                chunk = content[start:start + break_point + 1]
                end = start + break_point + 1

        chunks.append(chunk.strip())
        start = end - overlap

    return [c for c in chunks if c.strip()]
