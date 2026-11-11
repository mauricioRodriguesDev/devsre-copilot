"""Testes unitários para as ferramentas de arquivo e repositório do MCP Server."""

import tempfile
from pathlib import Path
from src.mcp_server.server import list_directory, read_file, apply_patch, read_application_logs


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
        )
        assert "Sucesso" in result
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
        assert "Segurança: caminhos absolutos não são permitidos" in result


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
