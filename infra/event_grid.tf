# Azure RAGcelerator - Event Grid Infrastructure

# Event Grid System Topic for Storage Account
resource "azurerm_eventgrid_system_topic" "storage" {
  name                   = "${local.name_prefix}-storage-events"
  resource_group_name    = azurerm_resource_group.main.name
  location               = azurerm_resource_group.main.location
  source_arm_resource_id = azurerm_storage_account.main.id
  topic_type             = "Microsoft.Storage.StorageAccounts"

  identity {
    type = "SystemAssigned"
  }

  tags = local.common_tags
}

# Event Grid Subscription for Blob Created events
resource "azurerm_eventgrid_system_topic_event_subscription" "blob_created" {
  name                = "${local.name_prefix}-blob-created"
  system_topic        = azurerm_eventgrid_system_topic.storage.name
  resource_group_name = azurerm_resource_group.main.name

  # Filter to only documents container and specific blob events
  subject_filter {
    subject_begins_with = "/blobServices/default/containers/${azurerm_storage_container.documents.name}/"
    subject_ends_with   = ""
  }

  included_event_types = [
    "Microsoft.Storage.BlobCreated"
  ]

  # Advanced filtering for specific file types (optional)
  advanced_filter {
    string_ends_with {
      key    = "subject"
      values = [".pdf", ".PDF"]  # MVP: PDF files only
    }
  }

  # Target: Azure Function App
  azure_function_endpoint {
    function_id = "${azurerm_linux_function_app.processor.id}/functions/process_document"
    
    # Batching configuration
    max_events_per_batch              = 1
    preferred_batch_size_in_kilobytes = 64
  }

  retry_policy {
    max_delivery_attempts = 30
    event_time_to_live    = 1440  # 24 hours in minutes
  }

  # Dead letter destination (optional but recommended)
  # Uncomment to enable dead lettering
  # storage_blob_dead_letter_destination {
  #   storage_account_id          = azurerm_storage_account.main.id
  #   storage_blob_container_name = "deadletter"
  # }

  depends_on = [
    azurerm_linux_function_app.processor
  ]
}

# Note: The Event Grid subscription targets a function named "process_document"
# This function must be deployed to the Function App before the subscription
# will work correctly. During initial deployment, you may see errors until
# the function code is deployed.



