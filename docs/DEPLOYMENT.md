# Deployment Guide

This guide provides comprehensive instructions for deploying the OpenEdu MCP Server in various environments, from development to production.

## 📋 Overview

The OpenEdu MCP Server can be deployed in multiple ways:
- **Local Development**: Direct Python execution
- **Docker Container**: Containerized deployment
- **Cloud Platforms**: AWS, GCP, Azure deployment
- **Kubernetes**: Scalable container orchestration
- **Edge Deployment**: Local network deployment

## 🚀 Quick Deployment

### Local Development Deployment

The fastest way to get started:

```bash
# Clone the repository
git clone <repository-url>
cd openedu-mcp

# Install dependencies
pip install -r requirements.txt

# Run the server
python -m src.main
```

### Docker Deployment

```bash
# Build the image
docker build -t openedu-mcp-server .

# Run the container
docker run -p 8000:8000 openedu-mcp-server
```

## 🐳 Docker Deployment

### Dockerfile

Create a `Dockerfile` in the project root:

```dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY config/ ./config/
COPY pyproject.toml .

# Create directories for data
RUN mkdir -p /app/data/cache /app/data/logs

# Set environment variables
ENV PYTHONPATH=/app
ENV OPENEDU_MCP_CACHE_PATH=/app/data/cache/cache.db
ENV OPENEDU_MCP_LOG_PATH=/app/data/logs/server.log

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

# Run the server
CMD ["python", "-m", "src.main"]
```

### Docker Compose

Create a `docker-compose.yml` for complete deployment:

```yaml
version: '3.8'

services:
  openedu-mcp-server:
    build: .
    ports:
      - "8000:8000"
    environment:
      - OPENEDU_MCP_LOG_LEVEL=INFO
      - OPENEDU_MCP_CACHE_TTL=3600
      - OPENEDU_MCP_WIKIPEDIA_RATE_LIMIT=200
    volumes:
      - ./data:/app/data
      - ./config:/app/config
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "python", "-c", "import requests; requests.get('http://localhost:8000/health')"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  # Optional: Add monitoring
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana-storage:/var/lib/grafana

volumes:
  grafana-storage:
```

### Build and Deploy

```bash
# Build and start services
docker-compose up -d

# View logs
docker-compose logs -f openedu-mcp-server

# Scale the service
docker-compose up -d --scale openedu-mcp-server=3

# Stop services
docker-compose down
```

## ☁️ Cloud Platform Deployment

### AWS Deployment

#### Using AWS ECS (Elastic Container Service)

1. **Create ECR Repository:**
```bash
# Create repository
aws ecr create-repository --repository-name openedu-mcp-server

# Get login token
aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-west-2.amazonaws.com

# Build and push image
docker build -t openedu-mcp-server .
docker tag openedu-mcp-server:latest <account-id>.dkr.ecr.us-west-2.amazonaws.com/openedu-mcp-server:latest
docker push <account-id>.dkr.ecr.us-west-2.amazonaws.com/openedu-mcp-server:latest
```

2. **Create ECS Task Definition:**
```json
{
    "family": "openedu-mcp-server",
    "networkMode": "awsvpc",
    "requiresCompatibilities": ["FARGATE"],
    "cpu": "512",
    "memory": "1024",
    "executionRoleArn": "arn:aws:iam::<account-id>:role/ecsTaskExecutionRole",
    "containerDefinitions": [
        {
            "name": "openedu-mcp-server",
            "image": "<account-id>.dkr.ecr.us-west-2.amazonaws.com/openedu-mcp-server:latest",
            "portMappings": [
                {
                    "containerPort": 8000,
                    "protocol": "tcp"
                }
            ],
            "environment": [
                {
                    "name": "OPENEDU_MCP_LOG_LEVEL",
                    "value": "INFO"
                }
            ],
            "logConfiguration": {
                "logDriver": "awslogs",
                "options": {
                    "awslogs-group": "/ecs/openedu-mcp-server",
                    "awslogs-region": "us-west-2",
                    "awslogs-stream-prefix": "ecs"
                }
            }
        }
    ]
}
```

3. **Create ECS Service:**
```bash
aws ecs create-service \
    --cluster openedu-mcp-cluster \
    --service-name openedu-mcp-service \
    --task-definition openedu-mcp-server \
    --desired-count 2 \
    --launch-type FARGATE \
    --network-configuration "awsvpcConfiguration={subnets=[subnet-12345],securityGroups=[sg-12345],assignPublicIp=ENABLED}"
```

#### Using AWS Lambda (Serverless)

