#!/bin/bash

# Configurazione AWS per Almacenado API
REGION="eu-central-1"
ACCOUNT_ID="757909672126"
REPOSITORY_NAME="adibody-almacenado-api"
LAMBDA_FUNCTION_NAME="adibodyes_getAlmacenado"

echo "🔐 Autenticazione su ECR..."
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com

if [ $? -ne 0 ]; then
    echo "❌ Errore durante l'autenticazione su ECR"
    exit 1
fi

echo "📦 Creazione repository ECR se non esiste..."
aws ecr create-repository --repository-name $REPOSITORY_NAME --region $REGION 2>/dev/null || echo "✅ Repository già esistente o creato"

# Root del progetto = due livelli sopra rispetto a web/utility/
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "🏗️  Building Docker image for x86_64..."
cd "$PROJECT_ROOT"
docker buildx build --platform linux/amd64 --provenance=false --output type=docker -t $REPOSITORY_NAME -f shopify/Dockerfile.almacenado .

if [ $? -ne 0 ]; then
    echo "❌ Errore durante il build dell'immagine"
    exit 1
fi

echo "🏷️  Tagging image..."
docker tag $REPOSITORY_NAME:latest $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$REPOSITORY_NAME:latest

echo "⬆️  Pushing to ECR..."
docker push $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$REPOSITORY_NAME:latest

if [ $? -ne 0 ]; then
    echo "❌ Errore durante il push su ECR"
    exit 1
fi

echo "🔄 Controllo se la Lambda function esiste..."
aws lambda get-function --function-name $LAMBDA_FUNCTION_NAME --region $REGION > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "❌ Lambda function '$LAMBDA_FUNCTION_NAME' non trovata!"
    echo "💡 Devi creare la Lambda function manualmente su AWS Console prima di fare il deploy."
    echo "   - Nome: $LAMBDA_FUNCTION_NAME"
    echo "   - Runtime: Container image"
    echo "   - Image URI: $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$REPOSITORY_NAME:latest"
    echo "   - Architettura: x86_64"
    echo "   - Timeout: 300 secondi"
    echo "   - Memoria: 512 MB"
    exit 1
fi

echo "🔄 Aggiornamento Lambda function..."
aws lambda update-function-code \
    --function-name $LAMBDA_FUNCTION_NAME \
    --image-uri $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$REPOSITORY_NAME:latest \
    --region $REGION

if [ $? -ne 0 ]; then
    echo "❌ Errore durante l'aggiornamento della Lambda"
    exit 1
fi
echo "✅ Lambda function aggiornata con successo"

echo "⏳ Attesa che la Lambda sia pronta..."
sleep 10

echo "✅ Deploy completato con successo!"
echo "🌐 Lambda function: $LAMBDA_FUNCTION_NAME"
echo "📦 Repository ECR: $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$REPOSITORY_NAME"