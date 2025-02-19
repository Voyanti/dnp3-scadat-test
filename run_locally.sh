#!/bin/bash
echo ""

echo "LOCAL Start Mosquitto in the background"
echo ""
mosquitto -p 1884 -d
# MOSQUITTO_PID=$!

echo "Hello DNP3"
echo "---"

python3 -m src.app config.yaml

echo "LOCAL Stop Mosquitto"
echo ""
kill $(pgrep -f "mosquitto -p 1884")