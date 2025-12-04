# Azure RAGcelerator - Cognitive Search Infrastructure

# Azure Cognitive Search Service
resource "azurerm_search_service" "main" {
  name                = "${local.name_prefix}-search"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  sku                 = var.search_sku

  # Enable semantic search (requires Basic tier or higher)
  semantic_search_sku = var.search_sku == "free" ? null : "standard"

  # Security settings
  public_network_access_enabled = true
  local_authentication_enabled  = true

  identity {
    type = "SystemAssigned"
  }

  tags = local.common_tags
}

# Azure OpenAI Cognitive Services Account
resource "azurerm_cognitive_account" "openai" {
  name                = "${local.name_prefix}-openai"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  kind                = "OpenAI"
  sku_name            = var.openai_sku

  # Security settings
  public_network_access_enabled = true
  local_auth_enabled            = true

  identity {
    type = "SystemAssigned"
  }

  tags = local.common_tags
}

# Azure OpenAI Embedding Model Deployment
resource "azurerm_cognitive_deployment" "embedding" {
  name                 = var.embedding_model_name
  cognitive_account_id = azurerm_cognitive_account.openai.id

  model {
    format  = "OpenAI"
    name    = "text-embedding-ada-002"
    version = "2"
  }

  scale {
    type     = "Standard"
    capacity = 120
  }
}

# Azure OpenAI Chat Model Deployment
resource "azurerm_cognitive_deployment" "chat" {
  name                 = var.chat_model_name
  cognitive_account_id = azurerm_cognitive_account.openai.id

  model {
    format  = "OpenAI"
    name    = "gpt-35-turbo"
    version = "0613"
  }

  scale {
    type     = "Standard"
    capacity = 120
  }
}

# Note: The search index is created programmatically via Python script
# See: src/processor/indexers/provision_index.py
# This allows for more complex index configurations including vector fields



