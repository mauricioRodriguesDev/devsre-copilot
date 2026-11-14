# Runbook de Modernização de Aplicações Java e Resolução de Depreciações

Este documento estabelece os padrões obrigatórios de engenharia e os procedimentos de modernização de código legado e resolução de depreciações em aplicações **Java / Spring Boot** mantidas pela organização.

---

## 1. Diretrizes de Migração de Versão (Java 8/11 para Java 17/21)

Todas as novas versões de microsserviços corporativos devem ter como alvo mínimo o **Java 17 LTS** ou preferencialmente o **Java 21 LTS**.

### Padrões de Linguagem Modernos Obrigatórios:
* **Records:** Utilizar `record` em substituição a DTOs anêmicos com getters/setters repetitivos ou dependência excessiva do Lombok `@Data`.
* **Pattern Matching para `instanceof`:** Substituir casting manual pelo bind direto:
  ```java
  // Padrão legado
  if (obj instanceof String) {
      String s = (String) obj;
      System.out.println(s.toLowerCase());
  }

  // Padrão moderno
  if (obj instanceof String s) {
      System.out.println(s.toLowerCase());
  }
  ```
* **Text Blocks:** Utilizar blocos de texto multilinha com `"""` para queries SQL, schemas JSON e templates Markdown, eliminando concatenações manuais com `+` ou `\n`.
* **Switch Expressions:** Utilizar expressões de switch com arrow `->` exaustivas, eliminando comandos `break` propensos a bugs de fall-through.

---

## 2. Tratamento de Métodos e Classes Depreciadas (@Deprecated)

Quando o compilador ou analisador estático (SonarQube/SpotBugs) acusar o uso de APIs depreciadas:

1. **Inspeção do Javadoc:** Verificar o `@deprecated` no Javadoc do método para identificar a API substituta recomendada pelo fornecedor.
2. **Eliminação Imediata:** Não utilizar `@SuppressWarnings("deprecation")` para mascarar avisos a menos que não haja alternativa disponível em bibliotecas de terceiros.
3. **Compilação com Verificação Estrita:**
   * **No Maven:** Executar `mvn clean compile -Xlint:deprecation` para listar cada linha e método obsoleto.
   * **No Gradle:** Executar `gradle compileJava --warning-mode all`.

---

## 3. Migração de Pacotes javax.* para jakarta.* (Spring Boot 3 / Jakarta EE)

A transição para o Spring Boot 3 e Java 17+ exige a substituição completa dos pacotes `javax.*` que migraram para a especificação **Jakarta EE**:

| Pacote Depreciado (Legado) | Pacote Moderno Obrigatório | Módulo / Finalidade |
| :--- | :--- | :--- |
| `javax.persistence.*` | `jakarta.persistence.*` | JPA / Hibernate Entities |
| `javax.validation.*` | `jakarta.validation.*` | Bean Validation (`@NotNull`, `@Size`) |
| `javax.servlet.*` | `jakarta.servlet.*` | Servlet API e Filtros HTTP |
| `javax.annotation.*` | `jakarta.annotation.*` | Anotações comuns (`@PostConstruct`) |
| `javax.transaction.*` | `jakarta.transaction.*` | Transações JTA |

### Procedimento de Correção em `pom.xml`:
* Atualizar a dependência do `spring-boot-starter-parent` para `3.x.x`.
* Atualizar `spring-boot-starter-data-jpa` e `spring-boot-starter-validation`.
* Substituir os imports em todas as classes de entidade e controllers.

---

## 4. Substituição de Classes e Utilitários Legados

Classes utilitárias legadas da época do Java 1.0 a 1.4 devem ser refatoradas conforme a tabela abaixo:

* **`java.util.Date` e `java.util.Calendar`:**
  * Substituir por **`java.time.LocalDate`**, **`java.time.LocalDateTime`** ou **`java.time.Instant`** com formatação via `DateTimeFormatter`.
* **Coleções Sincronizadas Obsoletas (`Vector`, `Hashtable`):**
  * Substituir por `java.util.ArrayList`, `java.util.HashMap` ou alternativas concorrentes seguras (`java.util.concurrent.ConcurrentHashMap`).
* **Construtor de Tipos Primitivos Wrappers:**
  * Substituir `new Integer(10)` e `new Long(100L)` por `Integer.valueOf(10)` ou autoboxing direto `Integer val = 10;`.
* **`Thread.stop()`, `Thread.suspend()`, `Thread.resume()`:**
  * Estritamente proibidos por causarem corrupção de estado de locks e deadlocks. Utilizar flags atômicas (`AtomicBoolean`) ou cancelamento de `Future` / `ExecutorService`.

---

## 5. Modernização de Clientes HTTP e Chamadas REST

No ecossistema Spring:

* **`RestTemplate` (Modo de Manutenção):**
  * Não criar novas instâncias de `RestTemplate`.
  * Em projetos Spring Framework 6+ / Spring Boot 3+:
    * Para chamadas síncronas bloqueantes: Utilizar **`RestClient`**:
      ```java
      RestClient restClient = RestClient.create();
      UserDTO user = restClient.get()
          .uri("https://api.empresa.com/users/{id}", userId)
          .retrieve()
          .body(UserDTO.class);
      ```
    * Para chamadas reativas/não-bloqueantes: Utilizar **`WebClient`** (`spring-boot-starter-webflux`).

---

## 6. Procedimento de Diagnóstico e Compilação Automatizada

Ao investigar um projeto Java:
1. Inspecione o arquivo descritor de dependências (`pom.xml` ou `build.gradle`).
2. Execute a suíte de testes com a ferramenta `run_tests` para verificar a saúde do projeto.
3. Para compilar com detalhamento de depreciações, execute a compilação verificando saídas de logs sanitizados.
4. Aplique patches cirúrgicos com `apply_patch` substituindo os imports e métodos antigos.
5. Re-execute os testes para validar o Auto-Healing antes de gerar o relatório final de RCA.
