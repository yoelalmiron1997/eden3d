// © 2026 Eden3D — Yoel Almirón. Todos los derechos reservados.
// Conexión con Supabase (login y roles). La URL y la clave "anon" son públicas por
// diseño (viajan igual a cada navegador): lo que protege los datos son las reglas
// (RLS) de supabase/esquema.sql. NUNCA poner acá la clave service_role.
// Si existen las variables del repo SUPABASE_URL / SUPABASE_ANON_KEY, el build las usa.
export const SUPABASE = {
  url: "https://xjyerniuhecwdgfbteez.supabase.co",
  anonKey: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InhqeWVybml1aGVjd2RnZmJ0ZWV6Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTMxNDc2NDQsImV4cCI6MjEwODcyMzY0NH0._ot9U5JN_aUJsgKaLqbcZ2b6PqmGu7G6CSzsgSySOE4",
};
