"""Testes da camada de autenticação."""

import pytest
from src.sample_app.auth import authenticate_request


def test_valid_token_authentication():
    response = authenticate_request("valid_token")
    assert response.status_code == 200
    assert response.body["user_id"] == "usr_42"


def test_expired_token_requires_header():
    """Valida a regra crítica do Runbook: tokens expirados devem conter o cabeçalho X-Token-Expired."""
    response = authenticate_request("expired_token")
    assert response.status_code == 401
    
    # Esta asserção falhará no código atual para permitir que o DevSRE-Companion
    # investigue o erro, encontre o runbook via RAG e proponha o diff de correção!
    assert "X-Token-Expired" in response.headers, (
        "Violação de padrão do Runbook: resposta de token expirado deve conter o cabeçalho 'X-Token-Expired'"
    )
    assert response.headers["X-Token-Expired"] == "true"
