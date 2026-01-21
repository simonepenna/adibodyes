#!/bin/bash

# Configurazione AWS per GLS Parcel Shop Lambda
REGION="eu-central-1"
ACCOUNT_ID="757909672126"
REPOSITORY_NAME="adibody-parcel-shop-api"
LAMBDA_FUNCTION_NAME="adibodyes_getParcelShop"

echo "🔐 Autenticazione su ECR..."
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com

if [ $? -ne 0 ]; then
    echo "❌ Errore durante l'autenticazione su ECR"
    exit 1
fi

echo "🏗️  Building Docker image for x86_64..."
cd ../..
docker buildx build --platform linux/amd64 --provenance=false --output type=docker -t $REPOSITORY_NAME -f web/utility/Dockerfile.parcelshop .
cd web/utility

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

echo "🔄 Aggiornamento Lambda function..."
aws lambda update-function-code \
    --function-name $LAMBDA_FUNCTION_NAME \
    --image-uri $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$REPOSITORY_NAME:latest \
    --region $REGION

if [ $? -ne 0 ]; then
    echo "❌ Errore durante l'aggiornamento della Lambda"
    exit 1
fi

echo "✅ Deploy completato con successo!"