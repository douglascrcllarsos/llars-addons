# Changelog

Todos los cambios notables en este proyecto están documentados en este archivo.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/),
y este proyecto se adhiere a [Versionado Semántico](https://semver.org/lang/es/).

## 0.5.2 — 2026-09-08

### Añadido
- Eventos de demanda en el registro de clima: transición de demanda por zona (fancoil y suelo, etiqueta DEMANDA) y eventos ESTADO (cambio de modo global, termostato caído/recuperado). El primer refresco tras arrancar fija la línea base sin anotar nada.
- «Antibloqueo de fancoils» configurable desde el panel: sección nueva al final del Avanzado de la tarjeta «Aerotermia y bombas» (solo en modo edición), guardada con el mismo Guardar del tablero. El generador del Visual siempre emite el bloque `impulso_fancoil`. Además, endpoints `GET/POST /api/clima/impulso_fancoil` para diagnóstico por curl (edición quirúrgica del YAML que preserva comentarios).
- Registro de clima como subpestaña del Panel (Estado | Registro), con cabeceras de columna, columna Rol, y filtros de fecha y tipo de orden. El registro del watchdog pasa a tabla con cabeceras.
- Alias de la zona bajo «Zona X» en el Estado del motor y en las tarjetas del tablero.

### Arreglado
- El vigilante ya no puede fallar el reinicio de Z2M en silencio: un `addon_restart` rechazado por HA queda como evento «reinicio_z2m: error» y motivo de atención; un `addon_slug` sin pinta de slug (p. ej. el campo *repository* a secas) se rechaza al guardar; y el add-on pide el rol de Supervisor que necesita el desplegable de add-ons (antes 403 y desplegable vacío).
- Tablero recortado hasta tocar el zoom: las medidas ya no se aplican con la pestaña oculta y se recalculan al volver a ella.
- Guardar desde el mapeador Visual ya no borra en silencio el bloque `impulso_fancoil` del YAML: el generador lo transporta tal cual (regresión detectada en banco el mismo 08/09).
- La barra «Roles requeridos conectados» solo aparece en modo edición; fuera los chips «Modo global» y «frenos · última hora»; título «Últimos registros» sobre el mini-registro.

## 0.5.0 — 2026-09-07

### Añadido
- Módulo Watchdog (activable con `modulo_watchdog: true` en las opciones, independiente de `motor_clima`): vigila los termostatos Zigbee de la instalación y los repara solo cuando puede, con una escalera de intervención cada vez más intrusiva (sondeo silencioso → ciclo de modo → entrevista Z2M de diagnóstico) y una ronda preventiva nocturna que pasa por todas las zonas para curar tontos antes de que se noten. Porte al add-on del `watchdog_climate` de AppDaemon, con su lógica de detección/remediación validada en banco.
- Vigilante de las propias instancias de Zigbee2MQTT: detecta una antena caída y la reintenta reiniciar con una escalera exponencial (inmediato, 5, 10, 20... minutos hasta un techo de 4 h), marcándola como «rendida» si se agotan los intentos en 24 h y requiere intervención manual.
- Subpestaña **Watchdog** dentro de Clima (Estado · Registro · Ajustes), con cabecera común: switch general, botón de ronda manual, diagrama de la máquina de estados (Desactivado · Observación · Vigilando · Sondeando · Curando · Ronda, con el estado actual encendido y su progreso), y chips de atención (motivos vigentes) y de acciones de las últimas 24 h.
- Vista **Estado**: tarjetas de las antenas Zigbee detectadas (estado, escalera de reinicio, botón de reinicio manual) y tabla de zonas ordenada por gravedad, con salud, calidad de enlace Zigbee (LQI, coloreado), minutos de silencio, intervenciones de los últimos 7 días y última acción; selección múltiple con acciones en lote (sondear, ciclar modo, toggle del switch de modo del termostato, entrevistar en Z2M, pausar/reanudar vigilancia de mantenimiento, poner a cero el contador de intervenciones).
- Vista **Registro**: historial filtrable por fecha, zona o antena, tipo de evento (cura, observación, ronda, z2m, ajuste, error) y origen (reactiva, ronda, manual), con drill-down directo desde una fila o antena de la vista Estado.
- Vista **Ajustes**: umbral de silencio, timeouts de sondeo y de ciclo, guarda de antena, modo observación (detecta y anota sin ejecutar ninguna remediación — pensado para las primeras noches de una instalación nueva), configuración completa de la ronda preventiva (activación, hora, días, qué zonas cicla) y de las antenas Z2M (ping de salud, reinicio automático, qué add-on reiniciar por instancia, autodescubiertas del propio tráfico MQTT); guardado en caliente, sin reiniciar el add-on, con cada cambio anotado en el registro.
- API REST de depuración `/api/watchdog/*` (9 rutas): pensada para que Douglas y Claude diagnostiquen el watchdog por SSH con `curl` sin pasar por la UI — incluye un endpoint de auto-diagnóstico (`/salud`) con un checklist de 8 invariantes (latido, conexión MQTT viva, antenas vistas, zonas casadas, ronda reciente, registro escribible, errores internos, OFF pendientes de reponer) que delata cualquier fallo silencioso del módulo. Guía completa en [`docs/watchdog-api.md`](docs/watchdog-api.md).
- Contrato anti-fallo-silencioso: ninguna excepción del watchdog se traga en silencio — toda queda contada, trazada en memoria, anotada en el registro (badge «error») y volcada en el log del add-on.
- Alta de antenas desde la UI: el watchdog escucha el broker en modo solo lectura y ofrece en Ajustes las instancias de Zigbee2MQTT que ve pero todavía no vigila («detectada, sin configurar»); se adoptan eligiendo su add-on y pulsando «Guardar ajustes» (la vigilancia arranca en el siguiente reinicio del add-on). Antes, una instalación nueva no tenía forma de configurar su primera antena sin editar el JSON a mano.
- Editar `termostatos.yaml` (añadir o quitar zonas) se recoge en caliente, sin reiniciar el add-on: el watchdog recasa conservando las escaleras en curso.

### Arreglado (revisión final de rama)
- El switch general ya no podía dejar un termostato apagado: con el watchdog desactivado se paran la vigilancia, las rondas y toda cura nueva, pero una cura ya en marcha termina su camino de vuelta (encender de nuevo el termostato) en vez de quedarse a medias. Las acciones manuales que apagan algo (ciclar modo, ronda) se rechazan con un mensaje claro mientras el watchdog está apagado.
- Una antena Z2M mal configurada desde Ajustes ya no puede tumbar el add-on entero al reiniciarse: se valida al guardar (con mensaje claro) y el arranque tolera configuraciones antiguas o escritas a mano.
- La opción «— no reiniciar —» de una antena ya no la borraba de la vigilancia: se conserva vigilada (ping de salud, detección de caída), simplemente no se reinicia sola.
- El modo observación ya no podía confundir al arranque: sus anotaciones («esto es lo que habría hecho») ya no se emparejan como si fueran acciones reales, ni para reponer algo que nunca se apagó ni para dar por resuelto algo que sigue pendiente.
- «Toggle del modo termostato» (acción manual del W100) apaga y vuelve a encender, como promete su descripción, en vez de dar un único cambio de estado que podía dejarlo encendido; si el add-on muere entre medias, se repone al arrancar.
- «Poner a cero Interv. 7 d» sobrevive a un reinicio del add-on.
- Una antena reiniciada a mano ya no enciende el aviso de «atención» mientras revive con normalidad.
- Los mensajes de error del panel se muestran en limpio (antes salía el JSON crudo del backend), los minutos de silencio de la tabla de zonas se redondean, y un `POST /api/watchdog/activo` con un cuerpo mal escrito se rechaza en vez de apagar el watchdog en silencio.

## 0.4.3 — 2026-09-08

### Añadido
- Impulso de fancoil (`global.impulso_fancoil`, desactivado por defecto): hay fancoils que se pierden un flanco (no arrancan al subir la demanda, no paran al bajarla) o se quedan sordos a mitad de demanda sostenida, y solo despiertan con un cambio de velocidad. El motor ahora puede repetir el flanco de los relés de velocidad: un re-flanco `retardo_s` (30 s) después de cada transición de demanda y un impulso periódico cada `intervalo_min` (60 min) de demanda sostenida. La pata de ida manda el estado contrario durante `ancho_s` (3 s) y la vuelta la pone la reconciliación normal (`refresh_all`), con un segundo refresh de seguridad contra el rate limit. Solo actúa sobre los relés de velocidad (la válvula/alimentación queda fuera a propósito), respeta los forzados manuales, cancela el impulso pendiente si la demanda vuelve a cambiar y nunca lanza dos impulsos a la misma zona en menos de 2 minutos. Cada impulso queda anotado en el registro de acciones con la etiqueta IMPULSO.

  ```yaml
  global:
    impulso_fancoil:
      activado: true
      retardo_s: 30
      ancho_s: 3
      intervalo_min: 60   # 0 = sin impulso periódico
  ```

## 0.4.2 — 2026-09-02

### Añadido
- Panel de clima con mapeador en modo lectura: tarjetas termostato estilo Home Assistant con dial interactivo para ajustar consigna de forma táctil o con botones − / +, control de modo y velocidad de fancoil, y lectura de humedad.
- Nuevos endpoints: `GET /api/clima/termostatos` y `POST /api/clima/termostato` para auditabilidad de cambios enviados desde el dial.
- «Estado del motor» operativo: chips de salud (forzados activos, entidades sin conexión, frenos de la última hora), selectores globales conmutables desde el panel (calentar/enfriar/por suelo/por aire, auditados), zonas con sus relés en vivo, fila de Aerotermia y bombas, y mini-registro con salto al registro completo. Endpoints nuevos: `GET /api/clima/selectores`, `POST /api/clima/selector` y `GET /api/clima/registro?resumen=1`.
- Navegación en dos niveles: módulos (Clima primero) como pestañas primarias y las secciones del módulo activo subordinadas debajo; en pantallas estrechas la marca cede su sitio a las pestañas.
- El editor YAML abre en solo lectura: editar exige pulsar «Editar» (evita modificaciones accidentales); guardar, descartar o volver al tablero lo devuelven a solo lectura.
- Interfaz móvil mejorada: soporte para paneo y zoom con pinch (rango 40–130 %), pantalla completa con giro automático.
- Zonas plegables en lectura: presentación compacta de la información del mapeador.
- Registro de acciones en pestaña dedicada con selector de cantidad de entradas (25, 50, 100, 200).
- Termostatos y relés sin conexión visibles en el panel (con estado de bloqueo forzado cuando el relé está caído).
- Leyenda del mapeador eliminada en favor de una UI más clara.
- Nombres de rol en lectura («Suelo Z1», «Válvula Z1», «Baño Z2·Z3»…) en vez del entity_id, tanto en el mapeador como en el Estado del motor; el entity_id queda en el icono ⓘ (hover) y un click lo copia al portapapeles.
- Tarjetas de zona del Estado del motor en dos mitades: termostato (temperatura, consigna, modo, demanda) a la izquierda y actuadores en columna a la derecha, cada relé con el mismo icono y color de rol que el mapeador.

### Arreglado (validación en banco)
- Los deslizadores de forzado ya no se recortan por la derecha en móvil (las filas de canal encogen con elipsis en vez de desbordar la tarjeta).
- El scroll vertical de la página vuelve a funcionar con la rueda o el dedo sobre el tablero.
- El tablero abre ajustado al ancho de la pantalla (zoom inicial automático) en vez de recortado.
- Un arrastre de consigna cancelado por el navegador se descarta sin enviar órdenes tardías; consignas nulas o fuera de rango se pintan con seguridad.
- Los banners «Módulo aerotermia desactivado» y «Sin conexión con la máquina» ya no se colaban en el módulo Clima; el segundo solo se pinta con Aerotermia activo.
