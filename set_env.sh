#!/bin/bash
# Script per impostare le variabili d'ambiente
# (eseguire con `source set_env.sh` su Linux o macOS)

export GOOGLE_CLOUD_PROJECT="sistemi-distribuiti-nuovo"
export GOOGLE_APPLICATION_CREDENTIALS="$(pwd)/credentials.json"
export USE_PUBSUB="false"

echo "✅ Variabili d'ambiente impostate:"
echo "   GOOGLE_CLOUD_PROJECT=$GOOGLE_CLOUD_PROJECT"
echo "   GOOGLE_APPLICATION_CREDENTIALS=$GOOGLE_APPLICATION_CREDENTIALS"
echo "   USE_PUBSUB=$USE_PUBSUB"

if [ ! -f "$GOOGLE_APPLICATION_CREDENTIALS" ]; then
    echo ""
    echo "⚠️  ATTENZIONE: Il file delle credenziali NON esiste in: $GOOGLE_APPLICATION_CREDENTIALS"
    echo ""
fi
