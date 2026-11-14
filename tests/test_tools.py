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
    detect_project_ecosystem,
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


def test_read_and_patch_block_sensitive_dotfiles():
    """Garante que .env, .git e chaves privadas sejam estritamente bloqueados contra leitura e escrita."""
    with tempfile.TemporaryDirectory() as tmpdir:
        (Path(tmpdir) / ".env").write_text("SECRET_KEY=123456\n", encoding="utf-8")
        git_dir = Path(tmpdir) / ".git"
        git_dir.mkdir()
        (git_dir / "config").write_text("[core]\n", encoding="utf-8")

        # 1. Leitura bloqueada em .env
        res_read_env = read_file(file_path=".env", repo_path=tmpdir)
        assert "Segurança: acesso a arquivos ou diretórios protegidos/sensíveis não é permitido" in res_read_env

        # 2. Patch bloqueado em .env
        res_patch_env = apply_patch(
            file_path=".env",
            search_block="SECRET_KEY=123456",
            replace_block="SECRET_KEY=hacked",
            repo_path=tmpdir,
            auto_approve=True,
        )
        assert "Segurança: acesso a arquivos ou diretórios protegidos/sensíveis não é permitido" in res_patch_env

        # 3. Leitura e patch bloqueados em .git/
        res_read_git = read_file(file_path=".git/config", repo_path=tmpdir)
        assert "Segurança: acesso a arquivos ou diretórios protegidos/sensíveis não é permitido" in res_read_git

        res_patch_git = apply_patch(
            file_path=".git/config",
            search_block="[core]",
            replace_block="[hacked]",
            repo_path=tmpdir,
            auto_approve=True,
        )
        assert "Segurança: acesso a arquivos ou diretórios protegidos/sensíveis não é permitido" in res_patch_git


def test_sanitize_sensitive_data_masks_modern_google_aq_keys():
    """Valida redação de novas chaves Google AI Studio com prefixo AQ."""
    raw = "gemini_key = 'AQ.FakeExampleKeyForTestingPurposesOnly1234567890'"
    sanitized = sanitize_sensitive_data(raw)
    assert "AQ.FakeExampleKeyForTestingPurposesOnly1234567890" not in sanitized
    assert "[REDACTED_GOOGLE_KEY]" in sanitized


def test_read_file_blocks_oversized_files():
    """Garante que arquivos com mais de 5MB sejam rejeitados para evitar estouro de memória."""
    with tempfile.TemporaryDirectory() as tmpdir:
        big_file = Path(tmpdir) / "huge_data.bin"
        # Cria arquivo esparso ou com 5.5MB
        with open(big_file, "wb") as f:
            f.seek(6 * 1024 * 1024)
            f.write(b"\0")

        result = read_file(file_path="huge_data.bin", repo_path=tmpdir)
        assert "Segurança: arquivo excede o limite máximo permitido de 5MB" in result


# --- TESTES DE DETECÇÃO MULTI-LINGUAGEM (POLYGLOT ENGINE) ---

def test_list_directory_ignores_multilanguage_build_folders():
    """Garante que pastas de build/dependências de Java, Node e Rust sejam ignoradas na listagem."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)
        (base / "src").mkdir()
        (base / "node_modules").mkdir()
        (base / "target").mkdir()
        (base / "dist").mkdir()
        (base / "App.java").touch()

        output = list_directory(repo_path=tmpdir)
        assert "src/" in output
        assert "App.java" in output
        assert "node_modules" not in output
        assert "target" not in output
        assert "dist" not in output


def test_detect_project_ecosystem_maven():
    """Valida detecção de projetos Java baseados em Maven (pom.xml)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)
        (base / "pom.xml").write_text("<project></project>", encoding="utf-8")
        (base / "mvnw.cmd").touch()

        name, cmd, err = detect_project_ecosystem(base, clean_test="com.empresa.AuthTest")
        assert name == "Maven (Java)"
        assert err is None
        assert "test" in cmd
        assert "-Dtest=com.empresa.AuthTest" in cmd


def test_detect_project_ecosystem_gradle():
    """Valida detecção de projetos Java/Kotlin baseados em Gradle (build.gradle)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)
        (base / "build.gradle").write_text("plugins {}", encoding="utf-8")
        (base / "gradlew.bat").touch()

        name, cmd, err = detect_project_ecosystem(base, clean_test="AuthTest")
        assert name == "Gradle (Java/Kotlin)"
        assert err is None
        assert "test" in cmd
        assert "--tests" in cmd
        assert "AuthTest" in cmd


def test_detect_project_ecosystem_node():
    """Valida detecção de projetos JavaScript/TypeScript (package.json)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)
        (base / "package.json").write_text('{"name": "app"}', encoding="utf-8")

        name, cmd, err = detect_project_ecosystem(base, clean_test="auth.test.ts")
        assert "Node.js" in name
        if cmd is not None:
            assert "test" in cmd
            assert "auth.test.ts" in cmd


def test_detect_project_ecosystem_go():
    """Valida detecção de projetos Go (go.mod)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)
        (base / "go.mod").write_text("module meuapp\n", encoding="utf-8")

        name, cmd, err = detect_project_ecosystem(base)
        assert name == "Go"


def test_detect_project_ecosystem_rust():
    """Valida detecção de projetos Rust (Cargo.toml)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)
        (base / "Cargo.toml").write_text("[package]\nname='meuapp'\n", encoding="utf-8")

        name, cmd, err = detect_project_ecosystem(base)
        assert name == "Rust (Cargo)"


def test_detect_project_ecosystem_python_default():
    """Valida detecção padrão para projetos Python."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)
        (base / "app.py").touch()

        name, cmd, err = detect_project_ecosystem(base)
        assert name == "Python (pytest)"
        assert "pytest" in cmd




