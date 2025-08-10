#!/bin/bash

echo "🚀 Starting Whisper API with Monitoring Stack..."

# Build and start all services
docker-compose up --build -d

echo "⏳ Waiting for services to start..."
sleep 30

echo "✅ Services started!"
echo ""
echo "📊 Access your services:"
echo "   • Whisper API: http://localhost:8000"
echo "   • API Documentation: http://localhost:8000/docs"
echo "   • Prometheus: http://localhost:9090"
echo "   • Grafana: http://localhost:3000 (admin/grafana)"
echo ""
echo "📈 Grafana has been pre-configured with:"
echo "   • Prometheus datasource"
echo "   • Whisper API Performance Dashboard"
echo ""
echo "🔍 To view logs:"
echo "   docker-compose logs -f whisper-api"
echo ""
echo "🛑 To stop all services:"
echo "   docker-compose down"
