// PDF del CV profesional (la cesta): datos personales, foto, Sobre mí y proyectos.
// Los datos del usuario llegan como JSON en sys.inputs.data y NUNCA se pegan en este
// código, así que un nombre o una descripción no pueden inyectar marcado de Typst.
#import "comun.typ": *

#let d = json(bytes(sys.inputs.data))
#let info = d.personal_info
#let nombre = if info.at("name", default: "") != "" { info.name } else { d.username }

#set document(title: "Curriculum Vitae Profesional")
#set page(
  paper: "a4",
  margin: (top: 25mm, bottom: 25mm, left: 15mm, right: 15mm),
  header: cabecera[CV Profesional — #nombre],
  footer: pie,
)
#set text(font: fuentes, size: 11pt, fill: text-main, lang: "es")
#set par(leading: 0.65em, spacing: 1em)
#set list(spacing: 0.75em, indent: 6pt)
#set enum(spacing: 0.75em, indent: 6pt)
#show: estilos-markdown
#show raw.where(block: false): it => box(fill: bg-muted, inset: (x: 3pt), outset: (y: 2.5pt), radius: 3pt, it)
// sticky: un título nunca se queda solo al final de una página, separado de su contenido
#show heading.where(level: 2): it => block(below: 11pt, above: 18pt, sticky: true, {
  text(size: 16pt, weight: "bold", it.body)
  v(-2pt)
  line(length: 100%, stroke: 0.75pt + border-c)
})
// Títulos dentro de "Sobre mí" y de los resúmenes de la IA (su "#" llega como nivel 3)
#show heading.where(level: 3): it => block(above: 12pt, below: 6pt, sticky: true, text(size: 12.5pt, weight: "bold", it.body))
#show heading.where(level: 4): it => block(above: 10pt, below: 5pt, sticky: true, text(size: 11pt, weight: "bold", it.body))
#show heading: it => if it.level >= 5 {
  block(above: 8pt, below: 4pt, sticky: true, text(size: 10.5pt, weight: "bold", it.body))
} else { it }

#let badge(cuerpo, fondo: bg-muted, color: text-main, borde: border-c) = box(
  fill: fondo, stroke: if borde == none { none } else { 0.75pt + borde },
  radius: 9pt, inset: (x: 5.5pt, y: 3pt), baseline: 3pt,
  text(size: 8pt, weight: "medium", fill: color, cuerpo),
)

// 1520 → "1.520" (separador de miles en español)
#let miles(n) = {
  let cifras = str(n)
  let grupos = ()
  while cifras.len() > 3 {
    grupos.insert(0, cifras.slice(cifras.len() - 3))
    cifras = cifras.slice(0, cifras.len() - 3)
  }
  grupos.insert(0, cifras)
  grupos.join(".")
}
#let emoji(e) = text(font: "Noto Color Emoji", e)  // Inter tiene su propio ❤ en negro

#let colores-plataforma = (
  "GitHub": (rgb("#24292f"), white),
  "OpenAlex": (rgb("#f39c12"), white),
  "Hugging Face": (rgb("#ffd21e"), rgb("#3a3b45")),
  "IA Summary": (rgb("#2ea043"), white),
)

// ── Cabecera ──────────────────────────────────────────────
#let contacto = ()
#if info.at("phone", default: "") != "" { contacto.push[📞 #info.phone] }
#if info.at("email", default: "") != "" { contacto.push[✉️ #info.email] }
#if info.at("linkedin", default: "") != "" {
  contacto.push[🔗 #link(d.linkedin_url, text(fill: primary, info.linkedin))]
}
#block(below: 15pt, {
  grid(
    columns: if d.foto != none { (75pt, 1fr) } else { (1fr,) },
    column-gutter: 19pt,
    align: horizon,
    ..if d.foto != none { (box(clip: true, radius: 50%, stroke: 0.75pt + border-c,
                        image(d.foto, width: 75pt, height: 75pt, fit: "cover")),) },
    {
      text(size: 24pt, weight: "bold", nombre)
      if info.at("headline", default: "") != "" {
        v(-6pt)
        text(size: 12.5pt, fill: text-muted, weight: "medium", info.headline)
      }
      if contacto.len() > 0 {
        v(-4pt)
        text(size: 10pt, fill: text-muted, contacto.map(box).join(h(11pt)))
      }
    },
  )
  v(4pt)
  line(length: 100%, stroke: 1.5pt + border-c)
})

