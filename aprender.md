# Aprender: Integración de Gemini AI en Django

Guía paso a paso de cómo se integró la API de Google Gemini en la aplicación **Portfolio Creator** (Django).

---

## 1. Instalación de la librería

Lo primero es instalar el paquete oficial de Google para Gemini:

```bash
pip install google-genai
```

También se añadió a `requirements.txt` para que cualquiera pueda reproducir el entorno:

```
Django
requests
xhtml2pdf
social-auth-app-django
markdown
google-genai          ← NUEVO
```

---

## 2. Guardar la API Key del usuario — `models.py`

Cada usuario necesita su propia API Key de Gemini. Para guardarla, se añadió un campo al modelo `UserProfile`:

```python
# portfolioCV/models.py

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    github_token = models.CharField(max_length=255, blank=True, default='')
    gitlab_token = models.CharField(max_length=255, blank=True, default='')
    github_username = models.CharField(max_length=150, blank=True, default='')
    gitlab_username = models.CharField(max_length=150, blank=True, default='')
    openalex_token = models.CharField(max_length=255, blank=True, default='')
    gemini_api_key = models.CharField(max_length=255, blank=True, default='')  # ← NUEVO
```

### ¿Qué es esto?
- `CharField(max_length=255)` → un campo de texto con máximo 255 caracteres
- `blank=True, default=''` → es opcional, si no lo rellenas queda vacío
- Después de añadir el campo, hay que crear y aplicar la migración:

```bash
python3 manage.py makemigrations portfolioCV
python3 manage.py migrate
```

Esto genera un archivo en `portfolioCV/migrations/` que modifica la tabla en SQLite3 para añadir la nueva columna.

---

## 3. Formulario para introducir la clave — `forms.py`

Para que el usuario pueda escribir su API Key desde la web, se añadió al formulario `TokensForm`:

```python
# portfolioCV/forms.py

class TokensForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = [
            'github_token', 'gitlab_token', 'openalex_token',
            'gemini_api_key',        # ← NUEVO
            'github_username', 'gitlab_username'
        ]
        widgets = {
            # ... los demás widgets ...
            'gemini_api_key': forms.PasswordInput(attrs={
                'placeholder': 'API Key de Gemini'
            }),
        }
        labels = {
            # ... los demás labels ...
            'gemini_api_key': 'Gemini API Key',
        }
```

### ¿Por qué `PasswordInput`?
- Para que el campo se muestre como `****` en el navegador (tipo contraseña)
- La API Key es un secreto, no debe verse en pantalla

---

## 4. Tarjeta de ayuda en la página de Tokens — `tokens.html`

Se añadió una tarjeta informativa para que el usuario sepa cómo obtener su clave:

```html
<!-- portfolioCV/templates/portfolioCV/tokens.html -->
<div class="help-card">
    <h3>🤖 Gemini AI</h3>
    <p>Ve a <strong>aistudio.google.com/apikey</strong> → Create API Key</p>
    <p>Modelo: <code>gemini-2.5-pro</code></p>
</div>
```

El formulario ya existente (que recorre los campos con `{% for field in form %}`) muestra automáticamente el nuevo campo `gemini_api_key`.

---

## 5. La URL — `urls.py`

Se registró una nueva ruta para la vista de Gemini:

```python
# portfolioCV/urls.py

urlpatterns = [
    # ... todas las URLs anteriores ...

    # Gemini AI
    path('gemini/resumen/', views.generar_resumen_gemini, name='generar_resumen_gemini'),

    # ... recursos genéricos al final ...
]
```

### ¿Cómo funciona?
- Cuando el usuario envía un formulario POST a `/gemini/resumen/`, Django ejecuta la función `generar_resumen_gemini`
- El `name='generar_resumen_gemini'` permite referenciarla en templates con `{% url 'generar_resumen_gemini' %}`

---

## 6. La vista principal — `views.py`

Esta es la parte más importante. La función `generar_resumen_gemini` hace todo el trabajo:

### 6.1. Verificaciones iniciales

```python
@login_required
def generar_resumen_gemini(request):
    if request.method != 'POST':
        return redirect('index')

    profile = get_object_or_404(UserProfile, user=request.user)
    if not profile.gemini_api_key:
        messages.warning(request, 'Configura tu API Key de Gemini primero.')
        return redirect('configurar_tokens')
```

- `@login_required` → solo usuarios autenticados
- Solo acepta `POST` (no se puede acceder por URL directamente)
- Comprueba que el usuario tenga configurada su API Key

### 6.2. Recoger los datos del formulario

