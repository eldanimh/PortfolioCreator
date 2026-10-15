// PDF del CV profesional (la cesta): datos personales, foto, Sobre mí y proyectos.
// Los datos del usuario llegan como JSON en sys.inputs.data y NUNCA se pegan en este
// código, así que un nombre o una descripción no pueden inyectar marcado de Typst.
#import "comun.typ": *

#let d = json(bytes(sys.inputs.data))
#let info = d.personal_info

#set document(title: "Curriculum Vitae Profesional")
#set page(
  paper: "a4",
  margin: (top: 25mm, bottom: 25mm, left: 15mm, right: 15mm),
  header: cabecera[CV Profesional — #d.username],
  footer: pie,
)
#set text(font: fuentes, size: 11pt, fill: text-main, lang: "es")
#set par(leading: 0.65em, spacing: 1em)
#set list(spacing: 0.75em, indent: 6pt)
#set enum(spacing: 0.75em, indent: 6pt)
#show: estilos-markdown
#show raw.where(block: false): it => box(fill: bg-muted, inset: (x: 3pt), outset: (y: 2.5pt), radius: 3pt, it)
#show heading.where(level: 2): it => block(below: 11pt, above: 18pt, {
  text(size: 16pt, weight: "bold", it.body)
  v(-2pt)
  line(length: 100%, stroke: 0.75pt + border-c)
})

#let badge(cuerpo, fondo: bg-muted, color: text-main, borde: border-c) = box(
  fill: fondo, stroke: if borde == none { none } else { 0.75pt + borde },
  radius: 9pt, inset: (x: 5.5pt, y: 3pt), baseline: 3pt,
  text(size: 8pt, weight: "medium", fill: color, cuerpo),
)

#let colores-plataforma = (
  "GitHub": (rgb("#24292f"), white),
  "OpenAlex": (rgb("#f39c12"), white),
  "Hugging Face": (rgb("#ffd21e"), rgb("#3a3b45")),
  "IA Summary": (rgb("#2ea043"), white),
)

// ── Cabecera ──────────────────────────────────────────────
#let nombre = if info.at("name", default: "") != "" { info.name } else { d.username }
#let contacto = ()
#if info.at("phone", default: "") != "" { contacto.push[📞 #info.phone] }
#if info.at("email", default: "") != "" { contacto.push[✉️ #info.email] }
#if info.at("linkedin", default: "") != "" {
  contacto.push[🔗 #link(d.linkedin_url, text(fill: primary, info.linkedin))]
}
#contacto.push[👤 Plataforma Portfolio Creator]

#block(below: 15pt, {
  grid(
    columns: if d.foto != none { (75pt, 1fr) } else { (1fr,) },
    column-gutter: 19pt,
    align: horizon,
    ..if d.foto != none { (box(clip: true, radius: 50%, stroke: 0.75pt + border-c,
                        image(d.foto, width: 75pt, height: 75pt, fit: "cover")),) },
    {
      text(size: 24pt, weight: "bold", nombre)
      v(-4pt)
      text(size: 10pt, fill: text-muted, contacto.map(box).join(h(11pt)))
    },
  )
  v(4pt)
  line(length: 100%, stroke: 1.5pt + border-c)
})

// ── Sobre mí ──────────────────────────────────────────────
#if info.at("about", default: "") != "" [
  == Sobre Mí
  #block(width: 100%, fill: bg-muted, inset: 11pt, radius: 4.5pt, stroke: 0.75pt + border-c,
    text(size: 10.5pt, md(info.about)))
]

// ── Proyectos ─────────────────────────────────────────────
== Proyectos y Publicaciones Destacadas

#if d.items.len() == 0 [
  No se han registrado proyectos en este CV.
] else {
  for item in d.items {
    let plataforma = item.at("platform", default: "")
    let (fondo, color) = colores-plataforma.at(plataforma, default: (rgb("#fc6d26"), white))
    block(below: 20pt, {
      grid(
        columns: (auto, 1fr),
        column-gutter: 8pt,
        text(size: 13pt, weight: "semibold", str(item.at("name", default: ""))),
        if item.at("url", default: "") != "" {
          align(right, link(item.url, text(size: 9pt, fill: primary, item.url)))
        },
      )
      v(-1pt)
      text(size: 9pt, fill: text-muted, {
        badge(plataforma, fondo: fondo, color: color, borde: none)
        if item.at("language", default: none) not in (none, "") {
          h(4pt)
          badge[💻 #item.language]
        }
        h(8pt)
        [ID: #str(item.at("id", default: ""))]
      })
      if item.at("description", default: none) not in (none, "") {
        v(-2pt)
        text(size: 10pt, str(item.description))
      }
      if plataforma == "IA Summary" and item.at("content", default: "") != "" {
        block(width: 100%, fill: bg-muted, inset: 7.5pt, radius: 4.5pt, stroke: 0.75pt + border-c,
          text(size: 10pt, md(item.content)))
      }
    })
  }
}
