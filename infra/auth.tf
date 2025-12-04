# Azure RAGcelerator - Authentication Infrastructure
# Optional Entra ID App Registration for Container App authentication

# Conditionally create app registration if client ID is not provided externally
resource "azuread_application" "ui" {
  count        = var.entra_client_id == "" ? 1 : 0
  display_name = "${local.name_prefix}-ui-app"

  sign_in_audience = "AzureADMyOrg"

  web {
    redirect_uris = [
      "https://${azurerm_container_app.ui.ingress[0].fqdn}/.auth/login/aad/callback"
    ]

    implicit_grant {
      id_token_issuance_enabled = true
    }
  }

  required_resource_access {
    resource_app_id = "00000003-0000-0000-c000-000000000000" # Microsoft Graph

    resource_access {
      id   = "e1fe6dd8-ba31-4d61-89e7-88639da4683d" # User.Read
      type = "Scope"
    }
  }
}

resource "azuread_application_password" "ui" {
  count          = var.entra_client_id == "" ? 1 : 0
  application_id = azuread_application.ui[0].id
  display_name   = "Container App Auth Secret"
  end_date       = "2099-01-01T00:00:00Z"
}

resource "azuread_service_principal" "ui" {
  count     = var.entra_client_id == "" ? 1 : 0
  client_id = azuread_application.ui[0].client_id
}

# Local values for auth configuration
locals {
  # Use provided client ID or created one
  auth_client_id = var.entra_client_id != "" ? var.entra_client_id : (
    length(azuread_application.ui) > 0 ? azuread_application.ui[0].client_id : ""
  )
  
  # Use provided tenant ID or current tenant
  auth_tenant_id = var.entra_tenant_id != "" ? var.entra_tenant_id : data.azurerm_client_config.current.tenant_id
  
  # Check if auth should be enabled
  auth_enabled = local.auth_client_id != ""
}

# Output auth configuration
output "auth_client_id" {
  description = "Entra ID application client ID for authentication"
  value       = local.auth_client_id
}

output "auth_tenant_id" {
  description = "Entra ID tenant ID for authentication"
  value       = local.auth_tenant_id
}

output "auth_enabled" {
  description = "Whether authentication is configured"
  value       = local.auth_enabled
}

# Note: Container App authentication configuration is typically done
# via Azure CLI or Portal after initial deployment, as Terraform
# support for azurerm_container_app authentication is limited.
#
# See docs/AUTH_SETUP.md for manual configuration steps.
#
# After Container App is deployed, run:
#
# az containerapp auth update \
#   --name <container-app-name> \
#   --resource-group <resource-group> \
#   --unauthenticated-client-action RedirectToLoginPage \
#   --set identityProviders.azureActiveDirectory.enabled=true \
#   --set identityProviders.azureActiveDirectory.registration.clientId=<client-id> \
#   --set identityProviders.azureActiveDirectory.registration.openIdIssuer="https://login.microsoftonline.com/<tenant-id>/v2.0"



