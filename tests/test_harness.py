"""Testes unitários para o AI Harness e Orquestrador ReAct."""

import tempfile
from pathlib import Path
import pytest
from src.agent.harness import DevSREHarness, _call_with_retry, MAX_TOOL_OUTPUT_LENGTH
from src.agent.schemas import RootCauseAnalysisReport


def test_harness_initialization():
    """Valida a correta inicialização dos atributos do DevSREHarness."""
    with tempfile.TemporaryDirectory() as tmpdir:
        harness = DevSREHarness(
            api_key="teste_chave_mock",
            model_name="gemini-3.8-flash",
            target_repo=tmpdir,
            auto_approve=True,
        )
        assert harness.target_repo == str(Path(tmpdir).resolve())
        assert harness.auto_approve is True
        assert harness.model_name == "gemini-3.8-flash"
        assert "git_status" in harness.tools_map
        assert "apply_patch" in harness.tools_map
        assert "search_runbooks" in harness.tools_map


def test_execute_tool_success():
    """Valida execução bem-sucedida de ferramenta via harness."""
    with tempfile.TemporaryDirectory() as tmpdir:
        (Path(tmpdir) / "app.py").touch()
        harness = DevSREHarness(target_repo=tmpdir)

        result = harness.execute_tool("list_directory", {"relative_path": "."})
        assert "app.py" in result


def test_execute_tool_unknown_tool():
    """Valida mensagem de erro ao requisitar ferramenta inexistente."""
    harness = DevSREHarness()
    result = harness.execute_tool("ferramenta_inexistente_xyz", {})
    assert "Erro: Ferramenta 'ferramenta_inexistente_xyz' não existe" in result


def test_execute_tool_parameter_error():
    """Valida captura limpa de TypeError em argumentos de ferramentas."""
    harness = DevSREHarness()
    result = harness.execute_tool("read_file", {"argumento_invalido": 123})
    assert "Erro de parâmetro na chamada da ferramenta" in result


def test_execute_tool_truncates_long_output():
    """Valida que saídas longas de ferramentas sejam truncadas respeitando o limite."""
    with tempfile.TemporaryDirectory() as tmpdir:
        big_file = Path(tmpdir) / "long.txt"
        big_file.write_text("A" * 7000, encoding="utf-8")

        harness = DevSREHarness(target_repo=tmpdir)
        # Mock temporário no catálogo para testar a truncagem diretamente
        harness.tools_map["mock_long"] = lambda: "Linha de log\n" * 600

        result = harness.execute_tool("mock_long", {})
        assert len(result) <= MAX_TOOL_OUTPUT_LENGTH + 200
        assert "[Saída truncada pelo Harness para preservar contexto]" in result


def test_generate_structured_rca_fallback():
    """Valida geração do relatório estruturado Pydantic no modo offline/fallback."""
    harness = DevSREHarness(api_key="")
    diagnosis_text = "Incidente de autenticação: token expirado sem cabeçalho X-Token-Expired."
    report = harness.generate_structured_rca(diagnosis_text)

    assert isinstance(report, RootCauseAnalysisReport)
    assert report.severity in ["BAIXA", "MEDIA", "ALTA", "CRITICA"]
    assert len(report.culprit_files) > 0
    assert len(report.prevention_steps) > 0
    assert harness.last_rca_report == report


def test_call_with_retry_fails_fast_on_auth_error():
    """Garante que erros de autenticação não causem loops infinitos de retry."""
    attempts = 0

    def fail_auth():
        nonlocal attempts
        attempts += 1
        raise ValueError("API_KEY_INVALID: credentials rejected 401")

    with pytest.raises(ValueError) as exc_info:
        _call_with_retry(fail_auth, max_retries=3, initial_delay=0.01)

    assert "API_KEY_INVALID" in str(exc_info.value)
    assert attempts == 1  # Falha imediatamente no primeiro attempt!


def test_call_with_retry_succeeds_after_transient_error():
    """Garante resiliência com sucesso após falha temporária de rede."""
    attempts = 0

    def transient_call():
        nonlocal attempts
        attempts += 1
        if attempts < 2:
            raise ConnectionResetError("Connection reset by peer")
        return "sucesso_resiliente"

    result = _call_with_retry(transient_call, max_retries=3, initial_delay=0.01)
    assert result == "sucesso_resiliente"
    assert attempts == 2
