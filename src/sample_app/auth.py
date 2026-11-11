"""Módulo simulado de autenticação para servir de laboratório de incidentes."""

class AuthResponse:
    def __init__(self, status_code: int, body: dict, headers: dict = None):
        self.status_code = status_code
        self.body = body
        self.headers = headers or {}


def authenticate_request(token: str) -> AuthResponse:
    """Valida o token JWT recebido na requisição.
    
    NOTA: Este código contém intencionalmente um bug comum de incidente:
    quando o token é 'expired_token', ele retorna status 401, mas esquece de
    adicionar o cabeçalho 'X-Token-Expired: true' exigido pelo runbook da empresa!
    """
    if not token:
        return AuthResponse(401, {"error": "token_missing"})
    
    if token == "expired_token":
        # BUG: Faltando o header exigido 'X-Token-Expired': 'true'
        return AuthResponse(
            status_code=401,
            body={"error": "token_expired", "message": "O token fornecido expirou."}
        )
    
    if token == "valid_token":
        return AuthResponse(200, {"user_id": "usr_42", "role": "developer"})
        
    return AuthResponse(403, {"error": "invalid_signature"})
