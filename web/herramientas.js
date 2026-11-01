// © 2026 TecnoBear — Yoel Almirón. Todos los derechos reservados.
// Catálogo del inicio: una entrada por herramienta. Para sumar una herramienta nueva,
// agregá su entrada acá (y su pop-up en index.html si querés uno con detalles).
export const CATEGORIAS = [
  { id: "impresion", nombre: "Impresión 3D", icono: "cubo" },
  { id: "personalizacion", nombre: "Personalización", icono: "lapiz" },
  { id: "entretenimiento", nombre: "Entretenimiento", icono: "pieza" },
];

export const HERRAMIENTAS = [
  {
    id: "macetas", ruta: "macetas.html", modal: "tool-modal", categoria: "impresion",
    nombre: "Generador de macetas", corto: "Macetas con autorriego",
    descripcion: "Diseñá macetas con autorriego para imprimir en 3D, con plantas y su guía de cuidados.",
    imagen: "assets/herramientas/macetas_v_450.jpg", imagen2x: "assets/herramientas/macetas_v.jpg",
    alt: "Maceta con autorriego desarmada: planta, tierra, maceta y plato con agua, sobre una mesa de jardín",
    testImagen: "tool-imagen", foco: "50% 62%",
  },
  {
    id: "mate", ruta: "mate.html", modal: "mate-modal", categoria: "impresion",
    nombre: "Mate con hueco", corto: "Mate con hueco",
    descripcion: "Elegí el modelo de mate y el motor le hace el hueco exacto para tu polímero escalonado o polímero base.",
    imagen: "assets/herramientas/mate_v_450.jpg", imagen2x: "assets/herramientas/mate_v.jpg",
    alt: "Mate impreso en 3D con yerba y bombilla, al lado del polímero escalonado y el polímero base, sobre una mesa de jardín",
    testImagen: "tool-imagen-mate", foco: "50% 60%",
  },
  {
    id: "sopa", ruta: "sopa.html", modal: "sopa-modal", categoria: "entretenimiento",
    nombre: "Sopa de letras 3D", corto: "Sopa de letras 3D",
    descripcion: "Escribí tus palabras y bajá la sopa para imprimir, cortada en piezas que encastran como un rompecabezas.",
    imagen: "assets/herramientas/sopa_v_450.jpg", imagen2x: "assets/herramientas/sopa_v.jpg",
    alt: "Sopa de letras impresa en 3D, en piezas de rompecabezas que encastran, con letras rojas en relieve",
    testImagen: "tool-imagen-sopa", foco: "50% 55%",
  },
  {
    id: "topper", ruta: "topper.html", modal: "topper-modal", categoria: "personalizacion",
    nombre: "Topper para tortas", corto: "Topper para tortas",
    descripcion: "Escribí el texto y el nombre, elegí la tipografía y bajá el topper listo para imprimir, todo unido.",
    imagen: "assets/herramientas/topper_v_450.jpg", imagen2x: "assets/herramientas/topper_v.jpg",
    alt: "Topper impreso en 3D que dice Feliz Cumpleaños Sofi y el número 5 con estrellas, en lila y blanco, clavados en una torta de crema",
    testImagen: "tool-imagen-topper", foco: "50% 48%",
  },
  {
    id: "chapita", ruta: "chapita.html", modal: "chapita-modal", categoria: "personalizacion",
    nombre: "Chapitas para collares", corto: "Chapitas para collares",
    descripcion: "El nombre de tu perro o gato en una chapita con forma de hueso, gato, corazón o pescado, lista para el collar.",
    imagen: "assets/herramientas/chapita_v_450.jpg", imagen2x: "assets/herramientas/chapita_v.jpg",
    alt: "Chapita impresa en 3D con forma de hueso, azul con el nombre Roma, borde y patitas en blanco, con su argolla, sobre una mesa de madera",
    testImagen: "tool-imagen-chapita", foco: "50% 50%",
  },
];

export const REDES = [
  { id: "youtube", nombre: "YouTube", usuario: "@TecnoBearARG", url: "https://www.youtube.com/@TecnoBearARG" },
  { id: "instagram", nombre: "Instagram", usuario: "@tecnobearr", url: "https://www.instagram.com/tecnobearr/" },
];
