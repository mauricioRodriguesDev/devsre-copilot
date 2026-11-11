# Runbook: Serviço de Autenticação & Validação de JWT

## 1. Visão Geral
O serviço de autenticação utiliza JSON Web Tokens (JWT) assinados via HMAC-SHA256 com chaves rotativas. Todas as rotas protegidas passam pelo middleware `AuthMiddleware`.

## 2. Códigos de Erro e Padrões da Empresa
* **401 Unauthorized:** Emitido quando o token estiver ausente, com assinatura inválida ou **expirado**.
  * **Regra Obrigatória:** Em caso de token expirado (`TokenExpiredSignatureError`), a resposta **DEVE** incluir obrigatoriamente o cabeçalho HTTP:
    ```http
    X-Token-Expired: true
    ```
    E o corpo em JSON:
    ```json
    {"error": "token_expired", "message": "O token fornecido expirou. Solicite um refresh token."}
    ```
* **403 Forbidden:** Emitido quando o usuário está autenticado, mas seu `role` não tem permissão para a rota.

## 3. Erro Frequente em Testes Unitários
Quando o teste `tests/test_auth.py` falhar com `AssertionError: Header 'X-Token-Expired' is missing`, a causa mais comum é que o interceptor de exceção `AuthMiddleware.handle_expired_token` foi modificado ou retornou um `Response` sem injetar o cabeçalho customizado.
