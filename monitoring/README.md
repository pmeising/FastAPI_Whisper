# Monitoring Infrastructure

This directory contains the monitoring stack configuration for the Whisper API service.

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Monitoring Flow                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Whisper API           Prometheus            Grafana        │
│  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐  │
│  │             │      │             │      │             │  │
│  │ /metrics    │────▶ │ Scraper     │────▶ │ Dashboard   │  │
│  │ endpoint    │      │ TSDB        │      │ Alerts      │  │
│  │             │      │ Rules       │      │ Query UI    │  │
│  └─────────────┘      └─────────────┘      └─────────────┘  │
│       │                      │                      │       │
│       ▼                      ▼                      ▼       │
│  Application            Time Series            Visualization │
│  Metrics               Database                 & Alerting   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## 📁 Directory Structure

```
monitoring/
├── prometheus.yml                    # Prometheus configuration
└── grafana/
    ├── provisioning/
    │   ├── datasources/
    │   │   └── prometheus.yml       # Auto-configure Prometheus datasource
    │   └── dashboards/
    │       └── dashboard.yml        # Dashboard provisioning config
    └── dashboards/
        └── whisper-dashboard.json   # Pre-built Whisper performance dashboard
```

## 🎯 Prometheus Configuration

### Scrape Targets
- **whisper-api:8000/metrics**: Application metrics every 5 seconds
- **localhost:9090**: Prometheus self-monitoring

### Key Metrics Collected
```yaml
# Request metrics
whisper_transcription_requests_total
whisper_transcription_errors_total

# Performance metrics  
whisper_transcription_duration_seconds_bucket
whisper_inference_duration_seconds_bucket
whisper_audio_load_duration_seconds_bucket
whisper_processing_duration_seconds_bucket
whisper_decode_duration_seconds_bucket

# System metrics
whisper_model_loaded
```

### Data Retention
- **Retention**: 200 hours
- **Scrape interval**: 15 seconds (5 seconds for API)
- **Evaluation interval**: 15 seconds

## 📊 Grafana Configuration

### Pre-configured Components

#### Datasources
- **Prometheus**: Automatically configured to connect to Prometheus container
- **URL**: `http://prometheus:9090`
- **Access**: Server-side proxy

#### Dashboards
The Whisper Performance Dashboard includes:

1. **Transcription Duration Panel**
   - 95th and 50th percentile response times
   - Time series visualization
   - 5-minute rate windows

2. **Request Rate Panel** 
   - Requests per second
   - Real-time stat display
   - Color-coded thresholds

3. **Performance Breakdown Panel**
   - Individual operation timings
   - Audio loading, processing, inference, decode
   - Comparative analysis

### Dashboard Features
- **Auto-refresh**: 5-second intervals
- **Time range**: Last 15 minutes (configurable)
- **Responsive**: Works on desktop and mobile
- **Exportable**: JSON format for sharing

## 🔧 Customization

### Adding New Metrics

1. **In the API** (`app.py`):
```python
from prometheus_client import Counter, Histogram, Gauge

# Define your metric
NEW_METRIC = Counter('new_metric_name', 'Description')

# Use in code
NEW_METRIC.inc()
```

2. **Prometheus automatically discovers** new metrics from `/metrics` endpoint

3. **In Grafana**: Create new panels using PromQL queries

### Creating New Dashboards

1. **Manual approach**:
   - Access Grafana UI at http://localhost:3000
   - Create dashboard manually
   - Export as JSON
   - Save to `grafana/dashboards/`

2. **Programmatic approach**:
   - Modify `whisper-dashboard.json`
   - Add panels to the `panels` array
   - Restart Grafana container

### Alert Configuration

Example alert rule for high error rate:
```yaml
# Add to prometheus.yml
rule_files:
  - "alert_rules.yml"

# Create alert_rules.yml
groups:
  - name: whisper_alerts
    rules:
      - alert: HighErrorRate
        expr: rate(whisper_transcription_errors_total[5m]) > 0.1
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "High error rate in Whisper API"
```

## 🚀 Operational Guide

### Starting the Stack
```bash
docker-compose up -d
```

### Accessing Services
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (admin/grafana)

### Useful Prometheus Queries

```promql
# Request rate
rate(whisper_transcription_requests_total[5m])

# 95th percentile latency
histogram_quantile(0.95, rate(whisper_transcription_duration_seconds_bucket[5m]))

# Error percentage
rate(whisper_transcription_errors_total[5m]) / rate(whisper_transcription_requests_total[5m]) * 100

# Average inference time
rate(whisper_inference_duration_seconds_sum[5m]) / rate(whisper_inference_duration_seconds_count[5m])
```

### Troubleshooting

#### Prometheus not scraping metrics
1. Check if API is exposing `/metrics`: `curl http://localhost:8000/metrics`
2. Verify Prometheus config: `docker-compose logs prometheus`
3. Check targets in Prometheus UI: Status → Targets

#### Grafana not showing data
1. Verify datasource connection: Configuration → Data Sources
2. Test queries in Prometheus UI first
3. Check dashboard time range matches data availability

#### Missing dashboards
1. Verify file permissions on `grafana/dashboards/`
2. Check provisioning logs: `docker-compose logs grafana`
3. Restart Grafana: `docker-compose restart grafana`

## 📈 Performance Tuning

### High-throughput scenarios
- Increase Prometheus retention
- Adjust scrape intervals
- Use recording rules for complex queries

### Resource optimization
- Limit Prometheus memory: `--storage.tsdb.retention.size=1GB`
- Reduce Grafana refresh rates
- Archive old dashboards

## 🔄 Next Steps

For production deployment:
1. **External storage**: Configure Prometheus remote storage
2. **High availability**: Deploy Prometheus in HA mode
3. **Alerting**: Configure Alertmanager for notifications
4. **Security**: Add authentication and TLS
5. **Backup**: Regular dashboard and configuration backups
