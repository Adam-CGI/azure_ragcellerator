# Azure RAGcelerator - Main Terraform Configuration

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.85.0"
    }
    azuread = {
      source  = "hashicorp/azuread"
      version = "~> 2.47.0"
    }
  }

  # Uncomment and configure for remote state storage
  # backend "azurerm" {
  #   resource_group_name  = "tfstate-rg"
  #   storage_account_name = "tfstateragcelerator"
  #   container_name       = "tfstate"
  #   key                  = "ragcelerator.tfstate"
  # }
}

provider "azurerm" {
  skip_provider_registration = true
  features {
    resource_group {
      prevent_deletion_if_contains_resources = false
    }
    key_vault {
      purge_soft_delete_on_destroy = true
    }
  }
}

provider "azuread" {}

# Data sources
data "azurerm_client_config" "current" {}

# Local values for consistent naming
locals {
  # Resource naming convention: {prefix}-{resource}-{environment}
  name_prefix = "${var.base_name_prefix}-${var.environment}"
  
  # Common tags for all resources
  common_tags = {
    Environment = var.environment
    Project     = "Azure RAGcelerator"
    ManagedBy   = "Terraform"
  }
}



