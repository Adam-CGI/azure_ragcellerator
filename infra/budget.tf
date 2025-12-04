# Azure RAGcelerator - Budget and Cost Management
# Helps prevent unexpected charges on personal subscription

# Budget alert - notifies when spending approaches limit
resource "azurerm_consumption_budget_resource_group" "main" {
  name              = "${local.name_prefix}-budget"
  resource_group_id = azurerm_resource_group.main.id

  amount     = 100  # $100/month budget
  time_grain = "Monthly"

  time_period {
    start_date = formatdate("YYYY-MM-01'T'00:00:00Z", timestamp())
    # No end date = ongoing budget
  }

  # Alert at 50% ($50)
  notification {
    enabled   = true
    threshold = 50
    operator  = "GreaterThan"

    contact_emails = [
      # Add your email here
    ]
  }

  # Alert at 80% ($80)
  notification {
    enabled   = true
    threshold = 80
    operator  = "GreaterThan"

    contact_emails = [
      # Add your email here  
    ]
  }

  # Alert at 100% ($100)
  notification {
    enabled        = true
    threshold      = 100
    operator       = "GreaterThan"
    threshold_type = "Actual"

    contact_emails = [
      # Add your email here
    ]
  }

  lifecycle {
    ignore_changes = [
      time_period,  # Don't recreate on date change
    ]
  }
}

# Output estimated costs
output "estimated_monthly_cost" {
  description = "Estimated monthly cost (approximate)"
  value       = <<-EOT
    Estimated Monthly Costs:
    - Cognitive Search (${var.search_sku}): ${var.search_sku == "free" ? "$0" : "~$75"}
    - Storage Account (LRS): ~$1-2
    - Function App (Consumption): ~$0
    - Container Apps (scale to 0): ~$0-5
    - Azure OpenAI (pay per use): ~$1-10
    
    Total: ${var.search_sku == "free" ? "~$5-20/month" : "~$80-95/month"}
    
    To reduce costs:
    - Use 'terraform destroy' when not testing
    - Set search_sku = "free" (loses vector search)
  EOT
}

