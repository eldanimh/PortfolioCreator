"""
Configuración de gunicorn para el servidor (AWS Lightsail: 2 GB de RAM, 2 vCPU).

gunicorn la lee sola si se arranca desde esta carpeta (o con `-c gunicorn.conf.py`).
Ojo: lo que se pase en la línea de comandos (`--workers`, `-b`...) tiene prioridad.

Casi todo el tiempo de una petición es esperar a APIs externas (GitHub, GitLab, la IA...),
no CPU: con hilos, cada proceso atiende varias peticiones a la vez sin duplicar la memoria
de Django. 3 procesos × 8 hilos = 24 peticiones simultáneas con ~300 MB de RAM.
"""
import os

bind = os.environ.get('GUNICORN_BIND', '0.0.0.0:8000')
workers = int(os.environ.get('GUNICORN_WORKERS', 3))
worker_class = 'gthread'
threads = int(os.environ.get('GUNICORN_THREADS', 8))

timeout = 60            # un proceso que no responde en 60 s se reinicia
graceful_timeout = 30
keepalive = 5

# Reiniciar cada proceso tras ~1000 peticiones: si algo acumula memoria, se libera
max_requests = 1000
max_requests_jitter = 100

if os.path.isdir('/dev/shm'):
    worker_tmp_dir = '/dev/shm'  # el latido de los workers en RAM, no en el disco

accesslog = '-'
errorlog = '-'
