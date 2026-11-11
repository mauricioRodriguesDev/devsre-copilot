"""Módulo RAG (Retrieval-Augmented Generation) para DevSRE-Companion.

Responsável por ler, segmentar (chunking) e indexar a documentação interna e runbooks
em um banco vetorial (ChromaDB), permitindo buscas semânticas de alta precisão.
"""

import os
from pathlib import Path
from typing import List, Dict, Any
import chromadb
from chromadb.config import Settings


class KnowledgeBaseRAG:
    """Gerencia a base de conhecimento técnica e a busca semântica."""

    def __init__(self, db_dir: str = "chroma_db", collection_name: str = "devsre_docs"):
        self.db_dir = Path(db_dir)
        self.collection_name = collection_name
        self.client = chromadb.PersistentClient(path=str(self.db_dir))
        self.collection = self.client.get_or_create_collection(name=self.collection_name)

    def _chunk_markdown(self, content: str, source_name: str) -> List[Dict[str, Any]]:
        """Divide documentos Markdown com base em cabeçalhos (Chunking Estruturado)."""
        sections = []
        current_header = "Introdução"
        current_lines = []

        for line in content.splitlines():
            if line.startswith("#"):
                if current_lines:
                    text_chunk = "\n".join(current_lines).strip()
                    if text_chunk:
                        sections.append({
                            "text": f"[{source_name} > {current_header}]\n{text_chunk}",
                            "source": source_name,
                            "section": current_header,
                        })
                    current_lines = []
                current_header = line.lstrip("#").strip()
            else:
                current_lines.append(line)

        if current_lines:
            text_chunk = "\n".join(current_lines).strip()
            if text_chunk:
                sections.append({
                    "text": f"[{source_name} > {current_header}]\n{text_chunk}",
                    "source": source_name,
                    "section": current_header,
                })

        return sections

    def index_directory(self, docs_dir: str = "knowledge_base") -> int:
        """Lê todos os arquivos Markdown da pasta e indexa no banco vetorial."""
        dir_path = Path(docs_dir)
        if not dir_path.exists():
            return 0

        chunks_to_index = []
        for file_path in dir_path.glob("*.md"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                chunks = self._chunk_markdown(content, file_path.name)
                chunks_to_index.extend(chunks)
            except Exception as e:
                print(f"Erro ao processar arquivo {file_path}: {e}")

        if not chunks_to_index:
            return 0

        # Adiciona ao ChromaDB com IDs determinísticos
        documents = [c["text"] for c in chunks_to_index]
        metadatas = [{"source": c["source"], "section": c["section"]} for c in chunks_to_index]
        ids = [f"{c['source']}#{idx}" for idx, c in enumerate(chunks_to_index)]

        self.collection.upsert(
            documents=documents,
            metadatas=metadatas,
            ids=ids,
        )
        return len(documents)

    def search(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """Realiza busca semântica por similaridade vetorial."""
        count = self.collection.count()
        if count == 0:
            return []

        results = self.collection.query(
            query_texts=[query],
            n_results=min(top_k, count),
        )

        formatted = []
        if results and "documents" in results and results["documents"]:
            docs = results["documents"][0]
            metas = results["metadatas"][0] if "metadatas" in results else [{}] * len(docs)
            for doc, meta in zip(docs, metas):
                formatted.append({
                    "content": doc,
                    "source": meta.get("source", "desconhecido"),
                    "section": meta.get("section", ""),
                })
        return formatted


if __name__ == "__main__":
    # Teste de verificação rápida do RAG
    rag = KnowledgeBaseRAG()
    total = rag.index_directory("knowledge_base")
    print(f"Total de chunks indexados: {total}")
    matches = rag.search("Como lidar com token expirado?", top_k=2)
    for m in matches:
        print(f"\n--- Encontrado em: {m['source']} ({m['section']}) ---\n{m['content']}")
