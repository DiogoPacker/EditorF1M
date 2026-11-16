# Decisões de arquitetura

## Fluxo de uma edição

1. A rota recebe uma entrada Pydantic e resolve a sessão.
2. O caso de uso verifica as regras da operação.
3. Workspace.change captura banco, histórico e snapshots anteriores.
4. A operação altera o SQLite dentro de uma transação.
5. Banco e histórico são gravados em um único checkpoint atômico.
6. Só uma operação concluída pode aparecer como aplicada. Em falha, o estado em memória é restaurado; o checkpoint anterior continua válido se a substituição falhar.

O arquivo original é armazenado separadamente e nunca é sobrescrito. Checkpoints antigos no formato working.sqlite + session.json continuam legíveis; a próxima gravação usa o formato novo. Um arquivo temporário interrompido não é considerado checkpoint válido.

## Responsabilidades

- api: HTTP, códigos de resposta, limites de upload e adaptação dos dados.
- application: operações do editor, coordenação e consultas por funcionalidade.
- domain: conceitos/erros que não dependem de FastAPI.
- infrastructure: formato binário, SQLite e armazenamento de sessões.
- frontend/features: comportamento das telas; o frontend nunca acessa SQLite diretamente.

Esta é uma arquitetura modular pragmática. Os serviços ainda conhecem o esquema específico do jogo; não se pretende uma implementação integral de Clean Architecture. O repositório de campos editáveis centraliza suas instruções SQL. Consultas e operações complexas de contratos/motores mantêm SQL especializado nos módulos de funcionalidade, evitando um repositório genérico que apenas repasse strings.

## Concorrência e ciclo de vida

Use um único processo Uvicorn. Requisições sob /api/saves/{id} são serializadas por um lock assíncrono do processo; a unidade de trabalho também usa RLock. Isso prioriza consistência no editor local, ao custo de serializar sessões distintas. Não é um lock distribuído.

Rotas de SQLite e compressão são síncronas para execução no pool de threads. O upload recebe o arquivo de forma assíncrona e desloca o processamento para o pool. O encerramento da aplicação fecha as conexões.

Até 8 sessões permanecem abertas por processo. O desfazer tem limites de quantidade e bytes. Dados em disco não são removidos automaticamente: a limpeza deve ocorrer com o servidor parado e após exportar o que se deseja manter. Um serviço público exigirá leases/expiração e quotas por usuário.

## Testes e evolução

Testes unitários cobrem falha de persistência, falha de desfazer, limites e reabertura do checkpoint. Integrações com save real cobrem edição, contratos, peças e exportação sem incluir o save no repositório. Testes JavaScript cobrem ordenação, gráficos e hub de contratos.

Mudanças estruturais preservam os endpoints HTTP existentes. A etapa seguinte para hospedagem é introduzir identidade e autorização por sessão, configuração de armazenamento e coordenação entre processos, antes de habilitar múltiplos workers.

## Variações de saves e mods

Os módulos de gestão verificam tabelas e colunas com infrastructure/schema.py. Nome e cor são consultados em Teams/Teams_Colours; não se resolve a marca pelo ID. O nome literal de localização tem precedência quando existe. Edição de identidade altera apenas os campos de banco compatíveis, não os assets externos do jogo.

Instalações usam Buildings e Buildings_HQ para obter os níveis disponíveis. Trocas de nível respeitam tipo, requisitos e estado de obra; a conservação é convertida entre fração nativa e porcentagem da interface. Expertise usa lote por peça e temporada lógica. A interface faz os incrementos, e a API valida o lote inteiro antes de gravar.

Motores usam perfis customizados quando o esquema é reconhecido; caso contrário, consultam fornecedores nativos e seus designs de referência. A criação e a alocação de perfis não são expostas como disponíveis no adaptador nativo. Conversões aerodinâmicas desconhecidas são marcadas como não editáveis; os agregados de desempenho continuam sendo estimativas do esquema conhecido, sem promessa de equivalência com todos os mods.
