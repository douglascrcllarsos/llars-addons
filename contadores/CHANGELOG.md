# Changelog

## 0.2.0 — 2026-10-01

Varios módulos WJ69 pueden colgar del mismo conversor USR-DR134: basta con
declararlos con el mismo `host` y `puerto` y distinta `direccion`. El add-on
abre una sola conexión por conversor y consulta sus módulos en serie, con un
breve silencio entre tramas. Antes se rechazaba el `host:puerto` repetido;
ahora solo se rechaza repetir la misma dirección en el mismo conversor.

## 0.1.1 — 2026-09-25

Los entity_id salen del nombre del canal a secas (object_id en el discovery),
sin el prefijo del dispositivo que HA añade por defecto, y las entidades de
módulo (Conexión, Último corte) dejan de duplicar el nombre del módulo.
Tras actualizar hay que purgar los retained de discovery y reiniciar el
add-on para que las entidades renazcan con el id nuevo.

## 0.1.0 — 2026-09-25

Primera versión: lectura de módulos WJ69-485 vía USR-DR134 (Modbus RTU sobre
TCP), acumulado a prueba de cortes en /data y entidades por MQTT discovery.
