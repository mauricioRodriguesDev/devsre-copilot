"""Testes unitários para as ferramentas de arquivo e repositório do MCP Server."""

import tempfile
from pathlib import Path
from src.mcp_server.server import (
    list_directory,
    read_file,
    apply_patch,
    run_tests,
    read_application_logs,
    sanitize_sensitive_data,
)


def test_list_directory():
    with tempfile.TemporaryDirectory() as tmpdir:
        (Path(tmpdir) / "app.py").touch()
        (Path(tmpdir) / "src").mkdir()

        output = list_directory(repo_path=tmpdir)
        assert "app.py" in output
        assert "src/" in output


def test_read_file_with_lines():
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = Path(tmpdir) / "sample.py"
        file_path.write_text("line 1\nline 2\nline 3\nline 4\n", encoding="utf-8")

        output = read_file(file_path="sample.py", start_line=2, line_count=2, repo_path=tmpdir)
        assert "2 | line 2" in output
        assert "3 | line 3" in output
        assert "line 1" not in output


def test_apply_patch_success():
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = Path(tmpdir) / "code.py"
        file_path.write_text('status = "error"\n', encoding="utf-8")

        result = apply_patch(
            file_path="code.py",
            search_block='status = "error"',
            replace_block='status = "ok"',
            repo_path=tmpdir,
            auto_approve=True,
        )
        assert "Sucesso" in result
        assert file_path.read_text(encoding="utf-8") == 'status = "ok"\n'


def test_apply_patch_blocks_in_headless_without_approval():
    """Garante que execução sem terminal interativo bloqueie patches se auto_approve for False."""
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = Path(tmpdir) / "code.py"
        file_path.write_text('status = "error"\n', encoding="utf-8")

        result = apply_patch(
            file_path="code.py",
            search_block='status = "error"',
            replace_block='status = "ok"',
            repo_path=tmpdir,
            auto_approve=False,
        )
        assert "Proteção de Segurança: execução em ambiente não-interativo requer flag auto_approve=True" in result
        # Confirma que o arquivo NÃO foi alterado
        assert file_path.read_text(encoding="utf-8") == 'status = "error"\n'


def test_apply_patch_interactive_rejection(monkeypatch):
    """Simula um desenvolvedor rejeitando o patch com 'n' no terminal interativo."""
    import sys
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda prompt: "n")

    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = Path(tmpdir) / "code.py"
        file_path.write_text('status = "error"\n', encoding="utf-8")

        result = apply_patch(
            file_path="code.py",
            search_block='status = "error"',
            replace_block='status = "ok"',
            repo_path=tmpdir,
            auto_approve=False,
        )
        assert "Operação cancelada pelo desenvolvedor" in result
        assert file_path.read_text(encoding="utf-8") == 'status = "error"\n'


def test_apply_patch_interactive_approval(monkeypatch):
    """Simula um desenvolvedor aprovando o patch com 's' no terminal interativo."""
    import sys
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda prompt: "s")

    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = Path(tmpdir) / "code.py"
        file_path.write_text('status = "error"\n', encoding="utf-8")

        result = apply_patch(
            file_path="code.py",
            search_block='status = "error"',
            replace_block='status = "ok"',
            repo_path=tmpdir,
            auto_approve=False,
        )
        assert "Sucesso: patch aplicado com êxito" in result
        assert file_path.read_text(encoding="utf-8") == 'status = "ok"\n'


def test_apply_patch_not_found():
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = Path(tmpdir) / "code.py"
        file_path.write_text('status = "error"\n', encoding="utf-8")

        result = apply_patch(
            file_path="code.py",
            search_block='status = "missing_block"',
            replace_block='status = "ok"',
            repo_path=tmpdir,
        )
        assert "Erro de correspondência" in result


# --- TESTES DE SEGURANÇA (ANTI-PATH TRAVERSAL) ---

def test_read_file_blocks_relative_traversal():
    """Garante que sequências '../' sejam bloqueadas ao tentar ler arquivos fora da raiz."""
    with tempfile.TemporaryDirectory() as tmpdir:
        result = read_file(file_path="../../etc/passwd", repo_path=tmpdir)
        assert "Segurança: tentativa de Path Traversal detectada" in result


def test_read_file_blocks_absolute_path():
    """Garante que caminhos absolutos do sistema sejam bloqueados."""
    with tempfile.TemporaryDirectory() as tmpdir:
        result = read_file(file_path="C:/Windows/win.ini", repo_path=tmpdir)
        assert "Segurança: caminhos absolutos ou com unidade não são permitidos" in result


