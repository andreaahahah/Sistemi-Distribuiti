#!/bin/bash
# Build e avvio del container locale
# Assicurarsi di aver impostato le variabili d'ambiente (source set_env.sh) e avere Docker attivo.

set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
IMAGE_NAME="wikinews-cloud-explorer"
CONTAINER_NAME="wikinews-app"
PORT=8080

source "$PROJECT_DIR/set_env.sh" > /dev/null 2>&1
if [ -z "$GOOGLE_CLOUD_PROJECT" ]; then
    GOOGLE_CLOUD_PROJECT="sistemi-distribuiti-nuovo"
fi

if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker non è attivo! Avvialo con: sudo systemctl start docker"
    exit 1
fi

CRED_FILE="$PROJECT_DIR/credentials.json"
if [ ! -f "$CRED_FILE" ]; then
    echo "❌ File credentials.json non trovato in $PROJECT_DIR"
    exit 1
fi

echo "📦 Build dell'immagine Docker..."
docker build -t "$IMAGE_NAME" "$PROJECT_DIR"

docker rm -f "$CONTAINER_NAME" 2>/dev/null || true

echo ""
echo "🚀 Avvio container con Google Cloud..."
echo "   Credenziali: $CRED_FILE"
echo "   Porta: http://localhost:$PORT"
echo ""

docker run -d \
  --name "$CONTAINER_NAME" \
  -p "$PORT:$PORT" \
  -v "$CRED_FILE":/workspace/credentials.json:ro \
  -e GOOGLE_APPLICATION_CREDENTIALS=/workspace/credentials.json \
  -e GOOGLE_CLOUD_PROJECT="$GOOGLE_CLOUD_PROJECT" \
  -e USE_PUBSUB=false \
  "$IMAGE_NAME"

echo ""
echo "✅ Container avviato! Aspetto che il server sia pronto..."
sleep 3

echo ""
echo "📋 Log del container:"
echo "──────────────────────"
docker logs "$CONTAINER_NAME" 2>&1

echo ""
echo "──────────────────────"
echo "🌐 Apri nel browser: http://localhost:$PORT"
echo ""
echo "Comandi utili:"
echo "  docker logs -f $CONTAINER_NAME     # Segui i log in tempo reale"
echo "  docker stop $CONTAINER_NAME        # Ferma il container"
echo "  docker rm $CONTAINER_NAME          # Rimuovi il container"
