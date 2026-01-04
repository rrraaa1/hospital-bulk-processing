# Hospital Bulk Processing System

A production-ready FastAPI application for bulk hospital CSV uploads, integrating with the Hospital Directory API.

## 🏗️ Architecture

The system follows a modular architecture with clear separation of concerns:

```
app/
├── main.py                 # FastAPI application and endpoints
├── models.py               # Pydantic models for validation
├── config.py              # Configuration management
└── services/
    ├── csv_processor.py   # CSV validation and parsing
    ├── hospital_client.py # Hospital API integration
    └── batch_manager.py   # Batch tracking and state management
```

## ✨ Features

- **Bulk CSV Upload**: Process up to 20 hospitals per batch
- **Comprehensive Validation**: CSV format and data validation before processing
- **Batch Management**: Track processing progress and results
- **Error Handling**: Robust error handling with detailed error messages
- **Retry Logic**: Automatic retries for failed API calls
- **Progress Tracking**: Real-time batch status monitoring
- **Docker Support**: Containerized deployment with Docker and Docker Compose
- **Full Test Coverage**: Unit and integration tests

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- pip
- Docker (optional, for containerized deployment)

### Local Development Setup

1. **Clone the repository**
```bash
git clone <repository-url>
cd hospital-bulk-processing
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Run the application**
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

5. **Access the API**
- API Documentation: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

### Docker Deployment

1. **Build and run with Docker Compose**
```bash
docker-compose up -d
```

2. **View logs**
```bash
docker-compose logs -f
```

3. **Stop the service**
```bash
docker-compose down
```

### Manual Docker Build

```bash
docker build -t hospital-bulk-api .
docker run -p 8000:8000 hospital-bulk-api
```

## 📋 API Endpoints

### 1. Bulk Upload Hospitals

**Endpoint**: `POST /hospitals/bulk`

**Description**: Upload a CSV file to create multiple hospitals in a single batch.

**Request**:
- Multipart form data
- File field: `file` (CSV format)

**CSV Format**:
```csv
name,address,phone
General Hospital,123 Main St,555-1234
City Hospital,456 Oak Ave,555-5678
```

**Response**:
```json
{
  "batch_id": "550e8400-e29b-41d4-a716-446655440000",
  "total_hospitals": 2,
  "processed_hospitals": 2,
  "failed_hospitals": 0,
  "processing_time_seconds": 2.5,
  "batch_activated": true,
  "hospitals": [
    {
      "row": 1,
      "hospital_id": 101,
      "name": "General Hospital",
      "status": "created_and_activated"
    }
  ]
}
```

**Example using curl**:
```bash
curl -X POST "http://localhost:8000/hospitals/bulk" \
  -H "accept: application/json" \
  -F "file=@hospitals.csv"
```

### 2. Validate CSV

**Endpoint**: `POST /hospitals/validate`

**Description**: Validate CSV format without creating hospitals.

**Request**:
- Multipart form data
- File field: `file` (CSV format)

**Response**:
```json
{
  "is_valid": true,
  "total_rows": 2,
  "errors": [],
  "warnings": []
}
```

### 3. Get Batch Status

**Endpoint**: `GET /hospitals/batch/{batch_id}/status`

**Description**: Get current processing status of a batch.

**Response**:
```json
{
  "batch_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "total_hospitals": 2,
  "processed_hospitals": 2,
  "progress_percentage": 100.0,
  "created_at": "2025-01-03T10:30:00Z",
  "completed_at": "2025-01-03T10:30:05Z"
}
```

### 4. Get Batch Results

**Endpoint**: `GET /hospitals/batch/{batch_id}/results`

**Description**: Get detailed results for a completed batch.

**Response**:
```json
{
  "batch_id": "550e8400-e29b-41d4-a716-446655440000",
  "total_hospitals": 2,
  "processed_hospitals": 2,
  "failed_hospitals": 0,
  "processing_time_seconds": 2.5,
  "batch_activated": true,
  "hospitals": [...]
}
```

## 🧪 Testing

### Run all tests
```bash
pytest
```

### Run with coverage
```bash
pytest --cov=app --cov-report=html
```

### Run specific test file
```bash
pytest tests/test_csv_processor.py -v
```

### Run integration tests only
```bash
pytest tests/test_integration.py -v
```

## 📝 CSV File Format

### Required Columns
- `name`: Hospital name (max 200 characters)
- `address`: Hospital address (max 500 characters)

### Optional Columns
- `phone`: Phone number (max 20 characters)

### Example CSV
```csv
name,address,phone
General Hospital,123 Main St,555-1234
City Hospital,456 Oak Ave,555-5678
Memorial Hospital,789 Elm St,
```

### Validation Rules
- Headers must include `name` and `address`
- Name and address cannot be empty
- Maximum 20 hospitals per batch
- UTF-8 encoding with optional BOM support

## 🔧 Configuration

Configuration can be set via environment variables or `.env` file:

```env
HOSPITAL_API_URL=https://hospital-directory.onrender.com
MAX_HOSPITALS_PER_BATCH=20
API_TIMEOUT=30
MAX_RETRIES=3
DEBUG=false
```

### Configuration Options

| Variable | Description | Default |
|----------|-------------|---------|
| `HOSPITAL_API_URL` | Hospital Directory API base URL | Required |
| `MAX_HOSPITALS_PER_BATCH` | Maximum hospitals per upload | 20 |
| `API_TIMEOUT` | HTTP request timeout (seconds) | 30 |
| `MAX_RETRIES` | Retry attempts for failed requests | 3 |
| `DEBUG` | Enable debug mode | false |

## 🌐 Deployment to Render

### Method 1: Render Blueprint (Recommended)

1. Create `render.yaml` in project root:

```yaml
services:
  - type: web
    name: hospital-bulk-api
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn app.main:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: HOSPITAL_API_URL
        value: https://hospital-directory.onrender.com
      - key: MAX_HOSPITALS_PER_BATCH
        value: 20
      - key: PYTHON_VERSION
        value: 3.11.0