```python
    platform = request.POST.get('platform', '')      # GitHub, GitLab URJC, OpenAlex
    item_id = request.POST.get('id', '')              # ID del repo/obra
    cv_type = request.POST.get('cv_type', 'extenso')  # extenso, una_pagina, tecnologia, tfg
    item_name = request.POST.get('name', 'Proyecto')   # Nombre del proyecto
```

Estos datos vienen del formulario HTML que está en `repo_detalle.html`.

### 6.3. Recopilar contenido del repositorio/obra

Según la plataforma, se llama a la API correspondiente para obtener el contenido:

**Para GitHub:**
```python
if platform == 'GitHub':
    # 1. Obtener info del repo (descripción, lenguaje, URL)
    headers = {"Authorization": f"Bearer {profile.github_token}", ...}
    resp = requests.get(f"{GITHUB_API_URL}/repos/{item_id}", headers=headers)
    
    # 2. Obtener el README en texto plano
    resp_r = requests.get(f"{GITHUB_API_URL}/repos/{item_id}/readme", headers=headers_raw)
    contenido_texto += f"\nREADME:\n{resp_r.text[:4000]}\n"
```

**Para GitLab URJC:**
```python
elif platform == 'GitLab URJC':
    headers = {"PRIVATE-TOKEN": profile.gitlab_token}
    resp = requests.get(f"{GITLAB_URJC_URL}/projects/{item_id}", headers=headers)
    # Obtener README
    resp_r = requests.get(
        f"{GITLAB_URJC_URL}/projects/{item_id}/repository/files/README.md/raw",
        headers=headers, params={"ref": default_branch}
    )
```

**Para OpenAlex:**
```python
elif platform == 'OpenAlex':
    resp = requests.get(f"https://api.openalex.org/works/{item_id}", params=params)
    # Reconstruir el abstract desde el "inverted index"
    abs_idx = wdata.get('abstract_inverted_index')
    if abs_idx:
        words = {}
        for word, pos_list in abs_idx.items():
            for pos in pos_list:
                words[pos] = word
        abstract = " ".join([words[p] for p in sorted(words.keys())])
```

> **Nota sobre OpenAlex:** El abstract viene como un "inverted index" (diccionario donde cada palabra mapea a sus posiciones). Hay que reconstruir el texto ordenando por posición.

### 6.4. Construir el prompt según el tipo de CV

Cada tipo de CV tiene un prompt diferente que le dice a Gemini cómo generar el resumen:

```python
prompts_map = {
    'extenso': "Genera un CV/portfolio EXTENSO y detallado en español...",
    'una_pagina': "Genera un CV/portfolio CONCISO de UNA SOLA PÁGINA...",
    'tecnologia': "Genera un análisis TECNOLÓGICO detallado en español...",
    'tfg': "Genera un resumen en formato de TRABAJO FIN DE GRADO (TFG)...",
}
prompt = prompts_map.get(cv_type, prompts_map['extenso'])
prompt += f"\n\nContenido del proyecto:\n{contenido_texto}"
```

### ¿Qué es un prompt?
Es la instrucción de texto que le das al modelo de IA. Cuanto más específico sea, mejor será la respuesta. Aquí le damos:
1. **Instrucciones** → qué formato queremos (extenso, corto, técnico, académico)
2. **Contexto** → el contenido real del proyecto (descripción, README, lenguajes, etc.)

### 6.5. Llamar a la API de Gemini

```python
from google import genai

client = genai.Client(api_key=profile.gemini_api_key)

modelos = ["gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.0-flash"]
for modelo in modelos:
    for intento in range(2):  # 2 intentos por modelo
        try:
            response = client.models.generate_content(
                model=modelo, contents=prompt
            )
            resumen_texto = response.text
            break
        except Exception as model_err:
            err_str = str(model_err)
            if "RESOURCE_EXHAUSTED" in err_str or "not found" in err_str.lower():
                break    # cuota agotada → siguiente modelo
            if "UNAVAILABLE" in err_str and intento == 0:
                time.sleep(3)  # servidor saturado → esperar 3s y reintentar
                continue
            raise model_err
    if resumen_texto:
        break
```

### ¿Cómo funciona el sistema de fallback?

```
gemini-2.5-pro  ──→ ¿Funciona? → SÍ → Usar respuesta ✅
       │                           
       └─→ NO (cuota/error) → gemini-2.5-flash ──→ ¿Funciona? → SÍ → ✅
                                      │
                                      └─→ NO → gemini-2.0-flash ──→ ¿Funciona? → SÍ → ✅
                                                     │
                                                     └─→ NO → Mostrar error ❌
```

