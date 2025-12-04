# Azure RAGcelerator - Function App Infrastructure

# Log Analytics Workspace for monitoring
resource "azurerm_log_analytics_workspace" "main" {
  name                = "${local.name_prefix}-logs"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  sku                 = "PerGB2018"
  retention_in_days   = 30

  tags = local.common_tags
}

# Application Insights for monitoring
resource "azurerm_application_insights" "main" {
  name                = "${local.name_prefix}-insights"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  workspace_id        = azurerm_log_analytics_workspace.main.id
  application_type    = "web"

  tags = local.common_tags
}

# App Service Plan for Function App (Consumption)
resource "azurerm_service_plan" "functions" {
  name                = "${local.name_prefix}-func-plan"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  os_type             = "Linux"
  sku_name            = "Y1"  # Consumption plan

  tags = local.common_tags
}

# Function App for document processing
resource "azurerm_linux_function_app" "processor" {
  name                = "${local.name_prefix}-processor"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location

  storage_account_name       = azurerm_storage_account.functions.name
  storage_account_access_key = azurerm_storage_account.functions.primary_access_key
  service_plan_id            = azurerm_service_plan.functions.id

  # Enable managed identity
  identity {
    type = "SystemAssigned"
  }

  site_config {
    application_stack {
      python_version = "3.11"
    }

    # CORS settings
    cors {
      allowed_origins = ["*"]
    }

    # Application Insights integration
    application_insights_connection_string = azurerm_application_insights.main.connection_string
    application_insights_key               = azurerm_application_insights.main.instrumentation_key
  }

  app_settings = {
    # Azure Functions runtime settings
    "FUNCTIONS_WORKER_RUNTIME"       = "python"
    "AzureWebJobsFeatureFlags"       = "EnableWorkerIndexing"
    "SCM_DO_BUILD_DURING_DEPLOYMENT" = "true"
    "ENABLE_ORYX_BUILD"              = "true"

    # Storage settings
    "STORAGE_CONNECTION_STRING"  = azurerm_storage_account.main.primary_connection_string
    "DOCUMENTS_CONTAINER_NAME"   = azurerm_storage_container.documents.name

    # Cognitive Search settings
    "SEARCH_ENDPOINT" = "https://${azurerm_search_service.main.name}.search.windows.net"
    "SEARCH_API_KEY"  = azurerm_search_service.main.primary_key
    "SEARCH_INDEX_NAME" = "rag-documents"

    # Azure OpenAI settings
    "OPENAI_ENDPOINT"      = azurerm_cognitive_account.openai.endpoint
    "OPENAI_API_KEY"       = azurerm_cognitive_account.openai.primary_access_key
    "EMBEDDING_MODEL"      = var.embedding_model_name
    "OPENAI_API_VERSION"   = "2024-02-01"

    # Application Insights
    "APPLICATIONINSIGHTS_CONNECTION_STRING" = azurerm_application_insights.main.connection_string
  }

  tags = local.common_tags

  lifecycle {
    ignore_changes = [
      # Ignore changes made by deployment
      app_settings["WEBSITE_RUN_FROM_PACKAGE"],
    ]
  }
}

# Role assignment for Function App to access Storage
resource "azurerm_role_assignment" "function_storage_blob" {
  scope                = azurerm_storage_account.main.id
  role_definition_name = "Storage Blob Data Reader"
  principal_id         = azurerm_linux_function_app.processor.identity[0].principal_id
}

# Role assignment for Function App to access Cognitive Search
resource "azurerm_role_assignment" "function_search_contributor" {
  scope                = azurerm_search_service.main.id
  role_definition_name = "Search Index Data Contributor"
  principal_id         = azurerm_linux_function_app.processor.identity[0].principal_id
}



