#!/bin/bash
# Quick script to start ngrok tunnel

echo "🚀 Starting ngrok tunnel for backend on port 8000..."
echo ""
echo "After ngrok starts, you'll see:"
echo "  - Forwarding URL (copy this!)"
echo "  - Web Interface: http://localhost:4040"
echo ""
echo "Press Ctrl+C to stop ngrok"
echo ""

ngrok http 8000
