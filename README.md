# YT Intelligence MCP 🎯

Servidor MCP local e independente para análise de YouTube: concorrência (sem gastar cota da API oficial) e gestão analítica das contas do Lucas (via OAuth Google).

Substituto direto do vidIQ, rodando 100% na VPS.

---

## 🚀 Quickstart

### 1. Criar venv e instalar dependências
```bash
cd /home/ubuntu/yt-intelligence-mcp
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Gerenciamento de Contas (CLI)
```bash
# Adicionar conta (Canal Dev ou Galuzera)
python -m src.cli add canal_dev

# Listar contas ativas
python -m src.cli list

# Testar leitura de canal concorrente (Zero Cota)
python -m src.cli test-competitor @BeroODev
```

### 3. Execução do Servidor MCP
```bash
python -m src.server
```

Consulte `PLAN.md` para o roteiro completo de implementação arquitetural.
