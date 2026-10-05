# SEGUIMIENTO DE FASES DEL PROYECTO

Este documento registra el avance del desarrollo de **Portfolio Creator**, detallando el estado de cada hito requerido en la evaluación.

---

## Fase 1: Prototipo Funcional

**Estado: Completado y Revisado**

### 1. Lo completado
Se ha establecido la estructura básica de la aplicación:
* **Modelo de datos implementado:** Se han creado y migrado a SQLite las tablas principales `UserProfile` (gestión de tokens y claves API) y `ContenidoData` (almacenamiento en caché de repositorios y datos en formato JSON).
* **Recursos web funcionando:** Se han programado las vistas y plantillas base para el sistema de Registro/Login de usuarios, la página principal (`index`) y la vista de configuración de tokens.
* **Integración inicial con API externa:** Se ha integrado exitosamente la **API REST de GitHub**, permitiendo que un usuario autenticado pueda listar sus repositorios públicos y privados de forma dinámica en la web.

### 2. Lo pendiente
En esta etapa del prototipo quedaba pendiente:
* Integrar la API de GitLab y el buscador científico de OpenAlex.
* Diseñar la interfaz del "Constructor de CV".
* Implementar la librería `xhtml2pdf` y Playwright para la exportación de documentos.
* Conectar la inteligencia artificial para el procesado de textos.

### 3. Cambios respecto a la propuesta inicial
Durante la fase de diseño inicial se propuso usar el motor de IA "Google Gemini". Sin embargo, durante el desarrollo del prototipo funcional se decidió pivotar hacia **soluciones de IA de código abierto (Open Weights)** por motivos de privacidad y control tecnológico. El modelo de datos y la librería de conexión se reestructuraron para usar el cliente `openai` apuntando a la **API en la nube de NVIDIA (modelo Gemma-2-2b-it)** y ofreciendo soporte para servidores de inferencia locales (LM Studio).

---

## Fase 2: Versión Avanzada

**Estado: Completado y Entregado**

### 1. Funcionalidad obligatoria completa
Se ha concluido el desarrollo de todo el sistema básico y avanzado propuesto:
* **Integración total de APIs:** La aplicación ya es capaz de extraer repositorios de GitHub, repositorios institucionales cerrados de GitLab y publicaciones de *papers* científicos mediante OpenAlex.
* **Generador de Portfolio/CV:** Se ha desarrollado un panel ("Constructor de CV") donde el usuario puede agrupar todos sus recursos, añadir información personal de contacto y previsualizar los resultados.
* **Exportación Profesional:** El proyecto se puede exportar tanto en una plantilla HTML moderna, estética y responsiva (lista para subir a GitHub Pages), como en formato documento PDF maquetado.

### 2. Parte optativa implementada
Para ir más allá de los requisitos básicos, se han implementado las siguientes funciones avanzadas:
* **Motor Generativo de IA en Streaming:** Integración profunda con el modelo **NVIDIA Gemma 2** (y soporte para LLMs locales). La web es capaz de leer el README de un repositorio o los metadatos de un paper, y generar en vivo (con efecto máquina de escribir / streaming) un resumen técnico, profesional y de impacto para incrustarlo automáticamente en el currículum.
* **Testing Automatizado Completo:** Se ha programado una suite de 15 tests unitarios en el entorno de Django (`tests.py`) utilizando simuladores o *Mocks* (`unittest.mock.patch`) para verificar la robustez de los modelos, formularios, integraciones de red externas y seguridad de las vistas. Todos los tests pasan correctamente (100% de éxito), garantizando la calidad y estabilidad de la versión final.
* **Login Social con OAuth 2.0 (django-allauth):** Integración de `django-allauth` para permitir inicio de sesión con un clic mediante cuentas de **GitHub** y **Google**. Incluye creación automática de `UserProfile` mediante signals de Django (`post_save`), configuración de OAuth Apps en ambas plataformas y gestión de credenciales desde el Admin Site.
* **Diseño Responsive y UX Mejorada:** Refactorización completa del CSS con media queries para dispositivos móviles (`max-width: 768px`), adaptando la navegación, el constructor de CV, las tarjetas de proyecto y los botones de descarga. Saludo personalizado al usuario en la barra de navegación (`¡Hola, <username>!`).
* **Seguridad de Datos:** Filtrado estricto de recursos por usuario autenticado para evitar fugas de información entre cuentas. Mensajes de error de autenticación diferenciados en español (usuario no existe, contraseña incorrecta, contraseña débil).
* **Despliegue en la Nube:** Desplegada en AWS Lightsail con Docker, Caddy como proxy inverso con HTTPS automático, gunicorn como servidor de la app y WhiteNoise para los ficheros estáticos, accesible en `https://creator.danimh.dev`.
