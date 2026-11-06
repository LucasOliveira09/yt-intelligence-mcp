# YouTube Intelligence MCP — Plataforma de Gestão Completa & Inteligência de Conteúdo

> **Autor/Estrategista:** Oliveira  
> **Objetivo:** Servidor MCP local e independente para gestão completa de conteúdo dos canais do Lucas (via OAuth Google) e inteligência de mercado/concorrência (Zero Cota), utilizável pelo Hermes / Claude / Codex.  
> **Target Path:** `/home/ubuntu/yt-intelligence-mcp`

---

## 🎯 Escopo da Plataforma (Visão Holística)

Não é apenas um buscador de vídeos. É um **centro de comando e estratégia de conteúdo**:
1. **Auditoria & Diagnóstico do Canal Próprio (via OAuth):** Retenção média, conversão de inscritos, dependência de tráfego (Busca vs Home/Sugeridos) e recomendações acionáveis.
2. **Raio-X de Vídeos (Deep Dive):** Tags reais ocultas, taxa de like/comentários e mineração de **dúvidas da audiência nos comentários** (pautas prontas que concorrentes deixaram passar).
3. **Radar de Nichos & Demanda:** Varredura de temas, análise de formatos recomendados (curto vs longo), palavras-chave dominantes e canais líderes.
4. **Inteligência de Concorrentes:** Mineração rápida de outliers com cálculo sobre a mediana (Zero Cota da API oficial).

---

## 🛠️ Matriz de Ferramentas MCP (`src/server.py`)

| Tool | Finalidade | Fonte de Dados | Cota API |
|---|---|---|---|
| `yt_channel_audit_report` | Relatório estratégico de 30 dias do canal com diagnóstico de gargalos | YouTube Analytics API (OAuth) | Baixa |
| `yt_my_channel_overview` | Resumo de inscritos, views totais e uploads recentes | YouTube Data API (OAuth) | 1 unidade |
| `yt_list_my_channels` | Lista canais próprios cadastrados | Local (`data/accounts.json`) | 0 |
| `yt_video_deep_dive` | Raio-X completo: tags reais, engajamento e dúvidas do público nos comentários | Google Data API / yt-dlp | 1 unidade |
| `yt_niche_radar` | Mapeia criadores dominantes, termos em alta e duração ideal de um nicho | yt-dlp search | 0 |
| `yt_analyze_competitor` | Mediana de views e cálculo de outliers de qualquer canal | yt-dlp flat-playlist | 0 |
| `yt_detect_outliers` | Filtra apenas vídeos que furaram a bolha de um criador | yt-dlp flat-playlist | 0 |
| `yt_compare_competitors` | Benchmark comparativo lado a lado de 2 a 5 canais | yt-dlp flat-playlist | 0 |
| `yt_get_video_transcript` | Extração de transcrições de vídeos para engenharia reversa de roteiro | yt-dlp / legendas | 0 |
| `yt_search_trends` | Busca rápida de pautas recentes por query | yt-dlp | 0 |

---

## 🔒 Autenticação OAuth2 Headless (VPS)

1. Coloque o `client_secret.json` em `data/client_secret.json`.
2. Rode no terminal:
   ```bash
   cd /home/ubuntu/yt-intelligence-mcp
   .venv/bin/python3 -m src.cli add-account canal_dev
   ```
3. O comando gera o link de autorização. Abra no navegador, autorize e cole o código de volta no terminal.
4. Os tokens são salvos em `data/accounts.json` com permissão restrita `0600` e ignorados pelo Git.
