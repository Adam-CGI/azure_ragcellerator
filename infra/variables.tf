# Azure RAGcelerator - Terraform Variables

variable "resource_group_name" {
  description = "Name of the resource group"
  type        = string
  default     = "rg-ragcelerator"
}

variable "location" {
  description = "Azure region for resources"
  type        = string
  default     = "eastus"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be one of: dev, staging, prod."
  }
}

variable "base_name_prefix" {
  description = "Base prefix for resource names (lowercase, no special chars)"
  type        = string
  default     = "ragcel"

  validation {
    condition     = can(regex("^[a-z0-9]{3,10}$", var.base_name_prefix))
    error_message = "Base name prefix must be 3-10 lowercase alphanumeric characters."
  }
}

# Storage configuration
variable "storage_replication_type" {
  description = "Storage account replication type"
  type        = string
  default     = "LRS"
}

# Cognitive Search configuration
variable "search_sku" {
  description = "Azure Cognitive Search SKU"
  type        = string
  default     = "basic"
}

# Azure OpenAI configuration
variable "openai_sku" {
  description = "Azure OpenAI SKU"
  type        = string
  default     = "S0"
}

variable "embedding_model_name" {
  description = "Name for the embedding model deployment"
  type        = string
  default     = "text-embedding-ada-002"
}

variable "chat_model_name" {
  description = "Name for the chat model deployment"
  type        = string
  default     = "gpt-35-turbo"
}

# Container Apps configuration
variable "container_app_cpu" {
  description = "CPU allocation for Container App"
  type        = number
  default     = 0.5
}

variable "container_app_memory" {
  description = "Memory allocation for Container App (in Gi)"
  type        = string
  default     = "1Gi"
}

# Authentication (optional - set for Entra ID auth)
variable "entra_client_id" {
  description = "Entra ID application client ID for authentication"
  type        = string
  default     = ""
}

variable "entra_tenant_id" {
  description = "Entra ID tenant ID for authentication"
  type        = string
  default     = ""
}



