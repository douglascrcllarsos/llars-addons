# Changelog

Todos los cambios notables en este proyecto están documentados en este archivo.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/),
y este proyecto se adhiere a [Versionado Semántico](https://semver.org/lang/es/).

## 0.7.2 — 2026-09-25

### Arreglado
- El relleno «sin dato» de NASA (todos los bytes a 0xFF) ya no se decodifica ni se publica. La máquina lo devuelve para un registro que conoce pero no mide (la aerotermia de Camp 64 contesta 0xFFFF a la presión de agua 0x82FE porque no monta sensor) y la unidad interior lo devuelve para cualquier registro de la exterior que se le pida (cada «Forzar lectura» del panel dejaba una ráfaga de «estado 255», «error 65535», «exterior -0.1 °C» y cerraba y reabría el error real en el historial). En HA esos sensores quedan en «desconocido» en vez de mostrar «-0.01 bar». Los ENUM que definen 255 en su tabla (0x4002 «NULL mode», 0x8247 «No defrost»…) siguen aceptándolo como valor.

## 0.7.1 — 2026-09-15

### Arreglado
- La columna «Zona» del watchdog muestra el número real de cada zona (el campo `numero_zona` del YAML, la numeración propia de la instalación) en vez de inventarse una numeración por posición en el fichero.
- El botón «Reparar emparejamiento» permite relanzar la reparación con el técnico delante del aparato: re-abre una escalera que esperaba su reintento (sin aguardar los 30 min/2 h) o que ya se había rendido, con contador fresco. Solo sigue bloqueado mientras hay órdenes en vuelo.
- La espera de la re-entrevista sube de 120 a 180 s: medida en instalaciones reales, la ficha nueva tarda ~75-90 s en llegar y el presupuesto antiguo podía declarar un fallo falso con la entrevista aún en marcha.
- El motor de clima ya no re-afirma los modos hvac al arrancar: cada reinicio o actualización del add-on volvía a encender (en el modo de temporada) las zonas que un usuario había apagado. El cambio real de los selectores de temporada sigue propagándose a todas las zonas, como siempre.
- Un ciclo manual lanzado justo después de apagar una zona ya no puede re-encenderla: la acción refresca el modo real desde Home Assistant antes de decidir (y su restauración y cura se registran con origen manual, no como automáticas).

## 0.7.0 — 2026-09-15

### Añadido
- Límites de setpoint para **todos** los termostatos vigilados (no solo W100): el watchdog detecta cualquier consigna fuera de los límites configurados — venga de Home Assistant, de MQTT o de la rueda física del aparato — y la recorta al momento, respetando el paso real del dispositivo. La orden de corrección toca **solo** la temperatura, nunca el modo ni el encendido.
- Los límites se configuran por modo (calor y frío, cada uno con su mínimo y máximo) para toda la instalación. El límite efectivo es siempre el más estricto entre el global y el de fábrica del propio aparato.
- Autodetección del setpoint de cada modelo desde los `exposes` de Zigbee2MQTT (nombre de la propiedad, límites de fábrica y paso): sin listas de modelos cableadas a mano. Una zona cuyo termostato no expone setpoint simplemente no se vigila.
- Cupo silencioso de 3 correcciones por zona y hora (ventana deslizante): si alguien se pelea con el límite o el aparato no obedece, el watchdog deja de insistir hasta la hora siguiente, sin generar avisos de atención — la detección sí queda en el registro para diagnóstico.
- Columna «Setpoint» en la tabla de zonas (valor en gris con su motivo cuando la zona no se vigila: apagada, sin respuesta, sin expose…) con marca ✂ y detalle de los recortes recientes; grupo de Ajustes «Límites de setpoint» (interruptor y pares calor/frío); filtro y badge «setpoint» en el Registro.
- Campos nuevos en `/api/watchdog/estado` por zona (`setpoint`, `setpoint_ts`, `setpoint_limites`, `modo_actual`, `ultimo_recorte`), filtro `?tipo=setpoint` en `/registro` y bloque `setpoints` con sus rangos en `/ajustes`. Los recortes aplicados cuentan como intervención de zona; las detecciones sin orden física, no.
- Guardas de seguridad: nada se evalúa en zonas apagadas, pausadas o sin modo conocido; gracia de 60 s tras cualquier cambio de modo (evita recortar la consigna nueva contra los límites del modo viejo); anti-eco de 30 s tras cada recorte; en modo observación solo se anota, sin órdenes físicas.

### Arreglado
- Actualizar el add-on ya no puede descartar la configuración afinada de la instalación: un `watchdog.json` escrito por una versión anterior (sin los bloques nuevos) se migra rellenando solo lo que falta, en vez de darse por corrupto entero y caer a los valores por defecto.
- Los eventos de la sonda de modo W100 salen ahora con su badge «modo» propio en el Registro y el filtro «Modo» aparece en el selector de tipos (la API ya lo soportaba, pero el panel no lo ofrecía).

## 0.6.0 — 2026-09-14

### Añadido
- Sonda real del modo termostato W100: en vez de fiarse de un toggle a ciegas, el watchdog lee el atributo propietario del W100 (`0xFFF2`) y decide ON/OFF con el contenido real de la respuesta del dispositivo. La sonda **sustituye** al toggle nocturno: la ronda pasa a sondeo + ciclo simétrico (una zona en calor/frío cicla off→modo como hasta ahora; una zona que ya está en OFF recibe un re-envío de «OFF», nunca cambia su estado final) + corrección dirigida, que solo actúa sobre las zonas que la sonda confirma apagadas.
- Detección de «emparejamiento incompleto» en zonas W100 (dispositivo casado sin el binding que necesita para responder bien) y reparación automática: re-entrevista Z2M + reconfiguración + corrección, con una escalera de reintentos de 3 intentos en 24 h (inmediato, +30 min, +2 h); si los tres fallan, sube un aviso de atención y queda un reintento diario dentro de la ronda nocturna hasta que una reparación entre.
- Acciones manuales nuevas en Opciones de la tabla de zonas: «Sondear modo real» y «Reparar emparejamiento», por selección múltiple.
- Columna «Modo» en la tabla de zonas (ON, OFF, desconocido, o «— No es Aqara W100» en zonas sin ese termostato) e insignia «emparejamiento incompleto» junto al alias de las zonas afectadas.
- Grupo de Ajustes «W100»: gracia tras el arranque/reconexión de una antena antes de sondear, sonda automática al ver «Failed to configure» en el log de Zigbee2MQTT, reparación automática activable/desactivable y timeout de la sonda.
- Comprobación `sondas_modo` en `/api/watchdog/salud` (9ª del checklist de auto-diagnóstico): degrada si alguna zona W100 lleva más de una hora con `modo_real: off` sin una corrección o reparación en curso — el equivalente anti-fallo-silencioso de un OFF crónico que nadie está corrigiendo.
- Eventos nuevos en el registro del watchdog (`sonda_modo`, `modo_on`, `reparacion`, con los bytes crudos de cada sonda para diagnóstico) y filtro de tipo «modo» en la vista Registro del panel.

### Arreglado
- El tooltip ⓘ (ayuda de columna) ya no se recorta al quedar dentro de un contenedor con scroll horizontal de la tabla de zonas: pasa a un globo flotante posicionado fuera del recorte, igual para el de LQI, el de la nueva columna Modo y el de la insignia «emparejamiento incompleto».
- La ronda nocturna ya no puede quedarse colgada para siempre en una zona cuya corrección de modo no llega a salir (por ejemplo si se apaga el interruptor general del watchdog justo en ese momento): esa espera pasa a tener su propio tope, como el resto de pasos de la ronda. Antes, esa situación dejaba la ronda muerta noche tras noche hasta reiniciar el add-on.
- La reparación del emparejamiento espera ahora a que Zigbee2MQTT termine de configurar el aparato antes de mandarle el encendido. Antes, la configuración podía pisar ese encendido y la reparación se daba por fallida sobre un aparato que en realidad había quedado bien.
- La reparación tampoco se rinde ya porque Zigbee2MQTT publique su lista de dispositivos por un motivo ajeno (un aparato distinto que se da de alta, un renombrado…): sigue esperando su turno mientras le quede plazo.
- La reparación solo se da por buena si la sonda de verificación confirma el encendido **y** el emparejamiento deja de estar incompleto, y esa sonda ya actualiza la columna Modo y el registro (con sus bytes crudos). Antes, tras una reparación correcta la columna Modo seguía marcando «OFF» en rojo y el auto-diagnóstico degradaba en falso una hora después.
- El latido del watchdog ya no se para mientras el propio watchdog trabaja: una sonda o una reparación largas hacían que el auto-diagnóstico declarase el proceso muerto justo cuando estaba en plena remediación.
- El botón «Re-entrevistar y configurar» responde de inmediato en vez de dejar la petición abierta durante todo el proceso (que con varios aparatos seleccionados podía superar el tiempo máximo del proxy y acabar en un error engañoso).
- Las sondas lanzadas a mano quedan registradas como manuales (antes se anotaban como automáticas, así que el filtro por origen del Registro no las encontraba y contaban en el resumen de acciones automáticas de 24 h).
- Un dispositivo con estructura inesperada en la lista de Zigbee2MQTT ya no puede pasar por «sano» en silencio: el fallo queda contado y trazado en el registro.

## 0.5.3 — 2026-09-08

### Arreglado
- El watchdog ya casa las zonas cuando el nombre del dispositivo en Zigbee2MQTT lleva mayúsculas o espacios («Z1» → `climate.z1`): el casado usa la misma normalización de nombres que Home Assistant y conserva el nombre real del dispositivo para hablarle por MQTT. Antes, una instalación con nombres en mayúscula quedaba con 0 zonas vigiladas.

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
