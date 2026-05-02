# PROPUESTA DE PROYECTO: Portfolio Creator

## 1. Descripción general de la aplicación y su utilidad
**Portfolio Creator** es una aplicación web diseñada para resolver el problema de la dispersión de información profesional en el ámbito del desarrollo de software y la investigación académica. Muchos estudiantes, ingenieros e investigadores tienen sus proyectos repartidos en plataformas como GitHub, repositorios institucionales (GitLab URJC) y publicaciones científicas (OpenAlex). 

La aplicación permite a los usuarios conectar sus cuentas y extraer automáticamente todos estos repositorios y publicaciones en un único panel de control. Su principal innovación radica en la **integración de Inteligencia Artificial (IA)** para analizar el código y los metadatos de dichos proyectos y generar resúmenes profesionales, descriptivos y formateados. Finalmente, el usuario puede seleccionar qué proyectos desea destacar y exportar un Currículum/Portfolio unificado, bien en formato PDF estructurado o como una plantilla HTML responsiva y moderna lista para ser alojada en la web (ej. GitHub Pages).

## 2. Tecnologías y APIs externas que se van a utilizar
El desarrollo se sustenta en una arquitectura clásica de servidor utilizando las siguientes tecnologías:

**Backend & Framework:**
* **Django (Python):** Framework principal para el enrutamiento, la lógica de negocio, la seguridad (autenticación) y el renderizado de plantillas.
* **SQLite:** Base de datos relacional ligera integrada por defecto para la persistencia de usuarios y datos de los portfolios.
* **Playwright & xhtml2pdf:** Librerías empleadas para la renderización de HTML y conversión fidedigna a documentos PDF.

**Frontend:**
* **HTML5, CSS3 y JavaScript (Vanilla):** Diseño responsivo, manejo de ventanas modales y diseño de plantillas minimalistas.
* **Markdown:** Para el renderizado seguro de los textos estructurados generados por la Inteligencia Artificial.

**APIs Externas y de Inteligencia Artificial:**
* **API REST de GitHub:** Para recuperar repositorios públicos y privados del usuario, así como su estructura de directorios.
* **API REST de GitLab (URJC):** Para extraer proyectos académicos alojados en los servidores de la universidad.
* **API de OpenAlex:** Para buscar y extraer metadatos de publicaciones científicas y *papers*.
* **API de NVIDIA (Gemma-2-2b-it):** Utilizando la librería `openai` para procesar en la nube peticiones complejas a la IA y generar resúmenes en *streaming*.
* **Local LM Studio API:** Soporte nativo para que el usuario pueda usar modelos locales (ej. `qwen2.5-7b-instruct`) y ejecutarlos en su propio hardware por privacidad.

## 3. Esquema preliminar del modelo de datos (tablas principales)
La base de datos relacional (SQLite) contará con las tablas nativas de Django para el manejo de sesiones y usuarios (`User`), que estarán directamente vinculadas a las tablas desarrolladas específicamente para la aplicación:

**Tabla 1: `UserProfile` (Extensión del Usuario)**
Gestiona la configuración privada de cada usuario y la vinculación con las APIs externas mediante una relación *One-to-One* con el modelo `User` de Django.
* `user`: FK (Clave foránea a la tabla User de autenticación de Django).
* `github_username` / `gitlab_username`: (String) Identificadores de usuario en las plataformas.
* `github_token` / `gitlab_token` / `openalex_token`: (String) Tokens personales de acceso seguro para APIs.
* `nvidia_api_key`: (String) Clave de acceso a la nube generativa de NVIDIA.
* `lm_studio_url`: (URL) Ruta del servidor de inferencia local.

**Tabla 2: `ContenidoData` (Almacén de Proyectos y CV)**
Responsable de almacenar de forma persistente los portfolios generados y los recursos externos extraídos para su rápido acceso.
* `recurso`: (String, Único) Identificador del recurso o nombre del CV.
* `contenido`: (JSON/Text) Almacén flexible estructurado en JSON que guarda los datos personales del usuario (nombre, email, foto, etc.) y la lista de proyectos seleccionados para el CV, junto con los resúmenes inyectados por la IA.
* `usuario`: (String) Propietario del recurso.
* `plataforma`: (String) Origen del dato (GitHub, GitLab, OpenAlex).
* `url_repo`: (URL) Enlace original de referencia.
* `fecha_creacion`: (DateTime) Sello de tiempo de la creación del documento.
