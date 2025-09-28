# OSINT Data Collection & Analysis Platform

A comprehensive Open Source Intelligence (OSINT) platform for collecting, analyzing, and monitoring social media data from Facebook, Twitter/X, and Instagram.

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   React UI      │    │   FastAPI       │    │   PostgreSQL    │
│   Dashboard     │◄───┤   Backend       │◄───┤   Database      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                       ┌─────────────────┐
                       │   Azure         │
                       │   Services      │
                       │   • Key Vault   │
                       │   • Service Bus │
                       │   • Cognitive   │
                       │   • Functions   │
                       └─────────────────┘
```

## 🚀 Features

- **Data Collection**: Automated daily collection from social media APIs
- **Threat Detection**: AI-powered analysis for suspicious content
- **Trend Analysis**: Real-time monitoring of emerging patterns
- **Vulnerability Assessment**: Risk signal identification
- **Interactive Dashboard**: Web-based visualization and reporting

## 📁 Project Structure

```
osint-platform/
├── backend/           # FastAPI Python backend
│   ├── app/
│   │   ├── collectors/    # Social media data collectors
│   │   ├── analysis/      # AI/ML analysis modules
│   │   ├── models/        # Database models
│   │   ├── api/          # REST API endpoints
│   │   └── core/         # Core utilities and config
├── frontend/          # React TypeScript frontend
├── infra/            # Azure Bicep infrastructure
├── shared/           # Shared configurations and types
└── README.md
```

## 🛠️ Technology Stack

### Backend
- **FastAPI**: High-performance Python web framework
- **SQLAlchemy**: Database ORM
- **PostgreSQL**: Primary database
- **Azure SDK**: Cloud services integration
- **FastAPI BackgroundTasks**: Simple background processing

### Frontend
- **React 18**: UI framework
- **TypeScript**: Type-safe JavaScript
- **Material-UI**: Component library
- **React Query**: Data fetching and caching

### Infrastructure
- **Azure Container Apps**: Serverless containers
- **Azure Database for PostgreSQL**: Managed database
- **Azure Key Vault**: Secrets management
- **Azure Service Bus**: Message queuing
- **Azure Cognitive Services**: AI/ML capabilities
- **Azure Functions**: Serverless compute

## 🔐 Security Features

- **Managed Identity**: Credential-free Azure authentication
- **Key Vault Integration**: Secure secrets management
- **RBAC**: Role-based access control
- **Data Encryption**: End-to-end encryption
- **API Rate Limiting**: Protection against abuse

## 📊 Analysis Capabilities

### Threat Detection
- Keyword-based filtering
- Pattern recognition
- Link analysis and reputation checking
- Behavioral anomaly detection

### Trend Analysis
- Real-time content monitoring
- Sentiment analysis
- Geographic trend mapping
- Temporal pattern analysis

## 🚀 Quick Start

### Prerequisites
- Azure CLI
- Azure Developer CLI (azd)
- Python 3.11+
- Node.js 18+
- PostgreSQL (for local development)

### Deployment
```bash
# Clone the repository
git clone <repository-url>
cd osint-platform

# Deploy to Azure
azd up
```

### Local Development
```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm start
```

## 📝 Configuration

### Environment Variables
- `AZURE_CLIENT_ID`: Azure AD application ID
- `AZURE_TENANT_ID`: Azure AD tenant ID
- `DATABASE_URL`: PostgreSQL connection string
- `FACEBOOK_API_KEY`: Facebook Graph API key
- `TWITTER_API_KEY`: Twitter API v2 key
- `INSTAGRAM_API_KEY`: Instagram Basic Display API key

### Social Media API Setup
1. **Facebook**: Create app in Facebook Developer Console
2. **Twitter/X**: Apply for Twitter API v2 access
3. **Instagram**: Set up Instagram Basic Display API

## 🔍 Usage

### Dashboard Features
- **Real-time Monitoring**: Live feed of collected data
- **Threat Alerts**: Immediate notifications for suspicious content
- **Analytics Reports**: Comprehensive analysis summaries
- **Search & Filter**: Advanced content discovery tools

### API Endpoints
- `GET /api/v1/posts`: Retrieve collected social media posts
- `GET /api/v1/threats`: Access threat detection results
- `GET /api/v1/trends`: View trending topics and patterns
- `POST /api/v1/analyze`: Trigger manual analysis

## 📈 Monitoring & Observability

- **Application Insights**: Performance monitoring
- **Azure Monitor**: Infrastructure monitoring
- **Custom Dashboards**: Business metrics tracking
- **Alerting**: Automated incident response

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes with proper testing
4. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## ⚠️ Disclaimer

This platform is intended for legitimate security research and threat intelligence purposes only. Users are responsible for compliance with applicable laws and platform terms of service.

## 🆘 Support

For support and questions:
- Create an issue in the GitHub repository
- Review the documentation in `/docs`
- Check the troubleshooting guide

---

**Note**: This platform requires proper authorization and compliance with social media platform APIs and terms of service. Ensure you have appropriate permissions before collecting data.