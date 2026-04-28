# Portfolio Generator

## Descripción del Proyecto

Aplicación web desarrollada en **Django** que permite generar un Currículum Vitae (CV) profesional en formato PDF a partir de los perfiles y repositorios de un usuario en **GitHub** y **GitLab (URJC)**. 

La aplicación se autentica a través de GitHub, permitiendo visualizar los repositorios que el usuario tiene en ambas plataformas. Al seleccionar uno de los proyectos, la aplicación genera y descarga de forma automática un CV en PDF. Este documento PDF tiene un formato elegante e incluye el contenido del archivo `README.md` proporcionado por el repositorio renderizado correctamente (con estilos como los propios de GitHub/GitLab), además de mostrar la estructura de archivos ordenada por carpetas del proyecto. 

El proyecto hace uso de:
- **Django** para la arquitectura base de la web, el ruteo de urls y renderizado de plantillas.
- **Bases de datos SQLite3** (`db.sqlite3`) para almacenar configuraciones, autenticaciones y cachés de forma persistente.
- **REST APIs de GitHub y GitLab URJC** para el listado e inspección de directorios en repositorios.
- **Diseño limpio sin JavaScript**, confiando únicamente en CSS y el backend de Django, brindando una experiencia profesional.

---

## Generación de PDFs y Renderizado Markdown

Uno de los principales retos del proyecto es convertir el código fuente `README.md` de un repositorio de GitHub o GitLab en un documento en PDF bien formateado que parezca profesional e idéntico a una previsualización web.

Para lograrlo, se implementaron las siguientes soluciones:
- **Librería `markdown` (Python)**: Transforma todo el texto escrito en Markdown (encontrado en los READMEs) a etiquetas HTML estándar y correctas.
- **Librería `xhtml2pdf`**: Toma el HTML renderizado (junto con CSS) y lo compila creando un documento PDF.
- **Inyección de CSS Específico en el Template HTML (`cv_template.html`)**: Para asegurar que elementos como tablas, bloques de código, citas blockquote, listas, y tipografías se vean de manera elegante en el PDF:
  - Se configuró la directiva `@page` de CSS3 (para ajustar automáticamente márgenes en hojas A4 y agregar pie de página/encabezado).
  - Se incluyeron selectores CSS concretos simulando la hoja de estilos de GitHub (`github-markdown-css` adaptada a compatibilidad con xhtml2pdf).
  - Se añadieron saltos de línea forzados y márgenes interiores en las celdas de las tablas y etiquetas `pre` y `code` para que el código dentro del README.md sea 100% legible.

---

## Requisitos Previos e Instalación

Para ejecutar este proyecto de forma local, necesitarás tener instalado `python3` y acceder mediante la línea de comandos/terminal.

A continuación, los pasos para que pongas en marcha el proyecto (desde cero, incluyendo el entorno virtual y el arranque):

### 1. Activar / Crear Entorno Virtual
Según los requerimientos en la especificación, el proyecto necesita el entorno virtual alojado en el directorio padre y llamado `venv-django`.

En la terminal (ubicado siempre a la altura del directorio del trabajo que incluye `manage.py`):
```bash
# Crear entorno virtual (ubicado un nivel arriba en el sistema de archivos)
python3 -m venv ../venv-django

# Activar el entorno virtual 
# -> En macOS o Linux:
source ../venv-django/bin/activate
# -> En Windows:
# ..\venv-django\Scripts\activate
```

### 2. Instalar Dependencias
Dentro del entorno virtual activado, debes instalar todas las librerías imprescindibles:
```bash
pip install -r requirements.txt
```

### 3. Migración de la Base de datos
Es necesario inicializar las tablas de la base de datos (se usa SQLite).
```bash
python manage.py makemigrations
python manage.py migrate
```

### 4. Arrancar el Servidor
Iniciaremos la puesta en marcha de la aplicación en el entorno de desarrollo local con:
```bash
python manage.py runserver
```

La consola te confirmará que el servidor se está ejecutando (por general, en el puerto `8000`).

### 5. Utilizar la Aplicación
Abre un navegador (Chrome, Firefox, Safari) y dirígete a:

👉 **[http://localhost:8000/](http://localhost:8000/)**

¡Ya puedes utilizar y probar la app de generación de CVs! 
(Al terminar tu sesión, con un `CTRL + C` en tu terminal, apagas el servidor web y para salir del entorno virtual podrás ejecutar el comando `deactivate`).
