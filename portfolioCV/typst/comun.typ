// Piezas compartidas por las plantillas de PDF.
#import "@preview/cmarker:0.1.10"

#let primary = rgb("#0969da")
#let text-main = rgb("#24292f")
#let text-muted = rgb("#57606a")
#let border-c = rgb("#d0d7de")
#let border-suave = rgb("#eaecef")
#let bg-muted = rgb("#f6f8fa")

#let fuentes = ("Inter", "Noto Color Emoji")
#let fuente-mono = ("DejaVu Sans Mono", "Noto Color Emoji")

// Markdown escrito por usuarios, READMEs o la IA:
// - raw-typst: false → un <!--raw-typst ... --> NO ejecuta código Typst.
// - Solo se pintan las imágenes que Python ya descargó (imagenes: src original → fichero);
//   el resto se omite, así que ninguna ruta del Markdown puede leer otros ficheros.
#let alineado(attrs, cuerpo) = if lower(attrs.at("align", default: "")) == "center" {
  align(center, cuerpo)
} else { cuerpo }

// Imagen del Markdown como en el navegador: en <img width="850"> los números son px
// (cmarker los pasa como pt; 1px = 0,75pt) y nunca más ancha que el espacio disponible.
#let imagen-md(ruta, alt: none, width: auto, height: auto, ..args) = {
  let px(v) = if type(v) == length { v * 0.75 } else { v }
  let (ancho, alto) = (px(width), px(height))
  box(layout(espacio => {
    let (w, h) = (ancho, alto)
    if type(w) == length and w.to-absolute() > espacio.width {
      (w, h) = (100%, auto)  // se reduce al ancho disponible manteniendo la proporción
    }
    image(ruta, alt: alt, width: w, height: h, ..args)
  }))
}

#let md(texto, imagenes: (:)) = cmarker.render(
  texto,
  raw-typst: false,
  set-document-title: false,
  // <p align="center"> y <div align="center">, típicos en la cabecera de los README
  html: (p: (attrs, cuerpo) => block(alineado(attrs, cuerpo)), div: (attrs, cuerpo) => alineado(attrs, cuerpo)),
  scope: (image: (source, alt: none, ..args) => {
    // box: en línea, como en GitHub (varios badges seguidos en la misma fila)
    if source in imagenes { imagen-md(imagenes.at(source), alt: alt, ..args) }
  }),
)

// Pie con "página / total" y línea superior, igual que tenía el PDF de Chromium
#let pie = context {
  line(length: 100%, stroke: 0.75pt + border-suave)
  v(-6pt)
  align(center, text(size: 6pt, fill: text-muted)[#counter(page).display() / #counter(page).final().first()])
}

#let cabecera(texto) = align(right, text(size: 6.75pt, fill: text-muted, texto))

// Estilos tipo GitHub para bloques de código, citas, tablas e imágenes del Markdown
#let estilos-markdown(cuerpo) = {
  show raw: set text(font: fuente-mono, size: 9pt)
  show raw.where(block: true): it => block(
    width: 100%, fill: bg-muted, inset: 7.5pt, radius: 4pt, stroke: 0.75pt + border-c,
    text(size: 8.5pt, it),
  )
  show quote.where(block: true): it => block(
    stroke: (left: 3pt + border-c), inset: (left: 8pt, y: 2pt),
    text(fill: text-muted, it.body),
  )
  set table(stroke: 0.75pt + border-c, inset: 5pt, fill: (_, y) => if y == 0 { bg-muted })
  show table.cell.where(y: 0): set text(weight: "bold")
  show link: set text(fill: primary)
  cuerpo
}
