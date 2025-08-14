#!/bin/bash

echo "🚀 Starting Whisper API..."

# Build and start the service
docker-compose up --build -d

echo "⏳ Waiting for service to start..."
sleep 15

echo "✅ Whisper API started!"
echo ""
echo "📊 Access your service:"
echo "   • Whisper API: http://localhost:8000"
echo "   • API Documentation: http://localhost:8000/docs"
echo "   • Metrics Endpoint: http://localhost:8000/metrics"
echo ""
echo "📈 For monitoring, start the centralized monitoring stack:"
echo "   • Navigate to: ../Monitoring_Stack/"
echo "   • Run: ./start-monitoring.sh"
echo "   • Access Grafana: http://localhost:3000 (admin/grafana)"
echo ""
echo "� The centralized monitoring will automatically discover this service."
echo "   • Whisper API Performance Dashboard"
echo ""
echo "🔍 To view logs:"
echo "   docker-compose logs -f whisper-api"
echo ""
echo "🛑 To stop all services:"
echo "   docker-compose down"
