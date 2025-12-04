# Azure RAGcelerator - Authentication Setup

This guide covers setting up Entra ID (Azure AD) authentication for the Streamlit UI.

## Overview

The application uses Azure Container Apps' built-in authentication (Easy Auth) to protect the UI. This provides:

- Single Sign-On (SSO) with Microsoft Entra ID
- Automatic token management
- No code changes required in the Streamlit app

## Prerequisites

- Azure subscription with Entra ID (Azure AD)
- Permissions to create App Registrations
- Container App deployed (see [DEPLOYMENT.md](DEPLOYMENT.md))

## Step 1: Create App Registration

### Via Azure Portal

1. Navigate to **Azure Portal** → **Microsoft Entra ID** → **App registrations**
2. Click **New registration**
3. Configure the registration:
   - **Name:** `Azure RAGcelerator UI`
   - **Supported account types:** Choose based on your needs:
     - Single tenant: Only users in your organization
     - Multitenant: Users from any organization
   - **Redirect URI:** 
     - Type: `Web`
     - URL: `https://<your-container-app-url>/.auth/login/aad/callback`

4. Click **Register**

### Via Azure CLI

```bash
# Get your Container App URL
CONTAINER_APP_URL=$(az containerapp show \
  --name <your-container-app-name> \
  --resource-group <your-resource-group> \
  --query properties.configuration.ingress.fqdn -o tsv)

# Create App Registration
az ad app create \
  --display-name "Azure RAGcelerator UI" \
  --web-redirect-uris "https://$CONTAINER_APP_URL/.auth/login/aad/callback" \
  --sign-in-audience AzureADMyOrg
```

## Step 2: Configure App Registration

### Get Required Values

After creating the app registration, note down:

1. **Application (client) ID** - Found on the Overview page
2. **Directory (tenant) ID** - Found on the Overview page

### Create Client Secret (Optional)

If you need a client secret:

