# Llars Contadores

## Qué hace

Este add-on lee los contadores de pulsos de módulos de agua Wayjun
WJ69-485 a través de un conversor USR-DR134 (puente Modbus RTU sobre TCP).
Cada `intervalo_s` segundos consulta, por dirección Modbus, el registro de
contadores de cada módulo configurado y publica los litros acumulados, los
pulsos brutos y el caudal instantáneo de cada canal como entidades MQTT con
autodescubrimiento de Home Assistant, además de un sensor de conexión por
módulo.

No es un simple puente Modbus → MQTT: lleva su propia contabilidad de
litros en `/data/estado.json`, independiente de lo que el módulo WJ69
recuerde en cada instante, para que el histórico de consumo no dependa de
que el módulo mantenga sus contadores internos entre reinicios.

## El problema: el firmware V1.50 pierde los contadores en cada corte

El firmware V1.50 del WJ69-485 reinicia sus contadores de pulsos (DI) a
cero cada vez que el módulo pierde alimentación, aunque sea un instante.
Un simple traductor Modbus → MQTT heredaría ese defecto: cada corte de luz
haría "desaparecer" litros ya consumidos y las gráficas de Home Assistant
mostrarían bajadas imposibles.

Para evitarlo, el add-on guarda en cada ciclo la última lectura cruda de
cada canal junto con el acumulado real. Si la lectura nueva es mayor o
igual que la anterior, suma la diferencia; si es **menor**, entiende que el
módulo se ha reiniciado y suma la lectura entera como pulsos nuevos desde
el arranque (nunca se resta ni se "adivina" el hueco). El acumulado vive en
`/data`, que persiste aunque se reinicie el add-on o el propio Home
Assistant.

## Configuración

Las opciones se editan en la pestaña **Configuración** del add-on (o en su
vista YAML). Ejemplo genérico con un módulo y un canal:

```yaml
modulos:
  - id: cocina                    # identidad ESTABLE del módulo. No renombrar.
    nombre: "Contador cocina"     # etiqueta libre, solo para mostrar.
    host: 192.168.1.50            # IP del conversor USR-DR134.
    puerto: 502                   # puerto TCP del conversor (Modbus sobre TCP).
    direccion: 1                  # dirección Modbus (esclavo) del módulo, 1-247.
    canales:
      - id: A0                    # canal físico del WJ69: A0-A7 o B0-B7. No renombrar.
        nombre: "Agua fría cocina"    # etiqueta libre, va al nombre de la entidad.
        litros_por_pulso: 1.0     # litros que representa cada pulso del contador.
        offset_litros: 0          # ver "Apuntar offset_litros" más abajo.
intervalo_s: 30                    # cada cuántos segundos se sondea cada módulo (5-3600).
```

Puede haber varios módulos, cada uno con sus propios canales.

### `id` frente a `nombre`

Cada módulo y cada canal tienen un `id` y un `nombre`:

- **`id`** es la identidad **estable**: de él sale el `unique_id` de la
  entidad en Home Assistant y la clave con la que se guarda su acumulado en
  `/data/estado.json`. **No renombrar un `id` una vez puesto en marcha**:
  Home Assistant lo vería como una entidad nueva y el add-on empezaría el
  acumulado de ese canal desde cero. El `id` del módulo es libre (letras
  minúsculas, dígitos y `_`, hasta 16 caracteres); el del canal viene fijado
  por el cableado físico del WJ69: `A0`-`A7` o `B0`-`B7`.
- **`nombre`** es solo la etiqueta visible en la interfaz: se puede cambiar
  en cualquier momento sin ningún efecto sobre el histórico.

### Apuntar `offset_litros`

`litros_por_pulso` convierte pulsos en litros, pero el add-on no conoce el
punto de partida real del contador físico (la esfera del WJ69) el día que
se instala o se pone en marcha el add-on. `offset_litros` corrige ese
desfase:

```
offset_litros = lectura de la esfera del contador − litros que el add-on
                ya ha contado ese mismo día (antes de aplicar el offset)
```

Hay que anotar la lectura de la esfera y el valor del sensor de litros del
add-on **el mismo día**, y restar. Cambiar el offset después solo afecta a
partir de ese momento: el acumulado de pulsos interno no se toca, solo se
desplaza la lectura en litros que se publica.

## Entidades creadas

Por cada **módulo** configurado:

| Entidad | Dominio | `device_class` | Notas |
|---|---|---|---|
| `<nombre> conexión` | `binary_sensor` | `connectivity` | Diagnóstico. `ON`/`OFF` según si el módulo responde. |
| `<nombre> último corte` | `sensor` | `timestamp` | Diagnóstico. Ver sección siguiente. |

Por cada **canal** del módulo:

| Entidad | Dominio | `device_class` / unidad | Notas |
|---|---|---|---|
| `<nombre del canal>` | `sensor` | `water`, litros (`L`) | Litros acumulados, `state_class: total_increasing`. |
| `<nombre del canal> pulsos` | `sensor` | sin unidad | Diagnóstico. Pulsos brutos acumulados. |
| `<nombre del canal> caudal` | `sensor` | `L/min` | Caudal instantáneo entre las dos últimas lecturas buenas. |

Todas las entidades de un módulo comparten un mismo dispositivo en Home
Assistant («WJ69-485 via USR-DR134», fabricante «Llars Sostenible»).

## El sensor «último corte»

Marca la fecha/hora (UTC) del último reinicio detectado del WJ69: la
última vez que una lectura de pulsos llegó por debajo de la anterior. **No
significa que se haya perdido consumo acumulado** (el add-on suma la
lectura íntegra tras el reinicio), sino que hubo un **hueco de consumo sin
contar**: los pulsos producidos durante el propio corte de alimentación,
mientras el módulo estaba apagado, no se pueden conocer y no se estiman ni
se reparten. Es diagnóstico para saber cuándo revisar la instalación
eléctrica del módulo, no una alarma sobre el dato publicado.

## Los cortes de conexión no tocan el acumulado

Si el add-on no consigue leer un módulo (conversor apagado, cable de red
desconectado...), no inventa ni descuenta nada: reintenta en el siguiente
ciclo. Tras tres intentos fallidos marca la conexión del módulo como
`OFF`, pero el acumulado se mantiene intacto en `/data/estado.json` con el
último valor bueno; al recuperar la lectura sigue sumando desde ahí. Solo
un reinicio real del propio WJ69 (contador que baja) cuenta como corte de
alimentación.
