# AGENTS.md

## 1. Stack e Versoes
- Linguagens: Python
- Python: >=3.12

## 2. Comandos de Validacao (Quality Gate)
- Testes: `python3 -m pytest -q`
- Build: `python3 -m build`

## 3. Comandos Essenciais (Operacao Local)
### Setup
```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e .
```

### Rodar local
```bash
python3 -m <seu_modulo_principal>
```

### Testes rapidos
```bash
python3 -m pytest -q tests/unit
```

### Testes completos
```bash
python3 -m pytest -q
```


## 4. Arquitetura e Constraints
- Organizar logica por modulo/cohesao; evitar funcoes gigantes.

## 5. Politica de Testes
- TDD obrigatorio: RED (teste falha) -> GREEN (minimo para passar) -> REFACTOR (limpeza sem quebrar).
- Nao iniciar implementacao sem primeiro teste falhando para o comportamento-alvo.
- Priorizar testes unitarios; usar integracao para contratos e fluxos.
- Ao tocar legado sem testes, adicionar ao menos um teste de caracterizacao.

## 6. Stop Rule (CRUCIAL)
- Implementar uma task slice vertical por vez (end-to-end).
- Nao quebrar o trabalho em slice horizontal por camada sem entrega de fluxo completo.
- Antes de codar o change: design.md e obrigatorio, exceto QUICK de bugfix simples e reversivel.
- Rodar comandos de validacao da secao 2.
- Atualizar tasks/specs com o status do slice.
- Fazer commit com mensagem rastreavel e dar push para branch remota.
- PARAR e pedir confirmacao explicita para o proximo slice.
- Nao iniciar o proximo slice sem confirmacao explicita do usuario.

## 7. Definition of Done (DoD)
- [ ] Build/check sem erros
- [ ] Testes relevantes passando
- [ ] Lint/type-check sem erros relevantes
- [ ] Specs/docs atualizadas quando necessario
- [ ] Commit com mensagem clara e rastreavel
- [ ] Push realizado para branch remota

## 8. Anti-patterns Proibidos
- Nao criar classes/funcoes God object com responsabilidades demais.
- Nao deixar TODO/FIXME sem issue ou plano.
- Nao acoplar regras de negocio em camada de apresentacao.
- Nao executar slices horizontais por camada sem valor end-to-end.
- Nao introduzir side effects globais invisiveis em import-time.

## 9. Prompt de Reentrada
```text
Read AGENTS.md and PROJECT_CONTEXT.md first.
Implement ONLY the next incomplete slice from tasks/spec.
Use vertical slicing (end-to-end); avoid horizontal slicing by layer.
Follow TDD cycle: RED (failing test) -> GREEN (minimal pass) -> REFACTOR (clean safely).
If the active change is not a simple QUICK bugfix, require design.md before implementation.
Run section 2 validation commands and update artifacts for the completed slice.
Commit and push the current branch.
STOP and ask for explicit confirmation before starting the next slice.
```

<!-- generated-by: agents-md-generator -->