Create a `serverless.yml` for serverless deployment:

```yaml
service: openedu-mcp-server

provider:
  name: aws
  runtime: python3.11
  region: us-west-2
  timeout: 30
  memorySize: 1024
  environment:
    OPENEDU_MCP_CACHE_PATH: /tmp/cache.db
    OPENEDU_MCP_LOG_LEVEL: INFO

functions:
  server:
    handler: src.lambda_handler.handler
    events:
      - http:
          path: /{proxy+}
          method: ANY
          cors: true
    layers:
      - arn:aws:lambda:us-west-2:123456789012:layer:openedu-mcp-deps:1

plugins:
  - serverless-python-requirements

custom:
  pythonRequirements:
    dockerizePip: true
    layer: true
```

### Google Cloud Platform (GCP)

#### Using Cloud Run

1. **Build and push to Container Registry:**
```bash
# Configure Docker for GCP
gcloud auth configure-docker

# Build and push
docker build -t gcr.io/PROJECT-ID/openedu-mcp-server .
docker push gcr.io/PROJECT-ID/openedu-mcp-server
```

2. **Deploy to Cloud Run:**
```bash
gcloud run deploy openedu-mcp-server \
    --image gcr.io/PROJECT-ID/openedu-mcp-server \
    --platform managed \
    --region us-central1 \
    --allow-unauthenticated \
    --memory 1Gi \
    --cpu 1 \
    --max-instances 10 \
    --set-env-vars OPENEDU_MCP_LOG_LEVEL=INFO
```

#### Using Google Kubernetes Engine (GKE)

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: openedu-mcp-server
spec:
  replicas: 3
  selector:
    matchLabels:
      app: openedu-mcp-server
  template:
    metadata:
      labels:
        app: openedu-mcp-server
    spec:
      containers:
      - name: openedu-mcp-server
        image: gcr.io/PROJECT-ID/openedu-mcp-server
        ports:
        - containerPort: 8000
        env:
        - name: OPENEDU_MCP_LOG_LEVEL
          value: "INFO"
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
---
apiVersion: v1
kind: Service
metadata:
  name: openedu-mcp-service
spec:
  selector:
    app: openedu-mcp-server
  ports:
  - port: 80
    targetPort: 8000
  type: LoadBalancer
```

### Microsoft Azure

#### Using Azure Container Instances

```bash
# Create resource group
az group create --name openedu-mcp-rg --location eastus

# Create container instance
az container create \
    --resource-group openedu-mcp-rg \
    --name openedu-mcp-server \
    --image openedu-mcp-server:latest \
    --cpu 1 \
    --memory 1 \
    --ports 8000 \
    --environment-variables OPENEDU_MCP_LOG_LEVEL=INFO \
    --restart-policy Always
```

## ⚙️ Configuration Management

### Environment Variables

The server supports configuration through environment variables:

```bash
# Server configuration
export OPENEDU_MCP_HOST=0.0.0.0
export OPENEDU_MCP_PORT=8000
export OPENEDU_MCP_LOG_LEVEL=INFO

# Cache configuration
export OPENEDU_MCP_CACHE_PATH=/app/data/cache.db
export OPENEDU_MCP_CACHE_TTL=3600
export OPENEDU_MCP_CACHE_MAX_SIZE_MB=100

# API rate limits
export OPENEDU_MCP_WIKIPEDIA_RATE_LIMIT=200
export OPENEDU_MCP_OPEN_LIBRARY_RATE_LIMIT=100
export OPENEDU_MCP_DICTIONARY_RATE_LIMIT=450
export OPENEDU_MCP_ARXIV_RATE_LIMIT=3

# Educational settings
export OPENEDU_MCP_MIN_EDUCATIONAL_RELEVANCE=0.7
export OPENEDU_MCP_ENABLE_AGE_FILTERING=true
```

### Configuration Files

Create environment-specific configuration files:

```yaml
# config/production.yaml
server:
  host: "0.0.0.0"
  port: 8000
  log_level: "INFO"
  debug: false

cache:
  database_path: "/app/data/cache.db"
  default_ttl: 7200
  max_size_mb: 500
  cleanup_interval: 1800

apis:
  open_library:
    rate_limit: 150
    timeout: 45
  wikipedia:
    rate_limit: 300
    timeout: 45
  dictionary:
    rate_limit: 600
    timeout: 20
  arxiv:
    rate_limit: 5
    timeout: 90

education:
  content_filters:
    min_educational_relevance: 0.8
    enable_age_appropriate: true
    enable_curriculum_alignment: true

