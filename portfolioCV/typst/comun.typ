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

// Alertas de GitHub (> [!NOTE]...): Python las convierte en <gh-alerta tipo="note"> y aquí se
// pintan como en GitHub. Iconos: Octicons de GitHub (licencia MIT), 16×16.
#let alertas = (
  note: ("Nota", rgb("#0969da"), "M0 8a8 8 0 1 1 16 0A8 8 0 0 1 0 8Zm8-6.5a6.5 6.5 0 1 0 0 13 6.5 6.5 0 0 0 0-13ZM6.5 7.75A.75.75 0 0 1 7.25 7h1a.75.75 0 0 1 .75.75v2.75h.25a.75.75 0 0 1 0 1.5h-2a.75.75 0 0 1 0-1.5h.25v-2h-.25a.75.75 0 0 1-.75-.75ZM8 6a1 1 0 1 1 0-2 1 1 0 0 1 0 2Z"),
  tip: ("Consejo", rgb("#1a7f37"), "M8 1.5c-2.363 0-4 1.69-4 3.75 0 .984.424 1.625.984 2.304l.214.253c.223.264.47.556.673.848.284.411.537.896.621 1.49a.75.75 0 0 1-1.484.211c-.04-.282-.163-.547-.37-.847a8.456 8.456 0 0 0-.542-.68c-.084-.1-.173-.205-.268-.32C3.201 7.75 2.5 6.766 2.5 5.25 2.5 2.31 4.863 0 8 0s5.5 2.31 5.5 5.25c0 1.516-.701 2.5-1.328 3.259-.095.115-.184.22-.268.319-.207.245-.383.453-.541.681-.208.3-.33.565-.37.847a.751.751 0 0 1-1.485-.212c.084-.593.337-1.078.621-1.489.203-.292.45-.584.673-.848.075-.088.147-.173.213-.253.561-.679.985-1.32.985-2.304 0-2.06-1.637-3.75-4-3.75ZM5.75 12h4.5a.75.75 0 0 1 0 1.5h-4.5a.75.75 0 0 1 0-1.5ZM6 15.25a.75.75 0 0 1 .75-.75h2.5a.75.75 0 0 1 0 1.5h-2.5a.75.75 0 0 1-.75-.75Z"),
  important: ("Importante", rgb("#8250df"), "M0 1.75C0 .784.784 0 1.75 0h12.5C15.216 0 16 .784 16 1.75v9.5A1.75 1.75 0 0 1 14.25 13H8.06l-2.573 2.573A1.458 1.458 0 0 1 3 14.543V13H1.75A1.75 1.75 0 0 1 0 11.25Zm1.75-.25a.25.25 0 0 0-.25.25v9.5c0 .138.112.25.25.25h2a.75.75 0 0 1 .75.75v2.19l2.72-2.72a.749.749 0 0 1 .53-.22h6.5a.25.25 0 0 0 .25-.25v-9.5a.25.25 0 0 0-.25-.25Zm7 2.25v2.5a.75.75 0 0 1-1.5 0v-2.5a.75.75 0 0 1 1.5 0ZM9 9a1 1 0 1 1-2 0 1 1 0 0 1 2 0Z"),
  warning: ("Advertencia", rgb("#9a6700"), "M6.457 1.047c.659-1.234 2.427-1.234 3.086 0l6.082 11.378A1.75 1.75 0 0 1 14.082 15H1.918a1.75 1.75 0 0 1-1.543-2.575Zm1.763.707a.25.25 0 0 0-.44 0L1.698 13.132a.25.25 0 0 0 .22.368h12.164a.25.25 0 0 0 .22-.368Zm.53 3.996v2.5a.75.75 0 0 1-1.5 0v-2.5a.75.75 0 0 1 1.5 0ZM9 11a1 1 0 1 1-2 0 1 1 0 0 1 2 0Z"),
  caution: ("Precaución", rgb("#cf222e"), "M4.47.22A.749.749 0 0 1 5 0h6c.199 0 .389.079.53.22l4.25 4.25c.141.14.22.331.22.53v6a.749.749 0 0 1-.22.53l-4.25 4.25A.749.749 0 0 1 11 16H5a.749.749 0 0 1-.53-.22L.22 11.53A.749.749 0 0 1 0 11V5c0-.199.079-.389.22-.53Zm.84 1.28L1.5 5.31v5.38l3.81 3.81h5.38l3.81-3.81V5.31L10.69 1.5ZM8 4a.75.75 0 0 1 .75.75v3.5a.75.75 0 0 1-1.5 0v-3.5A.75.75 0 0 1 8 4Zm0 8a1 1 0 1 1 0-2 1 1 0 0 1 0 2Z"),
)

#let alerta(attrs, cuerpo) = {
  let (titulo, color, icono) = alertas.at(lower(attrs.at("tipo", default: "note")), default: alertas.note)
  let svg = "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16'><path fill='" + color.to-hex() + "' d='" + icono + "'/></svg>"
  block(width: 100%, stroke: (left: 3pt + color), inset: (left: 10pt, y: 4pt), above: 10pt, below: 10pt, {
    text(fill: color, weight: "semibold")[#box(image(bytes(svg), format: "svg", height: 0.9em), baseline: 0.1em) #h(3pt) #titulo]
    v(-2pt)
    cuerpo
  })
}

// nivel-titulos: a qué nivel bajan los "# Título" del Markdown (3 → por debajo de las
// secciones del documento, para que un resumen de la IA no tenga títulos más grandes que el CV)
#let md(texto, imagenes: (:), nivel-titulos: 1) = cmarker.render(
  texto,
  raw-typst: false,
  set-document-title: false,
  h1-level: nivel-titulos,
  // <p align="center"> y <div align="center">, típicos en la cabecera de los README
  html: (
    p: (attrs, cuerpo) => block(alineado(attrs, cuerpo)),
    div: (attrs, cuerpo) => alineado(attrs, cuerpo),
    gh-alerta: alerta,
  ),
  scope: (image: (source, alt: none, ..args) => {
    // box: en línea, como en GitHub (varios badges seguidos en la misma fila)
    if source in imagenes { imagen-md(imagenes.at(source), alt: alt, ..args) }
  }),
)

// Pie con "página / total" y línea superior, igual que tenía el PDF de Chromium
#let pie = context {
  line(length: 100%, stroke: 0.75pt + border-suave)
  v(-6pt)
  grid(
    columns: (1fr, auto, 1fr),
    align: (left, center, right),
    text(size: 6pt, fill: text-muted)[Creado con #link("https://creator.danimh.dev", text(fill: primary)[Portfolio Creator])],
    text(size: 6pt, fill: text-muted)[#counter(page).display() / #counter(page).final().first()],
    [],
  )
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
