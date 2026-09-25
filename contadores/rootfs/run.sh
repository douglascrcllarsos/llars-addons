#!/bin/sh
# run.sh — resuelve el servicio MQTT del Supervisor y arranca la app.
MQTT_JSON=$(wget -q -O- --header "Authorization: Bearer ${SUPERVISOR_TOKEN}" \
  http://supervisor/services/mqtt || echo '{}')
export MQTT_HOST="$(echo "$MQTT_JSON" | jq -r '.data.host // "core-mosquitto"')"
export MQTT_PORT="$(echo "$MQTT_JSON" | jq -r '.data.port // 1883')"
export MQTT_USER="$(echo "$MQTT_JSON" | jq -r '.data.username // empty')"
export MQTT_PASSWORD="$(echo "$MQTT_JSON" | jq -r '.data.password // empty')"
exec python3 /app/main.py