```

2. Connect your GitHub repository to Render
3. Deploy automatically from the blueprint

### Method 2: Manual Render Deployment

1. Go to [Render Dashboard](https://dashboard.render.com/)
2. Click "New +" → "Web Service"
3. Connect your Git repository
4. Configure:
   - **Name**: hospital-bulk-api
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Add environment variables
6. Click "Create Web Service"

### Method 3: Deploy to Railway

1. Install Railway CLI:
```bash
npm install -g @railway/cli
```

2. Login and deploy:
```bash
railway login
railway init
railway up
```

## 📊 Processing Workflow

1. **Upload**: User uploads CSV file
2. **Validation**: System validates CSV format and content
3. **Batch Creation**: Generate unique batch ID
4. **Hospital Creation**: Create each hospital via API calls
   - Retry on failures (up to 3 attempts)
   - Track progress in real-time
5. **Batch Activation**: Activate all hospitals once created
6. **Results**: Return comprehensive processing results

## 🔍 Error Handling

The system handles various error scenarios:

- **CSV Validation Errors**: Invalid format, missing columns, empty fields
- **Network Errors**: Connection failures, timeouts
- **API Errors**: Hospital API failures, rate limits
- **Processing Errors**: Partial batch failures

Each error includes detailed information to help diagnose issues.

## 📈 Performance Considerations

- **Async Processing**: Uses httpx for async HTTP requests
- **Retry Logic**: Automatic retries with exponential backoff
- **Batch Limits**: Maximum 20 hospitals per batch to prevent timeouts
- **Connection Pooling**: Efficient HTTP connection management
- **In-Memory Storage**: Fast batch tracking without database overhead

## 🛡️ Security

- **Input Validation**: Pydantic models for request validation
- **File Type Checking**: Only CSV files accepted
- **Size Limits**: Configurable file size limits
- **Non-Root Container**: Docker container runs as non-root user
- **Health Checks**: Container health monitoring

## 📚 Project Structure

```
hospital-bulk-processing/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application
│   ├── models.py               # Pydantic models
│   ├── config.py              # Configuration
│   └── services/
│       ├── __init__.py
│       ├── csv_processor.py   # CSV processing
│       ├── hospital_client.py # API client
│       └── batch_manager.py   # Batch management
├── tests/
│   ├── __init__.py
│   ├── test_csv_processor.py
│   └── test_integration.py
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .env.example
└── README.md
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run tests: `pytest`
6. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details

## 🐛 Troubleshooting

### Issue: Connection refused to Hospital API

**Solution**: Check if HOSPITAL_API_URL is correct and the API is accessible:
```bash
curl https://hospital-directory.onrender.com/hospitals/
```

### Issue: CSV validation fails

**Solution**: Ensure CSV has required columns (name, address) and proper encoding (UTF-8)

### Issue: Batch not activating

**Solution**: Check logs for API errors. Some hospitals may have failed creation.

### Issue: Docker container fails to start

**Solution**: Check logs:
```bash
docker-compose logs api
```

## 📞 Support

For issues or questions:
1. Check the [Issues](https://github.com/your-repo/issues) page
2. Review API documentation at `/docs` endpoint
3. Check logs for detailed error messages

## 🎯 Future Enhancements

- WebSocket support for real-time progress updates
- Database persistence for batch history
- Resume capability for failed batches
- Advanced filtering and search
- Export batch results to various formats
- Rate limiting and quota management
- Multi-tenant support