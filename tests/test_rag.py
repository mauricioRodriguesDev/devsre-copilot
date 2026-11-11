"""Testes unitários rigorosos para a Engine de RAG e Chunking."""

import tempfile
from pathlib import Path
from src.rag.engine import KnowledgeBaseRAG


def test_chunk_markdown_preserves_code_blocks_with_hash_comments():
    """Garante que linhas com '#' dentro de blocos ``` não sejam interpretadas como headers."""
    rag = KnowledgeBaseRAG.__new__(KnowledgeBaseRAG)

    sample_md = """# Guia de Autenticação

Este é o texto introdutório.

```python
# Comentário de código em Python
def authenticate(token):
    # Outro comentário interno
    return True
```

## Seção Seguinte
Conteúdo da seção seguinte.
"""

    chunks = rag._chunk_markdown(sample_md, "test_doc.md")

    # Deve conter exatamente 2 seções: "Guia de Autenticação" e "Seção Seguinte"
    # Se estivesse quebrando nos comentários, haveria 4 seções!
    assert len(chunks) == 2
    assert chunks[0]["section"] == "Guia de Autenticação"
    assert "# Comentário de código em Python" in chunks[0]["text"]
    assert "# Outro comentário interno" in chunks[0]["text"]
    assert chunks[1]["section"] == "Seção Seguinte"


def test_rag_indexing_and_search():
    """Valida indexação e busca semântica em diretório temporário."""
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        db_dir = Path(tmpdir) / "chroma"
        docs_dir = Path(tmpdir) / "docs"
        docs_dir.mkdir()

        doc_file = docs_dir / "runbook_cache.md"
        doc_file.write_text(
            "# Runbook Cache Redis\n\n"
            "## Tratamento de Cache Stampede\n"
            "Utilize padrão singleflight e jitter de 15% para evitar sobrecarga no banco.\n",
            encoding="utf-8",
        )

        rag = KnowledgeBaseRAG(db_dir=str(db_dir), collection_name="test_collection")
        indexed_count = rag.index_directory(str(docs_dir))
        assert indexed_count >= 1

        results = rag.search("Como evitar sobrecarga e cache stampede no redis?", top_k=1)
        assert len(results) == 1
        assert "runbook_cache.md" in results[0]["source"]
        assert "singleflight" in results[0]["content"].lower()
