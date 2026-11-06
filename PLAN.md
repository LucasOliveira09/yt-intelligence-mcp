# YouTube Intelligence MCP — Plano de Arquitetura & Implementação (Substituto vidIQ)

> **Autor/Estrategista:** Oliveira  
> **Objetivo:** Criar um servidor MCP local na VPS para análise profunda de YouTube (contas próprias + inteligência de concorrentes sem pagar vidIQ), gerenciável via CLI para adicionar/remover contas, e utilizável pelo Hermes / Claude / Codex.  
> **Target Path:** `/home/ubuntu/yt-intelligence-mcp`

---

## ⚠️ Diagnóstico Crítico & Armadilhas Reais (Onde Isso Quebra se Fizer Errado)

1. **A Armadilha da Cota da API v3 do Google (10.000 unidades/dia):**
   - Um endpoint simples de busca (`search.list`) consome **100 unidades de cota por chamada**. Com 100 buscas, a cota diária do projeto Google Cloud estoura e você toma `403 quotaExceeded` pelo resto do dia.
   - **Regra de Ouro da Arquitetura:**
     - **Canais Próprios:** Usar YouTube Data API v3 + YouTube Analytics API via OAuth2 (cota gerenciada e baixa para listar vídeos e métricas internas).
     - **Concorrentes e Mineração de Mercado:** **ZERO COTA GOOGLE**. Usar `scrapetube` + `yt-dlp` + `youtube-transcript-api` diretamente. Custo de cota da API: **zero**.

2. **Autenticação OAuth2 em VPS Headless (Sem Navegador Gráfico):**
   - Na VPS não temos Chrome com interface gráfica para login Google com redirect para `localhost:8080`.
   - **Solução:** Implementar fluxo OAuth2 com `InstalledAppFlow` configurado para gerar a URL de autorização no terminal. O Lucas abre no celular ou navegador do PC, autoriza com sua conta Google, copia o código de redirecionamento ou callback, e cola no terminal da CLI. Os refresh tokens são salvos localmente em `data/accounts.json` com `chmod 600`.

3. **Segurança de Tokens:**
   - Tokens com escopos de YouTube não podem vazar. O diretório `data/` e arquivos `*.json` de credenciais ficam permanentemente fora do Git via `.gitignore`.

4. **A Métrica de "Outlier" (O Segredo do vidIQ):**
   - Um vídeo com 50.000 visualizações não é necessariamente um outlier se o canal tem 2 milhões de inscritos.
   - O multiplicador de outlier real deve ser calculado como:
     $$\text{Score Outlier} = \frac{\text{Views do Vídeo}}{\text{Mediana das Views dos últimos 20 vídeos do canal}}$$
   - Score $\ge 2.5\times$ = Outlier confirmado.
   - Score $\ge 5.0\times$ = Vídeo viral/anomalia de retenção.

---

## 🏗️ Arquitetura do Sistema

```
/home/ubuntu/yt-intelligence-mcp/
├── PLAN.md                     <- Este documento de referência
├── README.md                   <- Guia rápido de uso e comandos
├── requirements.txt            <- Dependências Python
├── pyproject.toml              <- Configuração do projeto e entrypoint
├── data/                       <- Armazenamento local (gitignored)
│   ├── accounts.json           <- Tokens criptografados/seguros das contas autenticadas
│   └── cache.sqlite3           <- Cache local de transcrições e métricas de concorrentes
└── src/
    ├── __init__.py
    ├── config.py               <- Constantes, paths e variáveis de ambiente
    ├── cli.py                  <- CLI Typer/Rich para gerenciar contas do Lucas
    ├── auth.py                 <- Gerenciador de OAuth2 Google para headless VPS
    ├── server.py               <- Servidor FastMCP (tools expostas para IA)
    ├── services/
    │   ├── __init__.py
    │   ├── owned.py            <- Dados analíticos das contas do Lucas (API oficial)
    │   ├── competitor.py       <- Scraping de vídeos e canais concorrentes (Zero-Quota)
    │   └── transcripts.py      <- Extração e limpeza de transcrições de vídeos
    └── analytics/
        ├── __init__.py
        ├── outliers.py         <- Cálculo de mediana, outliers e velocidade de views
        └── tags_keywords.py    <- Extração de palavras-chave, tags reais e metadados
```

---

## 🛠️ Ferramentas MCP a Implementar (`src/server.py`)

