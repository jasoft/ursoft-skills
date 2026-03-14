---
name: jina-cli
description: Use when All Jina AI APIs (Reader, Search, Embed, Rerank, and more) as powerful Unix CLI commands. Ideal for web scraping, semantic search, and RAG (Retrieval-Augmented Generation) workflows.
metadata:
    openclaw:
        requires:
            env:
                - JINA_API_KEY
            bins:
                - jina
                - uv
        primaryEnv: JINA_API_KEY
---

# Jina AI CLI Skill

All Jina AI APIs (Reader, Search, Embed, Rerank, and more) as powerful Unix CLI commands. Ideal for web scraping, semantic search, and RAG (Retrieval-Augmented Generation) workflows.

## Capabilities

- **`jina search <QUERY>`**: Performs deep web searches. *Note: If this command fails with auth errors, use the curl alternative below.*
- **`jina read <URL>`**: Extracts clean, markdown-ready content from any webpage.
- **`jina embed <TEXT>`**: Generates text embeddings for semantic similarity or storage.
- **`jina rerank <QUERY>`**: Re-ranks documents based on relevance to a search query.
- **`jina screenshot <URL>`**: Captures high-quality screenshots of webpages.
- **`jina pdf <URL>`**: Extracts structured data (tables, charts, formulas) from PDF documents.
- **`jina expand <QUERY>`**: Expand queries for search.
- **`jina bibtex <QUERY>`**: Search bibtex citations.
- **`jina primer`**: Get system context (time, location, authenticated user).

## Usage Examples

### Web Search (Fallback if jina search fails)
```bash
curl -H "Authorization: Bearer $JINA_API_KEY" "https://s.jina.ai/<QUERY>"
```

### Web Reading for LLMs
```bash
jina read https://jina.ai/reader | pbcopy
```

### Advanced Search & Reranking (RAG)
```bash
jina search "latest trends in AI agents" --json | jina rerank "autonomous systems" --top-n 3
```

### Academic Research
```bash
jina search "transformer architectures" --arxiv --time 2024
jina bibtex "Attention is All You Need"
```

## Security & Configuration

- **API Token**: The `JINA_API_KEY` is pre-configured in `~/.zshrc`.
- **Environment**: Ensure the command is executed in an environment that has access to the shell profile.
