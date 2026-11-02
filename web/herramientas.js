// © 2026 TecnoBear — Yoel Almirón. Todos los derechos reservados.
// Catálogo del inicio: una entrada por herramienta. Para sumar una herramienta nueva,
// agregá su entrada acá (y su pop-up en index.html si querés uno con detalles).
// La imagen de la tarjeta es apaisada (12:5): <id>_card.jpg (1200×500) y <id>_card_600.jpg.
// etiqueta: el cartelito arriba a la izquierda; rubros: los dos de abajo, con su ícono.
export const CATEGORIAS = [
  { id: "impresion", nombre: "Impresión 3D", icono: "cubo" },
  { id: "personalizacion", nombre: "Personalización", icono: "lapiz" },
  { id: "entretenimiento", nombre: "Entretenimiento", icono: "pieza" },
];

export const HERRAMIENTAS = [
  {
    id: "macetas", ruta: "macetas.html", modal: "tool-modal", categoria: "impresion",
    nombre: "Generador de macetas con autorriego", corto: "Macetas con autorriego",
    descripcion: "Diseñá macetas en 3D con autorriego, listas para imprimir y con su guía de cuidados.",
    imagen: "assets/herramientas/macetas_card_600.jpg", imagen2x: "assets/herramientas/macetas_card.jpg",
    alt: "Maceta clara impresa en 3D con una suculenta, sobre su plato con agua, en una mesa de madera en el jardín",
    testImagen: "tool-imagen", foco: "50% 50%",
    etiqueta: { icono: "cubo", texto: "Impresión 3D" }, rubros: [{ icono: "cubo", texto: "Impresión 3D" }, { icono: "planta", texto: "Hogar y plantas" }],
  },
  {
    id: "mate", ruta: "mate.html", modal: "mate-modal", categoria: "impresion",
    nombre: "Mate con hueco", corto: "Mate con hueco",
    descripcion: "Elegí el modelo de mate y generá el hueco exacto para tu polímero escalonado o polímero base.",
    imagen: "assets/herramientas/mate_card_600.jpg", imagen2x: "assets/herramientas/mate_card.jpg",
    alt: "Mate impreso en 3D color terracota con su bombilla, sobre una mesa de madera en el jardín",
    testImagen: "tool-imagen-mate", foco: "50% 45%",
    etiqueta: { icono: "cubo", texto: "Impresión 3D" }, rubros: [{ icono: "cubo", texto: "Impresión 3D" }, { icono: "engranaje", texto: "Accesorios" }],
  },
  {
    id: "sopa", ruta: "sopa.html", modal: "sopa-modal", categoria: "entretenimiento",
    nombre: "Sopa de letras 3D", corto: "Sopa de letras 3D",
    descripcion: "Escribí tus palabras, generá tu sopa de letras y bajá las piezas listas para imprimir.",
    imagen: "assets/herramientas/sopa_card_600.jpg", imagen2x: "assets/herramientas/sopa_card.jpg",
    alt: "Sopa de letras impresa en 3D, blanca con letras rojas en relieve, con la lista de palabras",
    testImagen: "tool-imagen-sopa", foco: "50% 50%",
    etiqueta: { icono: "pieza", texto: "Entretenimiento" }, rubros: [{ icono: "pieza", texto: "Entretenimiento" }, { icono: "birrete", texto: "Educativo" }],
  },
  {
    id: "topper", ruta: "topper.html", modal: "topper-modal", categoria: "personalizacion",
    nombre: "Topper para tortas", corto: "Topper para tortas",
    descripcion: "Escribí el texto, elegí la tipografía y generá tu topper listo para imprimir.",
    imagen: "assets/herramientas/topper_card_600.jpg", imagen2x: "assets/herramientas/topper_card.jpg",
    alt: "Topper impreso en 3D que dice Feliz Cumpleaños y un número 1 con estrellas, clavado en una torta",
    testImagen: "tool-imagen-topper", foco: "50% 50%",
    etiqueta: { icono: "lapiz", texto: "Personalización" }, rubros: [{ icono: "lapiz", texto: "Personalización" }, { icono: "torta", texto: "Eventos" }],
  },
  {
    id: "chapita", ruta: "chapita.html", modal: "chapita-modal", categoria: "personalizacion",
    nombre: "Chapitas para collares", corto: "Chapitas para collares",
    descripcion: "Creá la chapita de tu mascota con su nombre, patitas y la forma que quieras.",
    imagen: "assets/herramientas/chapita_card_600.jpg", imagen2x: "assets/herramientas/chapita_card.jpg",
    alt: "Chapita impresa en 3D con forma de hueso, azul con el nombre Roma, borde y patitas en blanco, sobre una mesa de madera",
    testImagen: "tool-imagen-chapita", foco: "50% 50%",
    etiqueta: { icono: "destello", texto: "Nuevo" }, rubros: [{ icono: "lapiz", texto: "Personalización" }, { icono: "pata", texto: "Mascotas" }],
  },
  {
    id: "trofeo", ruta: "trofeo.html", modal: "trofeo-modal", categoria: "personalizacion",
    nombre: "Trofeos para eventos", corto: "Trofeos para eventos",
    descripcion: "Diseñá trofeos con figura, texto y base, listos para imprimir en 3D.",
    imagen: "assets/herramientas/trofeo_card_600.jpg", imagen2x: "assets/herramientas/trofeo_card.jpg",
    alt: "Trofeo impreso en 3D: una estrella dorada sobre una base negra que dice Campeón, Torneo 2026, en una oficina",
    testImagen: "tool-imagen-trofeo", foco: "60% 50%",
    etiqueta: { icono: "destello", texto: "Nuevo" }, rubros: [{ icono: "lapiz", texto: "Personalización" }, { icono: "copa", texto: "Eventos" }],
  },
];

export const REDES = [
  { id: "youtube", nombre: "YouTube", usuario: "@TecnoBearARG", url: "https://www.youtube.com/@TecnoBearARG" },
  { id: "instagram", nombre: "Instagram", usuario: "@tecnobearr", url: "https://www.instagram.com/tecnobearr/" },
];
