#!/bin/bash

# Vai alla directory root del progetto
cd "$(dirname "$(dirname "$(dirname "$0")")")"

# Configurazione AWS
REGION="eu-central-1"
ACCOUNT_ID="757909672126"
REPOSITORY_NAME="adibody-fulfillment-check"
LAMBDA_FUNCTION_NAME="adibodyes_getFulfillmentCheck"

echo "🔐 Autenticazione su ECR..."
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com

if [ $? -ne 0 ]; then
    echo "❌ Errore durante l'autenticazione su ECR"
    exit 1
fi

# Verifica se il repository ECR esiste, altrimenti crealo
echo "📦 Verifica repository ECR..."
aws ecr describe-repositories --repository-names $REPOSITORY_NAME --region $REGION > /dev/null 2>&1

if [ $? -ne 0 ]; then
    echo "📦 Creazione repository ECR..."
    aws ecr create-repository --repository-name $REPOSITORY_NAME --region $REGION
    if [ $? -ne 0 ]; then
        echo "❌ Errore durante la creazione del repository"
        exit 1
    fi
fi

echo "🏗️  Building Docker image for x86_64..."
cd web/utility
docker buildx build --platform linux/amd64 --provenance=false --output type=docker -t $REPOSITORY_NAME -f Dockerfile.fulfillment ../..
cd ..

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

# Verifica se la Lambda esiste
echo "🔍 Verifica Lambda function..."
aws lambda get-function --function-name $LAMBDA_FUNCTION_NAME --region $REGION > /dev/null 2>&1

if [ $? -eq 0 ]; then
    # Lambda esiste - aggiorna codice
    echo "🔄 Aggiornamento Lambda function..."
    aws lambda update-function-code \
        --function-name $LAMBDA_FUNCTION_NAME \
        --image-uri $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$REPOSITORY_NAME:latest \
        --region $REGION
else
    # Lambda non esiste - creala (senza variabili ambiente per ora)
    echo "🆕 Creazione Lambda function..."
    aws lambda create-function \
        --function-name $LAMBDA_FUNCTION_NAME \
        --package-type Image \
        --code ImageUri=$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$REPOSITORY_NAME:latest \
        --role arn:aws:iam::$ACCOUNT_ID:role/LambdaExecutionRole \
        --timeout 900 \
        --memory-size 512 \
        --region $REGION
    
    # Configura variabili ambiente separatamente
    if [ $? -eq 0 ]; then
        echo "⚙️  Configurazione variabili ambiente..."
        GOOGLE_CREDS=$(cat shopify-lambda-integration-ff8f0760340f.json | jq -c . | sed 's/"/\\"/g')
        aws lambda update-function-configuration \
            --function-name $LAMBDA_FUNCTION_NAME \
            --environment "Variables={SHOPIFY_ACCESS_TOKEN=${SHOPIFY_ACCESS_TOKEN},GOOGLE_CREDENTIALS_JSON=\"${GOOGLE_CREDS}\"}" \
            --region $REGION
    fi
fi

if [ $? -ne 0 ]; then
    echo "❌ Errore durante la configurazione della Lambda"
    exit 1
fi

echo "✅ Deploy completato con successo!"
echo ""
echo "📝 Prossimi passi:"
echo "1. Configura API Gateway per creare endpoint /prod/fulfillment"
echo "2. Testa Lambda con: aws lambda invoke --function-name $LAMBDA_FUNCTION_NAME --region $REGION response.json"
