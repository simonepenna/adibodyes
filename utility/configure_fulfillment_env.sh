#!/bin/bash

# Script per configurare variabili ambiente Lambda fulfillment

REGION="eu-central-1"
LAMBDA_FUNCTION_NAME="adibodyes_getFulfillmentCheck"

echo "⏳ Attendo che la Lambda sia attiva..."
aws lambda wait function-active --function-name $LAMBDA_FUNCTION_NAME --region $REGION

echo "⚙️ Configurazione variabili ambiente..."

# Carica il JSON delle credenziali Google
GOOGLE_CREDS_FILE="shopify-lambda-integration-ff8f0760340f.json"

if [ ! -f "$GOOGLE_CREDS_FILE" ]; then
    echo "❌ File credenziali Google non trovato: $GOOGLE_CREDS_FILE"
    exit 1
fi

# Crea un file JSON temporaneo per le variabili ambiente
GOOGLE_JSON_STRING=$(cat $GOOGLE_CREDS_FILE | jq -c . | sed 's/"/\\"/g')

cat > /tmp/lambda_env.json <<EOF
{
  "Variables": {
    "SHOPIFY_ACCESS_TOKEN": "${SHOPIFY_ACCESS_TOKEN}",
    "GOOGLE_CREDENTIALS_JSON": "${GOOGLE_JSON_STRING}"
  }
}
EOF

# Aggiorna la configurazione Lambda
aws lambda update-function-configuration \
    --function-name $LAMBDA_FUNCTION_NAME \
    --environment file:///tmp/lambda_env.json \
    --region $REGION

if [ $? -eq 0 ]; then
    echo "✅ Variabili ambiente configurate con successo!"
    rm /tmp/lambda_env.json
else
    echo "❌ Errore nella configurazione delle variabili ambiente"
    rm /tmp/lambda_env.json
    exit 1
fi

echo ""
echo "🧪 Test Lambda..."
aws lambda invoke --function-name $LAMBDA_FUNCTION_NAME --region $REGION /tmp/response.json
echo ""
echo "📋 Risposta Lambda:"
cat /tmp/response.json | jq .
