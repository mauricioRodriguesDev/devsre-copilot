# Runbook: Conexão com Banco de Dados e Pool de Conexões

## 1. Arquitetura de Conexão
Nossa aplicação utiliza SQLAlchemy com pool assíncrono (AsyncEngine). O tamanho padrão do pool (`pool_size`) é 10, com limite máximo de overflow (`max_overflow`) de 20 conexões.

## 2. Sintomas Comuns de Incidente
* **TimeoutError: QueuePool limit of size 10 overflow 20 reached:**
  * Ocorre quando conexões não são fechadas apropriadamente após queries.
  * Solução imediata: Verificar se os handlers estão utilizando o context manager `async with get_db_session() as session:`.
  * Nunca utilizar `session.close()` manualmente sem bloco `finally` ou context manager.

## 3. Configurações de Retry
Para falhas transitórias de rede, o cliente do banco deve ter backoff exponencial configurado com no máximo 3 tentativas e jitter de 100ms a 500ms.