logging:
  level: "INFO"
  format: "json"
  file_path: "/app/data/logs/server.log"
  max_file_size_mb: 50
  backup_count: 10

monitoring:
  enable_metrics: true
  metrics_port: 9090
  health_check_interval: 30
```

### Secrets Management

#### Using Docker Secrets

```yaml
# docker-compose.yml
version: '3.8'

services:
  openedu-mcp-server:
    build: .
    secrets:
      - api_keys
    environment:
      - OPENEDU_MCP_API_KEYS_FILE=/run/secrets/api_keys

secrets:
  api_keys:
    file: ./secrets/api_keys.json
```

#### Using Kubernetes Secrets

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: openedu-mcp-secrets
type: Opaque
data:
  api-keys: <base64-encoded-json>
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: openedu-mcp-server
spec:
  template:
    spec:
      containers:
      - name: openedu-mcp-server
        env:
        - name: OPENEDU_MCP_API_KEYS
          valueFrom:
            secretKeyRef:
              name: openedu-mcp-secrets
              key: api-keys
```

## 📊 Monitoring and Logging

### Health Checks

The server provides health check endpoints:

```python
# Health check endpoint
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }

# Readiness check
@app.get("/ready")
async def readiness_check():
    # Check database connectivity
    # Check external API availability
    return {"status": "ready"}
```

### Prometheus Metrics

Configure Prometheus monitoring:

```yaml
# monitoring/prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'openedu-mcp-server'
    static_configs:
      - targets: ['openedu-mcp-server:9090']
    metrics_path: /metrics
    scrape_interval: 30s
```

### Logging Configuration

```python
# Structured logging configuration
import logging
import json
from datetime import datetime

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
            
        return json.dumps(log_entry)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    handlers=[
        logging.FileHandler('/app/data/logs/server.log'),
        logging.StreamHandler()
    ]
)

for handler in logging.root.handlers:
    handler.setFormatter(JSONFormatter())
```

### Grafana Dashboards

Create monitoring dashboards:

```json
{
  "dashboard": {
    "title": "OpenEdu MCP Server",
    "panels": [
      {
        "title": "Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(http_requests_total[5m])",
            "legendFormat": "{{method}} {{endpoint}}"
          }
        ]
      },
      {
        "title": "Response Time",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))",
            "legendFormat": "95th percentile"
          }
        ]
      },
      {
        "title": "Cache Hit Rate",
        "type": "stat",
        "targets": [
          {
            "expr": "cache_hit_rate",
            "legendFormat": "Hit Rate"
          }
        ]
      }
    ]
  }
}
```

## 🔒 Security

### SSL/TLS Configuration

#### Using Let's Encrypt with Nginx

```nginx
# /etc/nginx/sites-available/openedu-mcp-server
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
    ssl_prefer_server_ciphers off;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Authentication and Authorization

```python
# API key authentication
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def verify_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if credentials.credentials not in valid_api_keys:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return credentials.credentials

# Apply to routes
@app.get("/api/books", dependencies=[Depends(verify_api_key)])
async def search_books():
    pass
```

### Rate Limiting

```python
# Advanced rate limiting
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.get("/api/books")
@limiter.limit("100/minute")
async def search_books(request: Request):
    pass
```

## 🔧 Performance Optimization

### Database Optimization

```python
# SQLite optimization for production
import sqlite3

