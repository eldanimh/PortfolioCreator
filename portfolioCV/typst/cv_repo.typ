// PDF de un repositorio (GitHub, GitLab, Hugging Face) u obra de OpenAlex.
// Los datos llegan como JSON en sys.inputs.data y nunca se pegan en este código.
#import "comun.typ": *

#let d = json(bytes(sys.inputs.data))

#set document(title: d.nombre)
#set page(
  paper: "a4",
  margin: (top: 25mm, bottom: 25mm, left: 15mm, right: 15mm),
  header: cabecera[Portfolio CV — #d.username — #d.platform],
  footer: pie,
)
#set text(font: fuentes, size: 11pt, fill: text-main, lang: "es")
#set par(leading: 0.65em, spacing: 1em)
#show: estilos-markdown
#show raw.where(block: false): it => box(
  fill: bg-muted, inset: (x: 3pt), outset: (y: 2.5pt), radius: 3pt,
  text(fill: rgb("#d73a49"), size: 9.5pt, it),
)
#show heading: set text(fill: rgb("#1a1a2e"), weight: "bold")
#show heading: set block(above: 15pt, below: 10pt)
#show heading.where(level: 1): it => block(above: 15pt, below: 12pt, {
  text(size: 24pt, it.body)
  v(-4pt)
  line(length: 100%, stroke: 1.5pt + border-suave)
})
#show heading.where(level: 2): it => block(above: 18pt, below: 10pt, {
  text(size: 18pt, it.body)
  v(-4pt)
  line(length: 100%, stroke: 0.75pt + border-suave)
})
#show heading.where(level: 3): set text(size: 14pt)

= #d.nombre

#block(width: 100%, fill: bg-muted, stroke: 0.75pt + border-c, radius: 4.5pt, inset: 10pt, below: 15pt)[
  *Descripción:* #d.descripcion

  *URL:* #if d.url.starts-with("http") { link(d.url, d.url) } else { d.url }

  *Creado en:* #d.creado

  *Última actividad:* #d.actividad
]

== Tecnologías Utilizadas
#if d.lenguajes.len() > 0 {
  list(indent: 10pt, ..d.lenguajes.map(l => [*#l.name:* #calc.round(float(l.pct), digits: 1)%]))
} else [
  No se encontraron datos de lenguajes.
]

== Estructura del Proyecto
#block(width: 100%, fill: bg-muted, stroke: 0.75pt + border-c, radius: 4.5pt, inset: 8pt, {
  if d.arbol.len() > 0 {
    for fichero in d.arbol {
      block(width: 100%, inset: (x: 4pt, y: 3pt), above: 0pt, below: 0pt,
        stroke: (bottom: 0.75pt + border-suave),
        text(font: fuente-mono, size: 8pt, fill: primary)[📁 #fichero])
    }
  } else [
    No se encontraron archivos o no fue posible obtener el árbol.
  ]
})

#pagebreak()

== Contenido de README
#if d.readme.trim() != "" {
  md(d.readme, imagenes: d.imagenes)
} else [
  Repositorio sin README o vacío.
]
