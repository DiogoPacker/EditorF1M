# F1 Save Studio

Editor local de saves do **F1 Manager 2024**, com API FastAPI e interface web em português. Consulte sua carreira, planeje contratos e exporte uma nova cópia do save.

Desenvolvido por **Diogo Packer Elias** · [LinkedIn](https://www.linkedin.com/in/diogo-packer-elias-11a3b7b6/) · [GitHub](https://github.com/DiogoPacker)

## Recursos

- Grid atual e projetado para a próxima temporada, com cores por equipe.
- Hub de contratos ao clicar em qualquer piloto: vínculos atuais, futuros, equipe, função, salário e duração.
- Titulares dos carros 1/2 e academia sem limite fixo de integrantes no editor.
- Transferências com prévia de quem sai; promoção de F2/F3 e arrastar/soltar.
- Atributos editáveis e comparação em linhas e radar.
- Ordenação por categoria, média dos atributos ou nome.
- Desempenho estimado do carro, evolução dos designs e edição das peças instaladas.
- Perfis de motor e seleção de clientes em saves com suporte Sector33.
- Histórico de corridas e sprints, calendário, finanças, projetos e pesquisa.
- Histórico de alterações, desfazer e exportação com verificação estrutural.
- Menu horizontal, controles −/+ e tamanho de letras ajustável.

## Instalação

Requer Python com SQLite `serialize/deserialize`. Desenvolvimento e testes locais realizados com Python 3.14 no Windows. Node é necessário apenas para os testes JavaScript.

```powershell
git clone https://github.com/DiogoPacker/EditorF1M.git
cd EditorF1M
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

Abra **http://127.0.0.1:8000**. A documentação da API está em **/docs** e o contrato OpenAPI em **/openapi.json**.

Não é necessário ativar a venv. Para encerrar, use Ctrl+C. Se a porta estiver ocupada, encerre o servidor anterior ou escolha outra:

```powershell
$env:F1_PORT = '8001'
.\.venv\Scripts\python.exe app.py
```

Em Linux/macOS, use `python3 -m venv .venv` e `.venv/bin/python` nos comandos equivalentes.

## Como usar

1. Abra um arquivo `.sav` ou SQLite compatível.
2. Selecione a tela e faça suas alterações.
3. Clique em **Aplicar à cópia**. Campos ainda não aplicados não entram na exportação.
4. Confira o histórico ou use **Desfazer**.
5. Clique em **Exportar novo save** e salve o arquivo baixado em outro slot.

O original enviado nunca é sobrescrito. SQLite isolado só pode ser exportado como SQLite: faltam os metadados necessários para gerar um save GVAS.

### Planejar um contrato futuro

Clique no nome do piloto em **Grid e transferências**, inclusive na academia ou na lista de entrada. O hub mostra os vínculos atuais e futuros. Escolha a próxima temporada, equipe e função, confira o novo contrato e aplique.

A contratação futura mantém o grid atual e ajusta os vínculos conflitantes quando necessário. Para titular, a prévia informa quem será substituído. Cancelar um contrato futuro não prolonga automaticamente vínculos que foram encurtados; use desfazer para reverter a operação completa.

### Sessões e armazenamento

O app **não abre automaticamente o save da visita anterior**. Sempre escolha o arquivo que deseja editar. Preferências de equipe e fonte podem permanecer no navegador.

Cópias de trabalho e histórico são armazenados em `work/sessions/`, fora do Git. Cada checkpoint reúne banco e histórico em um único arquivo substituído atomicamente. Edições e desfazer restauram o estado anterior se a persistência falhar.

O desfazer mantém até **20 operações**, limitado também a **128 MiB de snapshots por sessão**. Um snapshot maior que esse limite não é retido. O histórico descritivo permanece, mas snapshots não são restaurados após reiniciar. O limite é de **8 sessões abertas por processo**; exporte e reinicie para liberar memória. Arquivos em disco não são apagados automaticamente.

## Arquitetura

```text
app.py / run.py                 inicialização local
teams.py                        identidade visual das equipes
backend/
  main.py                       montagem do FastAPI, middleware e ciclo de vida
  api/
    dependencies.py             acesso às sessões e tradução de sessão inexistente
    routes/
      saves.py                  importação, exportação e desfazer
      drivers.py                pilotos e edição de contratos
      teams.py                  equipes e finanças
      calendar.py               calendário e clima
      performance.py            desempenho e evolução
      parts.py                  projetos, peças e expertise
      editor.py                 transferências, academia, motores e records
      inspection.py             inspeção técnica de tabelas
  application/
    editing.py                  casos de uso de edição de campos
    services.py                 consultas e cálculos compartilhados
    roster.py                   grid, transferências e contratos
    engines.py                  perfis e clientes de motores
    car_editor.py               edição em lote de peças instaladas
    records.py                  histórico de corridas
  domain/
    errors.py                   erros independentes do HTTP
  infrastructure/
    codec.py                    GVAS, zlib, SQLite e verificação da exportação
    workspace.py                transações, snapshots e checkpoints
    repositories/
      edits.py                  persistência dos campos editáveis
  models.py                     entradas tipadas e limites Pydantic
frontend/
  app.js                        composição das telas, navegação e estado da UI
  api.js                        cliente HTTP
  features/                     grid, contratos, comparação, engenharia e histórico
  charts.js                     gráficos SVG
  drivers.js                    categorias e ordenação compartilhada
  controls.js                   controles numéricos
  preferences.js                preferências de leitura
  *.css / index.html            tema, estrutura e responsividade
tests/                          testes Python e JavaScript
docs/architecture.md            decisões e limites da arquitetura
.github/workflows/tests.yml     verificação em push e pull request
```

A organização é modular e orientada a funcionalidades. Usa casos de uso, um adaptador de persistência para edições e uma unidade de trabalho com snapshots. O SQL específico de leitura e das operações complexas permanece próximo da funcionalidade que atende. Não há ORM ou framework de injeção de dependências.

O backend executa operações síncronas em rotas síncronas, atendidas pelo pool de threads. A importação desloca o processamento do save para o pool. Requisições de uma sessão são serializadas no processo para evitar leituras durante uma edição.

## API

| Método | Rota | Operação |
|---|---|---|
| GET | /api/health | Saúde e versão |
| POST | /api/saves | Importar; multipart no campo file, até 64 MiB |
| GET | /api/saves/{id} | Metadados e alterações |
| POST | /api/saves/{id}/undo | Desfazer |
| POST | /api/saves/{id}/export?format=sav | Exportar; aceita também format=sqlite |
| GET/PATCH | /api/saves/{id}/drivers/{driver} | Consultar/editar piloto |
| PATCH | /api/saves/{id}/contracts/{contract} | Salário, bônus e duração |
| GET | /api/saves/{id}/grid?year=2027 | Grid atual ou próximo |
| POST | /api/saves/{id}/transfers/preview | Conferir transferência |
| POST | /api/saves/{id}/transfers | Aplicar com expected_outgoing |
| POST | /api/saves/{id}/teams/{team}/academy | Contratar para academia |
| GET/PATCH | /api/saves/{id}/teams/{team}/fitted?car=1 | Peças instaladas |
| GET | /api/saves/{id}/records?season=2026 | Histórico da temporada |

Consulte **/docs** para todas as rotas e campos. GET consulta; PATCH edita; POST executa operações; DELETE remove vínculos específicos. Respostas 404 indicam recurso inexistente e 422 indicam entrada inválida ou operação incompatível.

## Testes

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
node scripts/test-frontend.mjs
```

Para integrar com um save real, defina uma variável local. O arquivo indicado é apenas lido e os testes trabalham em cópias temporárias:

```powershell
$env:F1_TEST_SAVE = 'C:\caminho\save.sav'
.\.venv\Scripts\python.exe -m pytest -q
$env:PYTHONPATH = '.'
.\.venv\Scripts\python.exe tests/build_ui_fixture.py
node scripts/test-frontend.mjs
```

Sem o save/fixture, testes dependentes desses dados são ignorados. A CI executa os testes independentes de arquivos privados. Os testes de componentes não substituem conferência visual ou validação dentro do jogo.

## Compatibilidade e limites

- O codec preserva prefixo, segmentos auxiliares e sufixo do save, remonta o bloco comprimido e reabre a exportação. O SQLite passa por `integrity_check`.
- O usuário confirmou carregamento de exportações no jogo; isso não garante todas as combinações de edição e mods. Preserve um backup.
- Os atributos agregados do carro e sua evolução são **estimativas do editor**. O histórico usa designs concluídos antes de cada GP, não peças comprovadamente instaladas naquela corrida.
- A média exibida para pilotos **não é o overall oficial**.
- Racing Bulls, Audi e Cadillac são nomes de apresentação; os nomes originais do banco são preservados.
- Motores personalizados dependem das tabelas Sector33 e não criam novas marcas nativas do jogo.
- Academia sem limite fixo no editor não garante suporte ilimitado da interface ou dos mods do jogo.
- O calendário permite editar clima/temperatura futuros; não adiciona nem reordena etapas.
- Não há paridade completa com o Database Editor.

## GitHub e hospedagem

O repositório inclui código, testes e documentação. `.venv/`, `work/`, saves, bancos, caches, logs e arquivos `.env` ficam fora do Git. Não envie saves ou credenciais em issues, commits ou pull requests.

Publicar o código no GitHub é diferente de disponibilizar o editor na internet. Esta versão é para **uso individual local**, sem login ou autorização por usuário. O ID da sessão não substitui autenticação.

Execute com **um único worker/processo**. O gerenciador de sessões vive em memória e não coordena múltiplos processos. Um serviço público precisa de autenticação, autorização, quotas, política de expiração e armazenamento apropriado; não basta trocar o endereço de escuta.

## Referências

A organização das telas foi inspirada no [Database Editor de IUrreta](https://github.com/IUrreta/DatabaseEditor). O projeto usa [FastAPI](https://fastapi.tiangolo.com/), Uvicorn, Python, SQLite e SVG. Não inclui saves nem recursos gráficos extraídos do jogo e não é um produto oficial da Frontier ou da Formula 1.
