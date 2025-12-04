# Azure RAGcelerator - Storage Infrastructure

# Resource Group
resource "azurerm_resource_group" "main" {
  name     = var.resource_group_name
  location = var.location
  tags     = local.common_tags
}

# Storage Account
resource "azurerm_storage_account" "main" {
  name                     = "${var.base_name_prefix}storage${var.environment}"
  resource_group_name      = azurerm_resource_group.main.name
  location                 = azurerm_resource_group.main.location
  account_tier             = "Standard"
  account_replication_type = var.storage_replication_type
  account_kind             = "StorageV2"

  # Security settings
  min_tls_version                 = "TLS1_2"
  allow_nested_items_to_be_public = false
  shared_access_key_enabled       = true

  # Enable blob versioning for document history
  blob_properties {
    versioning_enabled = true
    
    delete_retention_policy {
      days = 7
    }

    container_delete_retention_policy {
      days = 7
    }
  }

  tags = local.common_tags
}

# Container for document uploads
resource "azurerm_storage_container" "documents" {
  name                  = "documents"
  storage_account_name  = azurerm_storage_account.main.name
  container_access_type = "private"
}

# Container for test data
resource "azurerm_storage_container" "test_data" {
  name                  = "test-data"
  storage_account_name  = azurerm_storage_account.main.name
  container_access_type = "private"
}

# Storage account for Function App
resource "azurerm_storage_account" "functions" {
  name                     = "${var.base_name_prefix}func${var.environment}"
  resource_group_name      = azurerm_resource_group.main.name
  location                 = azurerm_resource_group.main.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  account_kind             = "StorageV2"

  min_tls_version                 = "TLS1_2"
  allow_nested_items_to_be_public = false

  tags = local.common_tags
}



