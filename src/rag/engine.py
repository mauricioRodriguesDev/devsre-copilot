"""Módulo RAG (Retrieval-Augmented Generation) para DevSRE-Companion.

Responsável por ler, segmentar (chunking) e indexar a documentação interna e runbooks
em um banco vetorial (ChromaDB), permitindo buscas semânticas de alta precisão.
"""

import os
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings

logger = logging.getLogger(__name__)


class KnowledgeBaseRAG:
    """Gerencia a base de conhecimento técnica e a busca semântica."""

    def __init__(self, db_dir: Optional[str] = None, collection_name: str = "devsre_docs"):
        if db_dir is None:
            # Padrão: chroma_db no diretório raiz do pacote
            default_dir = Path(__file__).resolve().parent.parent.parent / "chroma_db"
            self.db_dir = default_dir if default_dir.parent.exists() else Path("chroma_db")
        else:
            self.db_dir = Path(db_dir)

        self.collection_name = collection_name
        self.client = chromadb.PersistentClient(path=str(self.db_dir))
        self.collection = self.client.get_or_create_collection(name=self.collection_name)

    def _chunk_markdown(self, content: str, source_name: str) -> List[Dict[str, Any]]:
        """Divide documentos Markdown com base em cabeçalhos (Chunking Estruturado).

        Preserva blocos de código intactos (evita que linhas com '#' dentro de
        blocos de código delimitados por ``` sejam interpretadas como títulos).
        """
        sections = []
        current_header = "Introdução"
        current_lines = []
        in_code_block = False

        for line in content.splitlines():
            stripped = line.strip()
            # Alterna estado ao encontrar delimitador de bloco de código
            if stripped.startswith("```"):
                in_code_block = not in_code_block
                current_lines.append(line)
                continue

            # Cabeçalho fora de bloco de código define nova seção
            if not in_code_block and line.startswith("#"):
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

    def index_directory(self, docs_dir: Optional[str] = None, reset: bool = False) -> int:
        """Lê todos os arquivos Markdown da pasta e indexa no banco vetorial de forma determinística."""
        if reset:
            try:
                self.client.delete_collection(self.collection_name)
                self.collection = self.client.get_or_create_collection(name=self.collection_name)
            except Exception as e:
                logger.warning(f"Aviso ao reiniciar coleção do ChromaDB: {e}")

        if docs_dir is None:
            default_docs = Path(__file__).resolve().parent.parent.parent / "knowledge_base"
            dir_path = default_docs if default_docs.exists() else Path("knowledge_base")
        else:
            dir_path = Path(docs_dir)

        if not dir_path.exists():
            return 0

        total_indexed = 0
        # Ordenação explícita para reprodutibilidade entre plataformas (Windows/Linux)
        for file_path in sorted(dir_path.glob("*.md")):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                file_chunks = self._chunk_markdown(content, file_path.name)
                if not file_chunks:
                    continue

                documents = [c["text"] for c in file_chunks]
                metadatas = [{"source": c["source"], "section": c["section"]} for c in file_chunks]
                # IDs determinísticos vinculados ao arquivo e à posição relativa
                ids = [f"{c['source']}#{idx}" for idx, c in enumerate(file_chunks)]

                self.collection.upsert(
                    documents=documents,
                    metadatas=metadatas,
                    ids=ids,
                )
                total_indexed += len(documents)
            except Exception as e:
                logger.error(f"Erro ao processar arquivo {file_path}: {e}")

        return total_indexed

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