def optimize_database(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Enable WAL mode for better concurrency
    cursor.execute("PRAGMA journal_mode=WAL")
    
    # Optimize cache size
    cursor.execute("PRAGMA cache_size=10000")
    
    # Enable foreign keys
    cursor.execute("PRAGMA foreign_keys=ON")
    
    # Optimize synchronous mode
    cursor.execute("PRAGMA synchronous=NORMAL")
    
    conn.close()
```

### Caching Strategy

```python
# Multi-level caching
from functools import lru_cache
import redis

# In-memory cache for frequently accessed data
@lru_cache(maxsize=1000)
def get_grade_level_config(grade_level: str):
    return load_grade_level_config(grade_level)

# Redis cache for distributed deployment
redis_client = redis.Redis(host='redis', port=6379, db=0)

async def get_cached_result(key: str):
    # Try in-memory cache first
    if key in memory_cache:
        return memory_cache[key]
    
    # Try Redis cache
    result = redis_client.get(key)
    if result:
        return json.loads(result)
    
    return None
```

### Connection Pooling

```python
# HTTP connection pooling
import aiohttp
from aiohttp import TCPConnector

# Configure connection pool
connector = TCPConnector(
    limit=100,  # Total connection pool size
    limit_per_host=30,  # Per-host connection limit
    ttl_dns_cache=300,  # DNS cache TTL
    use_dns_cache=True,
    keepalive_timeout=30,
    enable_cleanup_closed=True
)

session = aiohttp.ClientSession(connector=connector)
```

## 🚨 Troubleshooting

### Common Issues

#### High Memory Usage

```bash
# Monitor memory usage
docker stats openedu-mcp-server

# Optimize cache size
export OPENEDU_MCP_CACHE_MAX_SIZE_MB=50

# Enable cache cleanup
export OPENEDU_MCP_CACHE_CLEANUP_INTERVAL=1800
```

#### Slow Response Times

```bash
# Check database performance
sqlite3 /app/data/cache.db "EXPLAIN QUERY PLAN SELECT * FROM cache WHERE key = 'test'"

# Monitor API response times
curl -w "@curl-format.txt" -o /dev/null -s "http://localhost:8000/api/books?query=test"
```

#### Rate Limit Errors

```bash
# Check rate limit status
curl http://localhost:8000/status | jq '.rate_limits'

# Adjust rate limits
export OPENEDU_MCP_WIKIPEDIA_RATE_LIMIT=300
```

### Debugging

```python
# Enable debug logging
import logging
logging.getLogger().setLevel(logging.DEBUG)

# Add request tracing
import uuid
from fastapi import Request

@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    
    logger.info(f"Request {request_id}: {request.method} {request.url}")
    
    response = await call_next(request)
    
    logger.info(f"Request {request_id}: Response {response.status_code}")
    
    return response
```

### Log Analysis

```bash
# Analyze error patterns
grep "ERROR" /app/data/logs/server.log | jq '.message' | sort | uniq -c

# Monitor response times
grep "Response" /app/data/logs/server.log | jq '.response_time' | awk '{sum+=$1; count++} END {print "Average:", sum/count}'

# Check cache performance
grep "cache" /app/data/logs/server.log | jq '.cache_hit' | grep -c "true"
```

## 📈 Scaling

### Horizontal Scaling

```yaml
# Kubernetes horizontal pod autoscaler
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: openedu-mcp-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: openedu-mcp-server
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

### Load Balancing

```nginx
# Nginx load balancer
upstream education_mcp_backend {
    least_conn;
    server openedu-mcp-1:8000 max_fails=3 fail_timeout=30s;
    server openedu-mcp-2:8000 max_fails=3 fail_timeout=30s;
    server openedu-mcp-3:8000 max_fails=3 fail_timeout=30s;
}

server {
    listen 80;
    
    location / {
        proxy_pass http://education_mcp_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        
        # Health checks
        proxy_next_upstream error timeout invalid_header http_500 http_502 http_503;
        proxy_connect_timeout 5s;
        proxy_send_timeout 10s;
        proxy_read_timeout 30s;
    }
    
    location /health {
        access_log off;
        proxy_pass http://education_mcp_backend;
    }
}
```

## 🔄 Backup and Recovery

### Database Backup

```bash
#!/bin/bash
# backup-script.sh

BACKUP_DIR="/app/backups"
DATE=$(date +%Y%m%d_%H%M%S)
DB_PATH="/app/data/cache.db"

# Create backup directory
mkdir -p $BACKUP_DIR

# Backup database
sqlite3 $DB_PATH ".backup $BACKUP_DIR/cache_backup_$DATE.db"

# Compress backup
gzip "$BACKUP_DIR/cache_backup_$DATE.db"

# Clean old backups (keep last 7 days)
find $BACKUP_DIR -name "cache_backup_*.db.gz" -mtime +7 -delete

echo "Backup completed: cache_backup_$DATE.db.gz"
```

### Automated Backups

```yaml
# Kubernetes CronJob for backups
apiVersion: batch/v1
kind: CronJob
metadata:
  name: openedu-mcp-backup
spec:
  schedule: "0 2 * * *"  # Daily at 2 AM
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: backup
            image: openedu-mcp-server:latest
            command: ["/bin/bash", "/app/scripts/backup.sh"]
            volumeMounts:
            - name: data-volume
              mountPath: /app/data
            - name: backup-volume
              mountPath: /app/backups
          restartPolicy: OnFailure
          volumes:
          - name: data-volume
            persistentVolumeClaim:
              claimName: openedu-mcp-data
          - name: backup-volume
            persistentVolumeClaim:
              claimName: openedu-mcp-backups
```

---

This deployment guide provides comprehensive instructions for deploying the OpenEdu MCP Server in various environments. Choose the deployment method that best fits your infrastructure and requirements.