Para cada modelo, si devuelve **503 UNAVAILABLE** (servidor saturado), espera 3 segundos y reintenta UNA vez ese mismo modelo antes de pasar al siguiente.

### 6.6. Convertir Markdown a HTML

Gemini devuelve texto en formato Markdown. Lo convertimos a HTML para mostrarlo bonito:

```python
import markdown

resumen_html = markdown.markdown(
    resumen_texto, 
    extensions=['extra', 'codehilite', 'tables', 'fenced_code']
)
```

Las extensiones permiten renderizar:
- `extra` → abreviaciones, footnotes, etc.
- `codehilite` → resaltado de código
- `tables` → tablas markdown
- `fenced_code` → bloques de código con \`\`\`

### 6.7. Renderizar el template

```python
return render(request, 'portfolioCV/gemini_resumen.html', {
    'resumen_html': resumen_html,
    'resumen_texto': resumen_texto,
    'error_msg': error_msg,
    'platform': platform,
    'item_id': item_id,
    'item_name': item_name,
    'cv_type': cv_type,
    'cv_type_label': cv_type_labels.get(cv_type, cv_type),
})
```

---

## 7. El formulario del selector — `repo_detalle.html`

En la página de detalle de cada repo, se añadió una sección con 4 radio buttons estilizados:

```html
<div class="detail-card gemini-section">
    <h2>🤖 Resumen con Inteligencia Artificial</h2>
    
    <form method="post" action="{% url 'generar_resumen_gemini' %}">
        {% csrf_token %}
        
        <!-- Datos ocultos del repo -->
        <input type="hidden" name="platform" value="GitHub">
        <input type="hidden" name="id" value="{{ owner }}/{{ repo_name }}">
        <input type="hidden" name="name" value="{{ repo.name }}">

        <!-- Selector de tipo de CV -->
        <div class="cv-type-selector">
            <label class="cv-type-option">
                <input type="radio" name="cv_type" value="extenso" checked>
                <span class="cv-type-card">
                    <span class="cv-type-icon">📝</span>
                    <span class="cv-type-label">CV Extenso</span>
                    <span class="cv-type-desc">Detallado y completo</span>
                </span>
            </label>
            <!-- ... más opciones (una_pagina, tecnologia, tfg) ... -->
        </div>

        <button type="submit">🤖 Generar Resumen con Gemini AI</button>
    </form>
</div>
```

### ¿Cómo funciona el selector visual?
1. Los `<input type="radio">` están ocultos con CSS (`display: none`)
2. El `<span class="cv-type-card">` es la tarjeta visible
3. Cuando se selecciona un radio, el CSS lo detecta con `:checked + .cv-type-card` y cambia el estilo (borde morado, fondo claro)

---

## 8. El template de resultado — `gemini_resumen.html`

```html
{% extends "portfolioCV/base.html" %}

{% block content %}
<h1>🤖 {{ cv_type_label }}</h1>

{% if error_msg %}
    <div class="alert alert-error">{{ error_msg }}</div>
{% endif %}

