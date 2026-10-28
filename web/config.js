// © 2026 Eden3D — Yoel Almirón. Todos los derechos reservados.
// Conexión con Supabase (login y roles). La URL y la clave "anon" son públicas por
// diseño: lo que protege los datos son las reglas (RLS) de supabase/esquema.sql.
// En GitHub se completan solas desde las variables del repositorio SUPABASE_URL y
// SUPABASE_ANON_KEY (ver docs/SUPABASE.md). Vacías = la web anda sin cuentas.
export const SUPABASE = { url: "", anonKey: "" };
