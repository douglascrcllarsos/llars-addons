# Add-ons de Llars Sostenible

Tienda de add-ons de Home Assistant de Llars Sostenible. Solo contiene los
metadatos: el código viaja dentro de imágenes privadas en GHCR, así que para
instalar hace falta acceso de lectura a esas imágenes.

## Instalación

1. Autenticar la máquina contra GHCR (una vez):
   `ha registries add ghcr.io --username <usuario> --password <token read:packages>`
2. Ajustes → Complementos → Tienda → ⋮ → Repositorios → añadir
   `https://github.com/douglascrcllarsos/llars-addons`
3. Instalar **Gestor Llars** desde la tienda.

Las actualizaciones llegan por la tienda (`ha addons update`).