{% if resumen_html %}
    <div class="gemini-result-card">
        <!-- Badge morado indicando que es IA -->
        <div class="gemini-badge">
            <span>🤖 Generado por Gemini AI</span>
            <span>{{ cv_type_label }}</span>
        </div>
        
        <!-- El contenido HTML generado por Gemini -->
        <div class="gemini-content">
            {{ resumen_html|safe }}
        </div>
    </div>
{% endif %}
{% endblock %}
```

### ¿Qué es `|safe`?
- Por seguridad, Django escapa todo el HTML por defecto (convierte `<h1>` en `&lt;h1&gt;`)
- `|safe` le dice a Django que confíe en ese HTML y lo renderice como tal
- Lo usamos porque el HTML viene de nuestra conversión Markdown, no del usuario

---

## 9. Los estilos CSS — `style.css`

### Sección de Gemini (fondo degradado morado)
```css
.gemini-section {
    border: 1px solid #c9b1ff;
    background: linear-gradient(135deg, #faf5ff 0%, #f0ebff 100%);
}
```

### Selector de tipo de CV (tarjetas interactivas)
```css
/* Ocultar el radio button nativo */
.cv-type-option input[type="radio"] {
    display: none;
}

/* Estilo de la tarjeta */
.cv-type-card {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 1.25rem 0.75rem;
    background: white;
    border: 2px solid #e5e7eb;
    border-radius: 8px;
    transition: all 0.25s;
}

/* Cuando está seleccionado → borde morado + fondo lila */
.cv-type-option input[type="radio"]:checked + .cv-type-card {
    border-color: #7c3aed;
    background: #ede9fe;
    box-shadow: 0 0 0 3px rgba(124, 58, 237, 0.15);
}

/* Hover → borde suave + elevar */
.cv-type-card:hover {
    border-color: #a78bfa;
    transform: translateY(-2px);
}
```

### Badge de resultado (gradiente morado)
```css
.gemini-badge {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.6rem 1rem;
    background: linear-gradient(135deg, #7c3aed, #a78bfa);
    color: white;
    border-radius: 8px;
    font-weight: 600;
}
```

---

## 10. Flujo completo (resumen visual)

```
┌──────────────┐     ┌─────────────────┐     ┌───────────────────┐
│  1. Usuario  │     │  2. Configurar  │     │  3. Ir a un repo  │
│  se registra │ ──→ │  API Key Gemini │ ──→ │  (GitHub/GitLab/  │
│  e inicia    │     │  en /tokens/    │     │   OpenAlex)       │
│  sesión      │     │                 │     │                   │
└──────────────┘     └─────────────────┘     └───────┬───────────┘
                                                     │
                                                     ▼
┌──────────────────────────────────────────────────────────────────┐
│  4. En la página de detalle del repo:                           │
│                                                                  │
│  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐                        │
│  │  📝  │  │  📄  │  │  💻  │  │  🎓  │  ← Seleccionar tipo   │
│  │Extenso│  │1 Pág │  │ Tech │  │ TFG  │                        │
│  └──────┘  └──────┘  └──────┘  └──────┘                        │
│                                                                  │
│  [🤖 Generar Resumen con Gemini AI]  ← Pulsar botón            │
└──────────────────────────────────────┬───────────────────────────┘
                                       │
                                       ▼
┌──────────────────────────────────────────────────────────────────┐
│  5. Django (views.py):                                           │
│                                                                  │
│  a) Recoge platform, id, cv_type del POST                       │
│  b) Llama a la API de la plataforma → obtiene README, desc...   │
│  c) Construye un prompt específico según el tipo de CV          │
│  d) Llama a Gemini con google.genai → obtiene texto Markdown    │
│  e) Convierte Markdown → HTML con la librería `markdown`        │
│  f) Renderiza gemini_resumen.html con el resultado              │
└──────────────────────────────────────┬───────────────────────────┘
                                       │
                                       ▼
┌──────────────────────────────────────────────────────────────────┐
│  6. Se muestra el resumen generado en pantalla                  │
│                                                                  │
│  ┌─────────────────────────────────────────────┐                │
│  │ 🤖 Generado por Gemini AI    CV Extenso    │  ← Badge      │
│  ├─────────────────────────────────────────────┤                │
│  │                                             │                │
│  │  # Resumen del Proyecto                     │                │
│  │  Este proyecto implementa...                │  ← Contenido  │
│  │                                             │                │
│  │  ## Tecnologías                             │                │
│  │  - Python, Django, SQLite3...               │                │
│  │                                             │                │
│  └─────────────────────────────────────────────┘                │
└──────────────────────────────────────────────────────────────────┘
```

---

## 11. Errores comunes y soluciones

| Error | Causa | Solución |
|-------|-------|----------|
| `429 RESOURCE_EXHAUSTED` | Cuota agotada del modelo | El sistema prueba automáticamente el siguiente modelo |
| `503 UNAVAILABLE` | Servidor Gemini saturado | Espera 3s y reintenta, luego pasa al siguiente modelo |
| `not found` | Modelo no existe | Pasa al siguiente modelo de la lista |
| "Configura tu API Key" | No hay clave guardada | Ir a `/tokens/` y añadir la clave |

---

## 12. Archivos involucrados (resumen)

| Archivo | Qué hace en la integración |
|---------|---------------------------|
| `requirements.txt` | Declara la dependencia `google-genai` |
| `models.py` | Almacena la API Key por usuario en la BD |
| `forms.py` | Formulario web para editar la API Key |
| `views.py` | Lógica: recopilar datos → prompt → llamar Gemini → respuesta |
| `urls.py` | Ruta `/gemini/resumen/` → función `generar_resumen_gemini` |
| `tokens.html` | Tarjeta de ayuda "cómo obtener la clave" |
| `repo_detalle.html` | Selector de tipo de CV + botón generar |
| `gemini_resumen.html` | Muestra el resultado formateado |
| `style.css` | Estilos del selector, badge y contenido |
