targetScope = 'resourceGroup'

@description('Location for all resources')
param location string = resourceGroup().location

@description('Environment name (e.g., dev, test, prod)')
param environmentName string = 'dev'

@description('Application name prefix')
param appNamePrefix string = 'osint'

@description('Database administrator username')
param dbAdminUsername string = 'osintadmin'

@description('Database administrator password')
@secure()
param dbAdminPassword string

// Variables
var resourceSuffix = '${appNamePrefix}-${environmentName}-${uniqueString(resourceGroup().id)}'
var containerAppEnvironmentName = 'cae-${resourceSuffix}'
var backendAppName = 'backend-${resourceSuffix}'
var frontendAppName = 'frontend-${resourceSuffix}'
var postgresServerName = 'psql-${resourceSuffix}'
var keyVaultName = 'kv-${take(resourceSuffix, 19)}' // Key Vault names are limited to 24 characters
var serviceBusNamespaceName = 'sb-${resourceSuffix}'
var logAnalyticsWorkspaceName = 'log-${resourceSuffix}'
var applicationInsightsName = 'ai-${resourceSuffix}'
var managedIdentityName = 'id-${resourceSuffix}'

// Common tags
var commonTags = {
  Environment: environmentName
  Application: 'OSINT-Platform'
  'Cost-Center': 'Security'
}

// User-assigned managed identity
resource managedIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: managedIdentityName
  location: location
  tags: commonTags
}

// Log Analytics Workspace
resource logAnalyticsWorkspace 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: logAnalyticsWorkspaceName
  location: location
  tags: commonTags
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
    features: {
      searchVersion: 1
      legacy: 0
      enableLogAccessUsingOnlyResourcePermissions: true
    }
  }
}

// Application Insights
resource applicationInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: applicationInsightsName
  location: location
  tags: commonTags
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalyticsWorkspace.id
    IngestionMode: 'LogAnalytics'
    publicNetworkAccessForIngestion: 'Enabled'
    publicNetworkAccessForQuery: 'Enabled'
  }
}

// Key Vault
resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: keyVaultName
  location: location
  tags: commonTags
  properties: {
    sku: {
      family: 'A'
      name: 'standard'
    }
    tenantId: tenant().tenantId
    enableRbacAuthorization: true
    enableSoftDelete: true
    softDeleteRetentionInDays: 7
    enablePurgeProtection: true
    networkAcls: {
      defaultAction: 'Allow'
      bypass: 'AzureServices'
    }
  }
}

// Grant Key Vault access to managed identity
resource keyVaultAccessPolicy 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: keyVault
  name: guid(keyVault.id, managedIdentity.id, 'Key Vault Secrets User')
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '4633458b-17de-408a-b874-0445c86b69e6') // Key Vault Secrets User
    principalId: managedIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

// Store database password in Key Vault
resource dbPasswordSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'database-password'
  properties: {
    value: dbAdminPassword
    contentType: 'text/plain'
  }
}

// Service Bus Namespace
resource serviceBusNamespace 'Microsoft.ServiceBus/namespaces@2023-01-01-preview' = {
  name: serviceBusNamespaceName
  location: location
  tags: commonTags
  sku: {
    name: 'Standard'
    tier: 'Standard'
  }
  properties: {
    minimumTlsVersion: '1.2'
    publicNetworkAccess: 'Enabled'
    disableLocalAuth: false
  }
}

// Service Bus Queue for data collection jobs
resource dataCollectionQueue 'Microsoft.ServiceBus/namespaces/queues@2023-01-01-preview' = {
  parent: serviceBusNamespace
  name: 'data-collection'
  properties: {
    lockDuration: 'PT5M'
    maxSizeInMegabytes: 1024
    requiresDuplicateDetection: false
    requiresSession: false
    defaultMessageTimeToLive: 'P14D'
    deadLetteringOnMessageExpiration: true
    duplicateDetectionHistoryTimeWindow: 'PT10M'
    maxDeliveryCount: 3
    enablePartitioning: false
    enableExpress: false
  }
}

// Service Bus Queue for threat analysis jobs
resource threatAnalysisQueue 'Microsoft.ServiceBus/namespaces/queues@2023-01-01-preview' = {
  parent: serviceBusNamespace
  name: 'threat-analysis'
  properties: {
    lockDuration: 'PT5M'
    maxSizeInMegabytes: 1024
    requiresDuplicateDetection: false
    requiresSession: false
    defaultMessageTimeToLive: 'P14D'
    deadLetteringOnMessageExpiration: true
    duplicateDetectionHistoryTimeWindow: 'PT10M'
    maxDeliveryCount: 3
    enablePartitioning: false
    enableExpress: false
  }
}

