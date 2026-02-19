# Docker Setup Guide

This guide explains how to run the personal chatbot using Docker and Docker Compose with Ollama.

## Prerequisites

- Docker and Docker Compose installed on your system
- At least 4GB of free RAM (for running language models)
- Optional: NVIDIA GPU support for faster model inference

## Useful Commands

```
docker compose up -d ollama
docker compose up ollama-init    # this pulls the model automatically
docker compose run --rm ingest
docker compose up -d chatbot
```