1. Go to **Certificates & secrets**
2. Click **New client secret**
3. Add a description and expiration
4. Copy the secret value immediately (it won't be shown again)

### Configure API Permissions

The default permissions are usually sufficient. Verify:

1. Go to **API permissions**
2. Ensure `Microsoft Graph` → `User.Read` is present
3. Click **Grant admin consent** if required

## Step 3: Enable Container App Authentication

### Via Azure Portal

1. Navigate to your Container App in Azure Portal
2. Go to **Settings** → **Authentication**
3. Click **Add identity provider**
4. Select **Microsoft**
5. Configure:
   - **App registration type:** Provide details of an existing app registration
   - **Application (client) ID:** Your app registration client ID
   - **Client secret (optional):** Your client secret if created
   - **Issuer URL:** `https://login.microsoftonline.com/<tenant-id>/v2.0`
6. Configure additional settings:
   - **Restrict access:** Require authentication
   - **Unauthenticated requests:** HTTP 302 Found redirect (recommended)
   - **Token store:** Enabled
7. Click **Add**

### Via Azure CLI

```bash
# Set variables
RESOURCE_GROUP="your-resource-group"
CONTAINER_APP_NAME="your-container-app-name"
CLIENT_ID="your-app-registration-client-id"
TENANT_ID="your-tenant-id"
CLIENT_SECRET="your-client-secret"  # Optional

# Enable authentication
az containerapp auth update \
  --name $CONTAINER_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --unauthenticated-client-action RedirectToLoginPage \
  --set identityProviders.azureActiveDirectory.enabled=true \
  --set identityProviders.azureActiveDirectory.registration.clientId=$CLIENT_ID \
  --set identityProviders.azureActiveDirectory.registration.openIdIssuer="https://login.microsoftonline.com/$TENANT_ID/v2.0"

# If using client secret
az containerapp auth update \
  --name $CONTAINER_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --set identityProviders.azureActiveDirectory.registration.clientSecretSettingName=MICROSOFT_PROVIDER_AUTHENTICATION_SECRET

# Set the secret
az containerapp secret set \
  --name $CONTAINER_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --secrets "microsoft-provider-authentication-secret=$CLIENT_SECRET"
```

### Via Terraform

Add to your `infra/container_apps.tf`:

```hcl
# Note: Container App authentication via Terraform is limited.
# You may need to use Azure CLI or Portal for full configuration.

# Add these variables to your terraform.tfvars
variable "entra_client_id" {
  description = "Entra ID application client ID"
  type        = string
}

variable "entra_tenant_id" {
  description = "Entra ID tenant ID"
  type        = string
}
```

## Step 4: Test Authentication

1. Open your Container App URL in an incognito/private browser window
2. You should be redirected to Microsoft login
3. Sign in with your organizational account
4. After successful login, you should see the RAGcelerator UI

## Step 5: Configure User Access (Optional)

### Restrict to Specific Users/Groups

1. Go to your App Registration → **Enterprise applications**
2. Click on your app
3. Go to **Users and groups**
4. Click **Add user/group**
5. Select users or groups who should have access
6. Go to **Properties**
7. Set **Assignment required?** to **Yes**

### Add App Roles (Optional)

For role-based access:

1. Go to App Registration → **App roles**
2. Click **Create app role**
3. Configure roles (e.g., `Reader`, `Admin`)
4. Assign roles to users in **Enterprise applications** → **Users and groups**

## Accessing User Information in the App

With Easy Auth enabled, user information is available in HTTP headers:

```python
# In your Streamlit app or API
import streamlit as st

# Get user info from headers (when running behind Easy Auth)
def get_user_info():
    # These headers are set by Container Apps authentication
    headers = st.context.headers  # Streamlit 1.32+
    
    user_info = {
        "name": headers.get("X-MS-CLIENT-PRINCIPAL-NAME", "Anonymous"),
        "id": headers.get("X-MS-CLIENT-PRINCIPAL-ID", ""),
        "idp": headers.get("X-MS-CLIENT-PRINCIPAL-IDP", ""),
    }
    return user_info
```

## Troubleshooting

### Common Issues

1. **Redirect URI Mismatch**
   - Ensure the redirect URI in App Registration exactly matches:
     `https://<container-app-url>/.auth/login/aad/callback`
   - Check for trailing slashes

2. **AADSTS Error Codes**
   - `AADSTS50011`: Reply URL doesn't match configured URLs
   - `AADSTS65001`: User or admin hasn't consented to use the app
   - `AADSTS700016`: Application not found in tenant

3. **Authentication Loop**
   - Clear browser cookies and cache
   - Check token expiration settings
   - Verify the token store is enabled

4. **Access Denied After Login**
   - Check if "Assignment required" is enabled
   - Verify user is assigned to the app

### Debugging

Check Container App logs:

```bash
az containerapp logs show \
  --name $CONTAINER_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --follow
```

Check authentication configuration:

```bash
az containerapp auth show \
  --name $CONTAINER_APP_NAME \
  --resource-group $RESOURCE_GROUP
```

## Security Best Practices

1. **Use HTTPS only** - Container Apps enforce this by default
2. **Set token expiration** - Configure appropriate session timeout
3. **Enable MFA** - Configure in Entra ID Conditional Access
4. **Rotate secrets** - If using client secrets, rotate regularly
5. **Audit access** - Review sign-in logs in Entra ID
6. **Limit redirect URIs** - Only add necessary redirect URIs

## Post-MVP Enhancements

After MVP, consider:

1. **Conditional Access Policies**
   - Require compliant devices
   - Block risky sign-ins
   - Geo-restrictions

2. **App Roles and Groups**
   - Implement admin vs. user roles
   - Sync with security groups

3. **Token Claims**
   - Add custom claims for user metadata
   - Include group membership

4. **API Protection**
   - Protect Function App with same auth
   - Implement on-behalf-of flow for API calls



