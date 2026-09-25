# Add-ons de Llars Sostenible

Tienda de add-ons de Home Assistant de Llars Sostenible. Contiene dos
add-ons con distinta forma de distribución:

- **Llars Control**: solo metadatos en este repo; el código viaja dentro de
  una imagen privada en GHCR, así que instalarlo requiere acceso de lectura
  a esa imagen.
- **Llars Contadores**: código fuente incluido en este repo; el Supervisor
  lo construye localmente en la propia máquina al instalarlo, sin necesitar
  autenticación contra GHCR.

## Instalación

1. Si vas a instalar **Llars Control**, autentica antes la máquina contra
   GHCR (una vez):
   `ha docker registries add ghcr.io --username <usuario> --password <token read:packages>`
2. Ajustes → Complementos → Tienda → ⋮ → Repositorios → añadir
   `https://github.com/douglascrcllarsos/llars-addons`
3. Instalar el add-on deseado (**Llars Control** o **Llars Contadores**)
   desde la tienda.

Las actualizaciones llegan por la tienda (`ha addons update`); la de
Llars Contadores reconstruye la imagen local con el código actualizado.