// ── Sobre mí ──────────────────────────────────────────────
#if info.at("about", default: "") != "" [
  == Sobre Mí
  #block(width: 100%, fill: bg-muted, inset: 11pt, radius: 4.5pt, stroke: 0.75pt + border-c,
    text(size: 10.5pt, md(info.about, nivel-titulos: 3)))
]

// ── Proyectos ─────────────────────────────────────────────
== Proyectos y Publicaciones Destacadas

#if d.items.len() == 0 [
  No se han registrado proyectos en este CV.
] else {
  for item in d.items {
    let plataforma = item.at("platform", default: "")
    let (fondo, color) = colores-plataforma.at(plataforma, default: (rgb("#fc6d26"), white))
    let dato(clave) = item.at(clave, default: none)
    let hay(clave) = dato(clave) not in (none, "", 0, ())
    block(below: 20pt, {
      // Título, etiquetas, descripción y enlaces van juntos y pegados a lo que sigue (sin huérfanos)
      block(breakable: false, sticky: true, below: 8pt, {
        grid(
          columns: (1fr, auto),
          column-gutter: 10pt,
          align: (left + bottom, right + bottom),
          text(size: 13pt, weight: "semibold", str(item.at("name", default: ""))),
          if hay("periodo") { text(size: 9pt, fill: text-muted, str(dato("periodo"))) },
        )
        v(-1pt)
        // Etiquetas: plataforma, lenguajes con % (o el principal) y cifras
        let cifras = ()
        if hay("estrellas") { cifras.push[#emoji("⭐") #miles(dato("estrellas"))] }
        if hay("forks") { cifras.push[#miles(dato("forks")) forks] }
        if hay("likes") { cifras.push[#emoji("❤️") #miles(dato("likes"))] }
        if hay("descargas") { cifras.push[#miles(dato("descargas")) descargas] }
        if hay("citas") { cifras.push[#miles(dato("citas")) citas] }
        if hay("licencia") { cifras.push(str(dato("licencia"))) }
        if hay("revista") { cifras.push(emph(str(dato("revista")))) }
        text(size: 9pt, fill: text-muted, {
          badge(plataforma, fondo: fondo, color: color, borde: none)
          let lenguajes = item.at("lenguajes", default: ())
          if lenguajes.len() > 0 {
            for l in lenguajes.slice(0, calc.min(4, lenguajes.len())) {
              h(4pt)
              badge[#l.name #str(calc.round(float(l.pct))) %]
            }
            if lenguajes.len() > 4 { h(4pt); badge[+#(lenguajes.len() - 4)] }
          } else if hay("language") {
            h(4pt)
            badge[💻 #dato("language")]
          }
          if cifras.len() > 0 {
            h(8pt)
            cifras.join([ · ])
          }
        })
        if hay("description") {
          v(-2pt)
          text(size: 10pt, str(dato("description")))
        }
        // Enlaces visibles también en papel: sin "https://", la web en vivo primero
        let corta(url) = url.replace(regex("^https?://(www\\.)?"), "").trim("/", at: end)
        let enlaces = ()
        if hay("homepage") { enlaces.push(link(dato("homepage"))[🌐 #corta(dato("homepage"))]) }
        if hay("url") { enlaces.push(link(dato("url"))[🔗 #corta(dato("url"))]) }
        if hay("doi") { enlaces.push(link(dato("doi"))[📄 #corta(dato("doi"))]) }
        if enlaces.len() > 0 {
          v(-4pt)
          text(size: 9pt, fill: primary, enlaces.join(h(12pt)))
        }
        let topics = item.at("topics", default: ())
        if topics.len() > 0 {
          v(-4pt)
          text(size: 8.5pt, fill: text-muted, topics.map(t => "#" + str(t)).join("  "))
        }
      })
      if plataforma == "IA Summary" and item.at("content", default: "") != "" {
        block(width: 100%, fill: bg-muted, inset: 7.5pt, radius: 4.5pt, stroke: 0.75pt + border-c,
          text(size: 10pt, md(item.content, nivel-titulos: 3)))
      }
    })
  }
}
