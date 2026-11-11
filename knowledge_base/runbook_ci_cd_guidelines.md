# Diretrizes de CI/CD e Padrões de Código

## 1. Padrão de Mensagens de Commit (Conventional Commits)
Todos os commits devem seguir a convenção:
`<tipo>(<escopo>): <descrição em imperativo>`
* Exemplos:
  * `feat(auth): add refresh token endpoint`
  * `fix(db): release connection on query timeout`
  * `test(auth): add edge case for expired jwt token`

## 2. Padrão de Relatórios de RCA (Root Cause Analysis / Post-Mortem)
Sempre que uma falha for diagnosticada, o relatório gerado deve seguir as seções:
1. **Resumo do Incidente:** O que aconteceu e impacto.
2. **Causa Raiz Identificada:** Explicação técnica do bug.
3. **Código Culpado vs. Código Corrigido:** Diferença precisa no código.
4. **Validação:** Qual teste comprova que a correção funciona.
5. **Prevenção:** Ação preventiva de longo prazo.
