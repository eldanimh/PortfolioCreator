#!/usr/bin/env bash
# Crea 2 GB de swap en el servidor (Ubuntu) como red de seguridad ante picos de memoria.
# Uso (en el Lightsail, no dentro del contenedor):  sudo bash scripts/crear_swap.sh
set -euo pipefail

if swapon --show | grep -q '/swapfile'; then
    echo "Ya hay swap en /swapfile:"; swapon --show; exit 0
fi

fallocate -l 2G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
grep -q '^/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab  # que siga tras reiniciar

# Usar el swap solo cuando haga falta de verdad (por defecto Ubuntu lo usa antes)
sysctl -w vm.swappiness=10
grep -q '^vm.swappiness' /etc/sysctl.conf || echo 'vm.swappiness=10' >> /etc/sysctl.conf

swapon --show
free -h
