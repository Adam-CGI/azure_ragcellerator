# Azure RAGcelerator - Container Apps Infrastructure

# Azure Container Registry
resource "azurerm_container_registry" "main" {
  name                = "${var.base_name_prefix}acr${var.environment}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  sku                 = "Basic"
  admin_enabled       = true

  tags = local.common_tags
}

# Container Apps Environment
resource "azurerm_container_app_environment" "main" {
  name                       = "${local.name_prefix}-cae"
  resource_group_name        = azurerm_resource_group.main.name
  location                   = azurerm_resource_group.main.location
  log_analytics_workspace_id = azurerm_log_analytics_workspace.main.id

  tags = local.common_tags
}

# Container App for Streamlit UI
resource "azurerm_container_app" "ui" {
  name                         = "${local.name_prefix}-ui"
  resource_group_name          = azurerm_resource_group.main.name
  container_app_environment_id = azurerm_container_app_environment.main.id
  revision_mode                = "Single"

  # Enable managed identity
  identity {
    type = "SystemAssigned"
  }

  # Registry configuration
  registry {
    server               = azurerm_container_registry.main.login_server
    username             = azurerm_container_registry.main.admin_username
    password_secret_name = "acr-password"
  }

  secret {
    name  = "acr-password"
    value = azurerm_container_registry.main.admin_password
  }

  secret {
    name  = "search-api-key"
    value = azurerm_search_service.main.primary_key
  }

  secret {
    name  = "openai-api-key"
    value = azurerm_cognitive_account.openai.primary_access_key
  }

  template {
    container {
      name   = "streamlit-ui"
      image  = "mcr.microsoft.com/azuredocs/containerapps-helloworld:latest"  # Placeholder
      cpu    = var.container_app_cpu
      memory = var.container_app_memory

      env {
        name  = "SEARCH_ENDPOINT"
        value = "https://${azurerm_search_service.main.name}.search.windows.net"
      }

      env {
        name        = "SEARCH_API_KEY"
        secret_name = "search-api-key"
      }

      env {
        name  = "SEARCH_INDEX_NAME"
        value = "rag-documents"
      }

      env {
        name  = "OPENAI_ENDPOINT"
        value = azurerm_cognitive_account.openai.endpoint
      }

      env {
        name        = "OPENAI_API_KEY"
        secret_name = "openai-api-key"
      }

      env {
        name  = "EMBEDDING_MODEL"
        value = var.embedding_model_name
      }

      env {
        name  = "CHAT_MODEL"
        value = var.chat_model_name
      }

      env {
        name  = "OPENAI_API_VERSION"
        value = "2024-02-01"
      }
    }

    min_replicas = 0
    max_replicas = 3
  }

  ingress {
    external_enabled = true
    target_port      = 8501
    transport        = "auto"

    traffic_weight {
      percentage      = 100
      latest_revision = true
    }
  }

  tags = local.common_tags

  lifecycle {
    ignore_changes = [
      # Ignore image changes made by CI/CD
      template[0].container[0].image,
    ]
  }
}

# Role assignment for Container App to access Cognitive Search
resource "azurerm_role_assignment" "container_app_search" {
  scope                = azurerm_search_service.main.id
  role_definition_name = "Search Index Data Reader"
  principal_id         = azurerm_container_app.ui.identity[0].principal_id
}

# Optional: Entra ID Authentication
# Uncomment and configure when ready to enable authentication
# resource "azurerm_container_app" "ui_auth" {
#   # ... existing configuration ...
#
#   # Add authentication block
#   # Note: This requires the azurerm provider version 3.70+ and 
#   # the auth configuration is typically done via Azure Portal or CLI
#   # as the Terraform support is limited
# }



