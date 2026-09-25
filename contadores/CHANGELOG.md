# Changelog


## 0.1.1 — 2026-09-25

Los entity_id salen del nombre del canal a secas (object_id en el discovery),
sin el prefijo del dispositivo que HA añade por defecto, y las entidades de
módulo (Conexión, Último corte) dejan de duplicar el nombre del módulo.
Tras actualizar hay que purgar los retained de discovery y reiniciar el
add-on para que las entidades renazcan con el id nuevo.

## 0.1.0 — 2026-09-25

Primera versión: lectura de módulos WJ69-485 vía USR-DR134 (Modbus RTU sobre
TCP), acumulado a prueba de cortes en /data y entidades por MQTT discovery.
