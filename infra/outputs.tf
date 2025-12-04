# Azure RAGcelerator - Terraform Outputs

# Resource Group
output "resource_group_name" {
  description = "Name of the resource group"
  value       = azurerm_resource_group.main.name
}

output "resource_group_id" {
  description = "ID of the resource group"
  value       = azurerm_resource_group.main.id
}

# Storage Account
output "storage_account_name" {
  description = "Name of the storage account"
  value       = azurerm_storage_account.main.name
}

output "storage_account_id" {
  description = "ID of the storage account"
  value       = azurerm_storage_account.main.id
}

output "storage_connection_string" {
  description = "Storage account connection string"
  value       = azurerm_storage_account.main.primary_connection_string
  sensitive   = true
}

output "storage_primary_blob_endpoint" {
  description = "Primary blob endpoint URL"
  value       = azurerm_storage_account.main.primary_blob_endpoint
}

# Cognitive Search
output "search_service_name" {
  description = "Name of the Cognitive Search service"
  value       = azurerm_search_service.main.name
}

output "search_endpoint" {
  description = "Cognitive Search endpoint URL"
  value       = "https://${azurerm_search_service.main.name}.search.windows.net"
}

output "search_api_key" {
  description = "Cognitive Search admin API key"
  value       = azurerm_search_service.main.primary_key
  sensitive   = true
}

# Azure OpenAI
output "openai_endpoint" {
  description = "Azure OpenAI endpoint URL"
  value       = azurerm_cognitive_account.openai.endpoint
}

output "openai_api_key" {
  description = "Azure OpenAI API key"
  value       = azurerm_cognitive_account.openai.primary_access_key
  sensitive   = true
}

output "embedding_deployment_name" {
  description = "Name of the embedding model deployment"
  value       = var.embedding_model_name
}

output "chat_deployment_name" {
  description = "Name of the chat model deployment"
  value       = var.chat_model_name
}

# Function App
output "function_app_name" {
  description = "Name of the Function App"
  value       = azurerm_linux_function_app.processor.name
}

output "function_app_url" {
  description = "URL of the Function App"
  value       = "https://${azurerm_linux_function_app.processor.default_hostname}"
}

output "function_app_principal_id" {
  description = "Principal ID of the Function App managed identity"
  value       = azurerm_linux_function_app.processor.identity[0].principal_id
}

# Container App
output "container_app_name" {
  description = "Name of the Container App"
  value       = azurerm_container_app.ui.name
}

output "container_app_url" {
  description = "URL of the Container App (UI)"
  value       = "https://${azurerm_container_app.ui.ingress[0].fqdn}"
}

# Application Insights
output "application_insights_connection_string" {
  description = "Application Insights connection string"
  value       = azurerm_application_insights.main.connection_string
  sensitive   = true
}

output "application_insights_instrumentation_key" {
  description = "Application Insights instrumentation key"
  value       = azurerm_application_insights.main.instrumentation_key
  sensitive   = true
}

# Container Registry
output "container_registry_name" {
  description = "Name of the Azure Container Registry"
  value       = azurerm_container_registry.main.name
}

output "container_registry_login_server" {
  description = "Login server for the Container Registry"
  value       = azurerm_container_registry.main.login_server
}



