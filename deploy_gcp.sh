#!/bin/bash
# ─────────────────────────────────────────────────────────────
# deploy_gcp.sh - Deploy SmartX PPE Detection na VM do GCP
# Uso: bash deploy_gcp.sh
# ─────────────────────────────────────────────────────────────

set -e

PROJECT_NAME="smartx-ppe-detection"
IMAGE_NAME="ppe-detection"
PORT=8080

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  SmartX PPE Detection - Deploy GCP"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 1. Instala Docker se necessário
if ! command -v docker &> /dev/null; then
    echo "📦 Instalando Docker..."
    curl -fsSL https://get.docker.com | sh
    sudo usermod -aG docker $USER
    echo "✅ Docker instalado. Rode o script novamente."
    exit 0
fi

# 2. Instala Docker Compose se necessário
if ! command -v docker compose &> /dev/null; then
    echo "📦 Instalando Docker Compose..."
    sudo apt-get update && sudo apt-get install -y docker-compose-plugin
fi

# 3. Para container anterior se existir
echo "🔄 Parando container anterior (se existir)..."
docker compose down 2>/dev/null || true

# 4. Build da imagem
echo "🔨 Fazendo build da imagem Docker..."
docker compose build --no-cache

# 5. Sobe o container
echo "🚀 Iniciando container..."
docker compose up -d

# 6. Aguarda health check
echo "⏳ Aguardando API inicializar (pode levar ~60s para baixar o modelo)..."
for i in {1..24}; do
    sleep 5
    STATUS=$(docker compose ps --format json 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('Health',''))" 2>/dev/null || echo "")
    HTTP=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:$PORT/health 2>/dev/null || echo "000")
    echo "  Tentativa $i/24 - HTTP: $HTTP"
    if [ "$HTTP" = "200" ]; then
        echo "✅ API online!"
        break
    fi
done

# 7. Exibe info
EXTERNAL_IP=$(curl -s ifconfig.me 2>/dev/null || echo "IP_NAO_DETECTADO")
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ✅ Deploy concluído!"
echo ""
echo "  Acesso local:    http://localhost:$PORT"
echo "  Acesso externo:  http://$EXTERNAL_IP:$PORT"
echo "  Health check:    http://localhost:$PORT/health"
echo "  Docs da API:     http://localhost:$PORT/docs"
echo ""
echo "  Logs: docker compose logs -f"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 8. Lembrete de Firewall GCP
echo ""
echo "⚠️  IMPORTANTE - Libere a porta no GCP Firewall:"
echo "   gcloud compute firewall-rules create allow-ppe-api \\"
echo "     --allow tcp:$PORT \\"
echo "     --target-tags=ppe-detection \\"
echo "     --description='SmartX PPE Detection API'"
