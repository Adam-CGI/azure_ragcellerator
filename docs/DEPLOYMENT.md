# Azure RAGcelerator - Deployment Guide

This guide covers the setup required for automated CI/CD deployment to Azure.

## Prerequisites

- Azure subscription with appropriate permissions
- GitHub repository access
- Azure CLI installed locally
- Terraform >= 1.5.0

## Azure Service Principal Setup

Create a service principal for GitHub Actions to authenticate with Azure.

### 1. Create the Service Principal

```bash
# Login to Azure
az login

# Set your subscription
az account set --subscription "<YOUR_SUBSCRIPTION_ID>"

# Create service principal with Contributor role
az ad sp create-for-rbac \
  --name "github-ragcelerator-deploy" \
  --role Contributor \
  --scopes /subscriptions/<YOUR_SUBSCRIPTION_ID> \
  --sdk-auth
```

This outputs JSON credentials like:

```json
{
  "clientId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "clientSecret": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "subscriptionId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "tenantId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  ...
}
```

Save this output - you'll need it for GitHub Secrets.

### 2. Grant Additional Permissions (if needed)

For Azure Container Registry push:

```bash
# Get the service principal object ID
SP_OBJECT_ID=$(az ad sp show --id <clientId> --query id -o tsv)

# Assign AcrPush role (after ACR is created)
az role assignment create \
  --assignee $SP_OBJECT_ID \
  --role AcrPush \
  --scope /subscriptions/<SUBSCRIPTION_ID>/resourceGroups/<RG_NAME>/providers/Microsoft.ContainerRegistry/registries/<ACR_NAME>
```

## GitHub Secrets Configuration

Navigate to your GitHub repository → Settings → Secrets and variables → Actions.

Add the following secrets:

| Secret Name | Description | Value |
|-------------|-------------|-------|
| `AZURE_CREDENTIALS` | Full JSON output from service principal creation | `{"clientId":"...","clientSecret":"...","subscriptionId":"...","tenantId":"..."}` |
| `AZURE_SUBSCRIPTION_ID` | Azure subscription ID | `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` |
| `AZURE_TENANT_ID` | Azure tenant ID | `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` |
| `AZURE_CLIENT_ID` | Service principal client ID | `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` |
| `AZURE_CLIENT_SECRET` | Service principal client secret | `xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx` |

## Terraform State Backend Setup

For production, configure remote state storage in Azure.

### 1. Create Storage Account for State

```bash
# Create resource group for state
az group create --name tfstate-rg --location eastus

# Create storage account
az storage account create \
  --name tfstateragcelerator \
  --resource-group tfstate-rg \
  --sku Standard_LRS \
  --encryption-services blob

# Create container for state files
az storage container create \
  --name tfstate \
  --account-name tfstateragcelerator
```

### 2. Configure Backend in Terraform

Uncomment the backend configuration in `infra/main.tf`:

```hcl
terraform {
  backend "azurerm" {
    resource_group_name  = "tfstate-rg"
    storage_account_name = "tfstateragcelerator"
    container_name       = "tfstate"
    key                  = "ragcelerator.tfstate"
  }
}
```

### 3. Add State Storage Access to GitHub Secrets

Add these additional secrets:

| Secret Name | Value |
|-------------|-------|
| `TF_STATE_RESOURCE_GROUP` | `tfstate-rg` |
| `TF_STATE_STORAGE_ACCOUNT` | `tfstateragcelerator` |
| `TF_STATE_CONTAINER` | `tfstate` |

## Manual Deployment

If you need to deploy manually (without GitHub Actions):

### 1. Deploy Infrastructure

```bash
cd infra

# Initialize Terraform
terraform init

# Plan changes
terraform plan -var="environment=dev" -out=tfplan

# Apply changes
terraform apply tfplan

# Get outputs
terraform output -json > outputs.json
```

### 2. Build and Push UI Container

```bash
# Login to ACR
ACR_NAME=$(terraform output -raw container_registry_name)
az acr login --name $ACR_NAME

# Build and push
docker build -t $ACR_NAME.azurecr.io/ragcelerator-ui:latest .
docker push $ACR_NAME.azurecr.io/ragcelerator-ui:latest
```

### 3. Update Container App

```bash
CONTAINER_APP_NAME=$(terraform output -raw container_app_name)
RESOURCE_GROUP=$(terraform output -raw resource_group_name)

az containerapp update \
  --name $CONTAINER_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --image $ACR_NAME.azurecr.io/ragcelerator-ui:latest
```

### 4. Deploy Function App

```bash
cd ../src/processor

# Deploy using Azure Functions Core Tools
func azure functionapp publish $(terraform -chdir=../../infra output -raw function_app_name)
```

## Provision Search Index

After infrastructure is deployed, create the search index:

```bash
# Set environment variables from Terraform outputs
export SEARCH_ENDPOINT=$(terraform -chdir=infra output -raw search_endpoint)
export SEARCH_API_KEY=$(terraform -chdir=infra output -raw search_api_key)

# Run provisioning script
python -m src.processor.indexers.provision_index
```

## Verify Deployment

### 1. Check Function App

```bash
# Get Function App URL
FUNC_URL=$(terraform -chdir=infra output -raw function_app_url)

# Check health endpoint
curl $FUNC_URL/api/health
```

### 2. Check UI Container App

```bash
# Get Container App URL
UI_URL=$(terraform -chdir=infra output -raw container_app_url)

# Open in browser
echo "UI available at: $UI_URL"
```

### 3. Test Document Processing

```bash
# Upload a test PDF
STORAGE_CS=$(terraform -chdir=infra output -raw storage_connection_string)

az storage blob upload \
  --connection-string "$STORAGE_CS" \
  --container-name documents \
  --name test-document.pdf \
  --file /path/to/test.pdf

# Check Function App logs for processing
az webapp log tail --name $(terraform -chdir=infra output -raw function_app_name) --resource-group $(terraform -chdir=infra output -raw resource_group_name)
```

## Troubleshooting

### Common Issues

1. **Service Principal Permissions**
   - Ensure the SP has Contributor role on the subscription or resource group
   - For ACR push, ensure AcrPush role is assigned

2. **Terraform State Lock**
   - If state is locked, break the lock with:
     ```bash
     terraform force-unlock <LOCK_ID>
     ```

3. **Container App Not Starting**
   - Check logs: `az containerapp logs show --name <app-name> --resource-group <rg>`
   - Verify environment variables are set correctly

4. **Function App Not Triggering**
   - Check Event Grid subscription status in Azure Portal
   - Verify function name matches subscription target

### Getting Help

- Check Azure Portal for resource health and diagnostics
- Review GitHub Actions logs for deployment failures
- Use Application Insights for runtime errors

## Cost Optimization

For development/testing:

1. Use `Basic` tier for Cognitive Search (or `Free` for very small workloads)
2. Use `Consumption` plan for Function Apps
3. Set Container Apps to scale to 0 when idle
4. Use `Standard_LRS` for storage (not geo-redundant)

For production:

1. Consider `Standard` tier for Cognitive Search
2. Enable autoscaling for Container Apps
3. Set up Azure Monitor alerts for cost thresholds