def test_apply_patch_blocks_traversal():
    """Garante que apply_patch não modifique arquivos fora da raiz do repositório."""
    with tempfile.TemporaryDirectory() as tmpdir:
        result = apply_patch(
            file_path="../outside.py",
            search_block="a = 1",
            replace_block="a = 2",
            repo_path=tmpdir,
        )
        assert "Segurança:" in result


def test_list_directory_blocks_traversal():
    """Garante que list_directory não liste diretórios superiores do sistema."""
    with tempfile.TemporaryDirectory() as tmpdir:
        result = list_directory(relative_path="../../..", repo_path=tmpdir)
        assert "Segurança:" in result


def test_read_logs_blocks_traversal():
    """Garante que read_application_logs não leia logs fora do repositório."""
    with tempfile.TemporaryDirectory() as tmpdir:
        result = read_application_logs(log_file="../system.log", repo_path=tmpdir)
        assert "Segurança:" in result


# --- TESTES DE SEGURANÇA (REDACTION DE SEGREDOS) ---

def test_sanitize_sensitive_data_masks_credentials():
    """Valida a substituição de segredos (chaves de API, senhas de banco e tokens JWT)."""
    raw = (
        "Erro ao conectar com postgresql://postgres:super_secret_password_123@localhost:5432/mydb\n"
        "Chave de api: AIzaSyA1B2C3D4E5F6G7H8I9J0K1L2M3N4O5P6\n"
        "Header recebido: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.doNotLeakThisSignature\n"
        "Configuracao: password='my_db_password_xyz'\n"
    )
    sanitized = sanitize_sensitive_data(raw)
    assert "super_secret_password_123" not in sanitized
    assert "[REDACTED_PASSWORD]" in sanitized
    assert "AIzaSyA1B2C3D4E5F6G7H8I9J0K1L2M3N4O5P6" not in sanitized
    assert "[REDACTED_GOOGLE_KEY]" in sanitized
    assert "doNotLeakThisSignature" not in sanitized
    assert "[REDACTED_JWT_TOKEN]" in sanitized
    assert "my_db_password_xyz" not in sanitized
    assert "[REDACTED_SECRET]" in sanitized


def test_read_application_logs_redacts_secrets_in_file():
    """Garante que logs lidos em disco tenham segredos mascarados antes de retornar."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_path = Path(tmpdir) / "app.log"
        log_path.write_text("Failed login with token Bearer secret_access_token_123456789\n", encoding="utf-8")

        result = read_application_logs(log_file="app.log", repo_path=tmpdir)
        assert "secret_access_token_123456789" not in result
        assert "[REDACTED_BEARER_TOKEN]" in result


def test_sanitize_sensitive_data_masks_complex_passwords():
    """Valida redação de senhas com caracteres especiais (@, #, $, !)."""
    raw = "database_config: password='P@ssw0rd!#$*' auth_token='SecretKey!999#.'"
    sanitized = sanitize_sensitive_data(raw)
    assert "P@ssw0rd!#$*" not in sanitized
    assert "SecretKey!999#." not in sanitized
    assert "[REDACTED_SECRET]" in sanitized


def test_run_tests_blocks_argument_injection():
    """Garante que flags e opções do pytest sejam bloqueadas em test_path."""
    with tempfile.TemporaryDirectory() as tmpdir:
        res1 = run_tests(test_path="-o cache_dir=/tmp", repo_path=tmpdir)
        assert "Segurança: opções e flags de linha de comando não são permitidas" in res1

        res2 = run_tests(test_path="--override-ini=cache_dir=/tmp", repo_path=tmpdir)
        assert "Segurança: opções e flags de linha de comando não são permitidas" in res2


def test_run_tests_blocks_path_traversal():
    """Garante que test_path não possa apontar para arquivos fora do repositório."""
    with tempfile.TemporaryDirectory() as tmpdir:
        result = run_tests(test_path="../../external_test.py", repo_path=tmpdir)
        assert "Segurança: tentativa de Path Traversal detectada" in result


def test_read_file_blocks_drive_relative_path():
    """Garante que caminhos com letra de unidade (ex: C:foo) sejam bloqueados no Windows."""
    with tempfile.TemporaryDirectory() as tmpdir:
        result = read_file(file_path="C:malicious.py", repo_path=tmpdir)
        assert "Segurança:" in result