// PostgreSQL Flexible Server using Azure Verified Module
module postgresServer 'br/public:avm/res/db-for-postgre-sql/flexible-server:0.4.0' = {
  name: 'postgres-deployment'
  params: {
    name: postgresServerName
    location: location
    availabilityZone: 1
    skuName: 'Standard_B2s'
    tier: 'Burstable'
    administratorLogin: dbAdminUsername
    administratorLoginPassword: dbAdminPassword
    version: '15'
    storageSizeGB: 128
    backupRetentionDays: 7
    geoRedundantBackup: 'Disabled'
    highAvailability: 'Disabled'
    autoGrow: 'Enabled'
    publicNetworkAccess: 'Enabled'
    serverThreatProtection: 'Enabled'
    tags: commonTags
    
    // Create required databases
    databases: [
      {
        name: 'osint_main'
        charset: 'UTF8'
        collation: 'en_US.utf8'
      }
    ]
    
    // Configure firewall rules to allow Azure services
    firewallRules: [
      {
        name: 'AllowAllWindowsAzureIps'
        startIpAddress: '0.0.0.0'
        endIpAddress: '0.0.0.0'
      }
    ]
    
    // Diagnostic settings
    diagnosticSettings: [
      {
        workspaceResourceId: logAnalyticsWorkspace.id
        metricCategories: [
          {
            category: 'AllMetrics'
          }
        ]
      }
    ]
  }
}

// Container Apps Environment
resource containerAppEnvironment 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: containerAppEnvironmentName
  location: location
  tags: commonTags
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalyticsWorkspace.properties.customerId
        sharedKey: logAnalyticsWorkspace.listKeys().primarySharedKey
      }
    }
    infrastructureResourceGroup: 'ME_${resourceGroup().name}_${location}'
  }
}

// Backend Container App using Azure Verified Module
module backendApp 'br/public:avm/res/app/container-app:0.11.0' = {
  name: 'backend-deployment'
  params: {
    name: backendAppName
    location: location
    environmentResourceId: containerAppEnvironment.id
    managedIdentities: {
      userAssignedResourceIds: [
        managedIdentity.id
      ]
    }
    
    containers: [
      {
        name: 'osint-backend'
        image: 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest' // Placeholder - will be replaced with actual image
        resources: {
          cpu: '0.5'
          memory: '1.0Gi'
        }
        env: [
          {
            name: 'DATABASE_URL'
            value: 'postgresql://${dbAdminUsername}:${dbAdminPassword}@${postgresServer.outputs.fqdn}:5432/osint_main?sslmode=require'
          }
          {
            name: 'AZURE_CLIENT_ID'
            value: managedIdentity.properties.clientId
          }
          {
            name: 'KEY_VAULT_URL'
            value: keyVault.properties.vaultUri
          }
          {
            name: 'SERVICE_BUS_NAMESPACE'
            value: '${serviceBusNamespaceName}.servicebus.windows.net'
          }
          {
            name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
            value: applicationInsights.properties.ConnectionString
          }
        ]
      }
    ]
    
    scaleSettings: {
      minReplicas: 1
      maxReplicas: 10
    }
    
    ingressExternal: true
    ingressTargetPort: 8000
    ingressAllowInsecure: false
    
    tags: commonTags
  }
}

// Frontend Container App using Azure Verified Module
module frontendApp 'br/public:avm/res/app/container-app:0.11.0' = {
  name: 'frontend-deployment'
  params: {
    name: frontendAppName
    location: location
    environmentResourceId: containerAppEnvironment.id
    
    containers: [
      {
        name: 'osint-frontend'
        image: 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest' // Placeholder - will be replaced with actual image
        resources: {
          cpu: '0.25'
          memory: '0.5Gi'
        }
        env: [
          {
            name: 'REACT_APP_API_URL'
            value: 'https://${backendApp.outputs.fqdn}'
          }
        ]
      }
    ]
    
    scaleSettings: {
      minReplicas: 1
      maxReplicas: 5
    }
    
    ingressExternal: true
    ingressTargetPort: 3000
    ingressAllowInsecure: false
    
    tags: commonTags
  }
}

// Service Bus role assignment for backend app
resource serviceBusDataOwnerRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: serviceBusNamespace
  name: guid(serviceBusNamespace.id, managedIdentity.id, 'Azure Service Bus Data Owner')
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '090c5cfd-751d-490a-894a-3ce6f1109419') // Azure Service Bus Data Owner
    principalId: managedIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

// Outputs
output resourceGroupName string = resourceGroup().name
output containerAppEnvironmentName string = containerAppEnvironment.name
output backendUrl string = 'https://${backendApp.outputs.fqdn}'
output frontendUrl string = 'https://${frontendApp.outputs.fqdn}'
output postgresServerName string = postgresServer.outputs.name
output postgresServerFQDN string = postgresServer.outputs.fqdn
output keyVaultName string = keyVault.name
output keyVaultUri string = keyVault.properties.vaultUri
output serviceBusNamespaceName string = serviceBusNamespace.name
output managedIdentityClientId string = managedIdentity.properties.clientId
output applicationInsightsConnectionString string = applicationInsights.properties.ConnectionString