O servidor FastMCP deve expor as seguintes ferramentas prontas para o agente:

### 1. Ferramentas para Contas Próprias (Authenticated)
* `yt_list_my_channels()`: Lista as contas conectadas (ex: Canal Dev, Galuzera).
* `yt_my_channel_overview(account_alias: str)`: Traz inscritos, views recentes, CTR médio e performance dos últimos vídeos.
* `yt_my_video_analytics(account_alias: str, video_id: str)`: Métricas detalhadas de um vídeo próprio (retenção média, impressões, CTR).

### 2. Ferramentas para Concorrentes e Mercado (Zero Quota)
* `yt_competitor_recent_videos(channel_url_or_handle: str, limit: int = 30)`: Lista os últimos N vídeos de qualquer canal público sem consumir cota.
* `yt_detect_outliers(channel_url_or_handle: str, limit: int = 30, threshold: float = 2.0)`: Calcula a mediana do canal e retorna apenas os vídeos que explodiram acima da curva, com títulos, datas e multiplicador de performance.
* `yt_get_video_transcript(video_url_or_id: str, lang: str = "pt")`: Extrai a transcrição completa e limpa de qualquer vídeo público para dissecação de roteiro.
* `yt_extract_video_metadata(video_url_or_id: str)`: Pega tags reais, descrição completa, contagem de likes, data exata e thumbnail em alta resolução.
* `yt_search_niche_trends(query: str, limit: int = 20)`: Busca vídeos recentes sobre um tema e filtra pelos de maior tração relativa.

---

## 📋 Roteiro de Execução para o Codex

### Fase 1: Fundação & Ambiente
1. Criar ambiente virtual Python (`.venv`).
2. Instalar dependências de `requirements.txt`.
3. Criar arquivo `src/config.py` definindo caminhos padrão (`DATA_DIR`, `ACCOUNTS_FILE`, `CACHE_DB`).

### Fase 2: Módulo de Concorrentes & Scraping (Zero Quota)
1. Implementar `src/services/competitor.py` usando `scrapetube` e `yt-dlp`.
2. Implementar `src/services/transcripts.py` com fallback de idioma (`pt`, `en`) e tratamento de erros para vídeos sem legenda.
3. Implementar `src/analytics/outliers.py` calculando mediana amostral e multiplicadores de views.
4. Escrever testes unitários em `tests/test_competitor.py` com canais reais públicos (ex: `@canaltech`, `@CodigofonteTV` ou `@BeroODev`).

### Fase 3: Módulo de Autenticação & Contas Próprias (OAuth Headless)
1. Implementar `src/auth.py`:
   - Leitura de `client_secret.json` do Google Cloud Console.
   - Suporte ao fluxo `Flow.from_client_secrets_file` com `run_local_server` ou geração de link com troca de authorization code no terminal.
   - Salvamento seguro de refresh tokens em `data/accounts.json` indexados por apelido (`alias`, ex: `canal_dev`, `galuzera`).
2. Implementar `src/cli.py` com comandos Typer:
   - `python -m src.cli add <alias>` -> Inicia fluxo de autorização no terminal.
   - `python -m src.cli list` -> Lista contas conectadas e status dos tokens.
   - `python -m src.cli remove <alias>` -> Remove conta.
3. Implementar `src/services/owned.py` consumindo `googleapiclient.discovery` usando as credenciais salvas.

### Fase 4: Servidor FastMCP
1. Implementar `src/server.py` registrando todas as tools descritas na seção anterior.
2. Garantir saída serializada em JSON limpo ou Markdown conciso para fácil consumo pelo LLM.
3. Permitir execução via `python -m src.server` (modo stdio para MCP).

### Fase 5: Integração com Hermes & Codex
1. Configurar o arquivo de manifesto MCP para plugar o novo servidor ao Hermes (`~/.hermes/config.yaml` ou profile ativo).
2. Fazer teste de ponta a ponta chamando uma busca de outliers e transcrição de concorrente diretamente pelo agente.

---

## 🔒 Regras de Segurança e Estabilidade na VPS
* Não rodar loops infinitos de scraping sem jitter/delay de rede.
* Manter o SQLite limpo, expurgando dados de cache com mais de 14 dias se o disco passar de 80%.
* Nunca expor portas desnecessárias no firewall da VPS; o servidor MCP roda estritamente via stdio local.
