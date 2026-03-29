# PROJECT_CONTEXT.md

## Proposito
Resumo executivo para retomada rapida apos pausas e para onboarding de novos contribuidores.

## Fontes Autoritativas
- `AGENTS.md`
- `openspec/specs/`
- `docs/adr/`
- `docs/releases/`
- Em caso de conflito: specs/artefatos mais recentes no Git prevalecem.

## Objetivo do Sistema
Definir objetivo de negocio e comportamento principal do sistema.

## Arquitetura de Alto Nivel
- **docs** (docs): Documentacao e rastreabilidade.
- **scripts** (scripts): Automacoes e utilitarios.
- **tests** (tests): Suite de testes automatizados.

## Regras Nao Negociaveis
- Nao quebrar contratos publicos de API sem mudanca versionada.
- Toda mudanca relevante deve deixar evidencia no Git (spec/task/commit).

## Quality Bar
- Testes relevantes executam localmente antes de merge.
- Lint e checks estaticos sem erros criticos.
- Mudancas com risco medio/alto devem ter plano de rollback.
- Build de pacote/app deve permanecer reprodutivel.

<!-- generated-by: project-context-maintainer -->
