#!/bin/bash

# Vai alla directory root del progetto
cd "$(dirname "$(dirname "$(dirname "$0")")")"

# Configurazione AWS
REGION="eu-central-1"
ACCOUNT_ID="757909672126"
REPOSITORY_NAME="adibody-stock-api"
LAMBDA_FUNCTION_NAME="adibodyes_getStock"

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
    echo "📦 Creazione repository ECR $REPOSITORY_NAME..."
    aws ecr create-repository --repository-name $REPOSITORY_NAME --region $REGION
    
    if [ $? -ne 0 ]; then
        echo "❌ Errore durante la creazione del repository ECR"
        exit 1
    fi
fi

echo "🏗️  Building Docker image for x86_64..."
docker buildx build --platform linux/amd64 --provenance=false --output type=docker -t $REPOSITORY_NAME -f web/utility/Dockerfile.stock .

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

if [ $? -ne 0 ]; then
    echo "🆕 Creazione nuova Lambda function $LAMBDA_FUNCTION_NAME..."
    aws lambda create-function \
        --function-name $LAMBDA_FUNCTION_NAME \
        --package-type Image \
        --code ImageUri=$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$REPOSITORY_NAME:latest \
        --role arn:aws:iam::$ACCOUNT_ID:role/LambdaExecutionRole \
        --timeout 60 \
        --memory-size 512 \
        --region $REGION \
        --environment "Variables={SHOPIFY_SHOP_NAME=\${SHOPIFY_SHOP_NAME},SHOPIFY_ACCESS_TOKEN=\${SHOPIFY_ACCESS_TOKEN},SHOPIFY_GRAPHQL_TOKEN=\${SHOPIFY_GRAPHQL_TOKEN},GOOGLE_SHEET_ID=\${GOOGLE_SHEET_ID}}"
    
    if [ $? -ne 0 ]; then
        echo "❌ Errore durante la creazione della Lambda"
        exit 1
    fi
else
    echo "🔄 Aggiornamento Lambda function..."
    aws lambda update-function-code \
        --function-name $LAMBDA_FUNCTION_NAME \
        --image-uri $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$REPOSITORY_NAME:latest \
        --region $REGION
    
    if [ $? -ne 0 ]; then
        echo "❌ Errore durante l'aggiornamento della Lambda"
        exit 1
    fi
fi

echo "✅ Deploy completato con successo!"
echo ""
echo "📝 Prossimi passi:"
echo "1. Vai su API Gateway Console"
echo "2. Crea/aggiorna endpoint GET /stock"
echo "3. Integrazione: Lambda Proxy -> $LAMBDA_FUNCTION_NAME"
echo "4. Deploy API stage: prod"
echo "5. Copia URL API Gateway e aggiorna web/src/services/stockService.ts"
