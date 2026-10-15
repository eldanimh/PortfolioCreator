#!/usr/bin/env bash
# Despliega la última versión en el servidor: git pull + reconstruir y arrancar los contenedores.
#
# Instalación (una vez, en el Lightsail) para lanzarlo escribiendo solo update:
#   chmod +x ~/despliegue/PortfolioCreator/scripts/desplegar.sh
#   type update   # antes, comprobar que no existe ya un comando con ese nombre
#   sudo ln -sf ~/despliegue/PortfolioCreator/scripts/desplegar.sh /usr/local/bin/update
#
# Uso: update
# Si la carpeta de despliegue no es ~/despliegue: DESPLIEGUE_DIR=/otra/ruta update
set -euo pipefail

# Todo va dentro de una función: bash la lee entera antes de ejecutarla, así que el
# git pull puede actualizar este mismo fichero sin romper el despliegue en marcha.
main() {
    local despliegue="${DESPLIEGUE_DIR:-$HOME/despliegue}"

    echo "▶ Bajando la última versión..."
    cd "$despliegue/PortfolioCreator"
    git pull --ff-only  # si hay cambios locales en el servidor, para aquí en vez de mezclar
    echo "  Versión: $(git log --oneline -1)"

    echo "▶ Reconstruyendo y arrancando los contenedores..."
    cd "$despliegue"
    docker compose up -d --build

    echo "▶ Limpiando imágenes antiguas (liberar disco)..."
    docker image prune -f >/dev/null

    echo "▶ Arranque de gunicorn:"
    sleep 3
    docker compose logs --tail=40 web | grep -E "gthread|Booting|Error|Traceback" || echo "  (aún no hay líneas de arranque; mira: docker compose logs -f web)"

    echo "✔ Despliegue terminado"
}

main "$@"
exit
