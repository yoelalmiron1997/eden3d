// © 2026 Eden3D — Yoel Almirón. Todos los derechos reservados.
// Cuentas y roles con Supabase.
//   visitante: mira y configura (si Supabase no está configurado, también descarga)
//   usuario:   descarga con la marca Eden3D
//   pro:       paquete extra, cambia el texto de la marca de agua
//   admin:     todo lo anterior + panel de administración (usuarios y cobertura)
// Las reglas que importan (quién cambia roles) viven en la base (RLS), no acá.
import { SUPABASE } from "./config.js";

export const ROLES = {
  // premium: render (foto) y PDF con consideraciones de impresión (plan Premium = Pro)
  visitante: { label: "Visitante", download: false, brand: false, premium: false, admin: false },
  usuario: { label: "Usuario", download: true, brand: false, premium: false, admin: false },
  pro: { label: "Pro", download: true, brand: true, premium: true, admin: false },
  admin: { label: "Administrador", download: true, brand: true, premium: true, admin: true },
};

const SITIO = new URL("./", import.meta.url).href;   // raíz de la web (para los links de los emails)
const listeners = new Set();
const auth = { configured: false, client: null, user: null, role: "visitante", mock: false, ready: false };

function emit() {
  for (const fn of listeners) fn(snapshot());
}

export function snapshot() {
  const perms = { ...ROLES[auth.role] };
  // sin cuentas configuradas la web sigue funcionando como antes (descarga libre)
  if (!auth.configured) { perms.download = true; perms.premium = true; }   // sin cuentas: todo libre
  return { configured: auth.configured, user: auth.user, role: auth.role, perms, mock: auth.mock, ready: auth.ready };
}

export function onAuth(fn) {
  listeners.add(fn);
  if (auth.ready) fn(snapshot());
  return () => listeners.delete(fn);
}

function loadScript(src) {
  return new Promise((res, rej) => {
    const s = document.createElement("script");
    s.src = src;
    s.onload = res;
    s.onerror = () => rej(new Error("no se pudo cargar " + src));
    document.head.appendChild(s);
  });
}

async function loadRole() {
  if (!auth.user) { auth.role = "visitante"; return; }
  const { data, error } = await auth.client.from("perfiles").select("rol").eq("id", auth.user.id).maybeSingle();
  auth.role = !error && data && ROLES[data.rol] ? data.rol : "usuario";
}

// Para los tests e2e (sólo en localhost): window.__EDEN_AUTH_MOCK = {email, role}.
function mockFromWindow() {
  const local = ["localhost", "127.0.0.1"].includes(location.hostname);
  const m = local && window.__EDEN_AUTH_MOCK;
  if (!m) return false;
  auth.mock = true;
  if (m.role === "sin-cuentas") { auth.configured = false; return true; }   // como antes del login
  auth.configured = true;
  auth.user = m.role && m.role !== "visitante" ? { id: "mock", email: m.email || "test@eden3d.local" } : null;
  auth.role = auth.user ? m.role : "visitante";
  auth.mockUsers = m.users || [{ id: "mock", email: auth.user ? auth.user.email : "", rol: auth.role, creado: new Date().toISOString() }];
  return true;
}

export async function initAuth() {
  if (auth.ready) return snapshot();
  try {
    if (!mockFromWindow() && SUPABASE.url && SUPABASE.anonKey) {
      await loadScript(new URL("./vendor/supabase/supabase.js", import.meta.url).href);
      auth.client = window.supabase.createClient(SUPABASE.url, SUPABASE.anonKey);
      auth.configured = true;
      const { data } = await auth.client.auth.getSession();
      auth.user = data.session ? data.session.user : null;
      await loadRole();
      auth.client.auth.onAuthStateChange(async (_ev, session) => {
        auth.user = session ? session.user : null;
        await loadRole();
        emit();
      });
    }
  } catch (e) {
    console.error(e);
  }
  auth.ready = true;
  emit();
  return snapshot();
}

const fail = (error) => { if (error) throw new Error(traducir(error.message)); };

function traducir(m) {
  const t = {
    "Invalid login credentials": "Email o contraseña incorrectos.",
    "Email not confirmed": "Confirmá tu email: te mandamos un link.",
    "User already registered": "Ese email ya tiene cuenta. Ingresá.",
  };
  if (/at least 6 characters/i.test(m)) return "La contraseña tiene que tener al menos 6 caracteres.";
  return t[m] || m;
}

export async function signIn(email, password) {
  if (auth.mock) {
    const m = window.__EDEN_AUTH_MOCK;
    if (m.password && password !== m.password) throw new Error("Email o contraseña incorrectos.");
    auth.user = { id: "mock", email };
    auth.role = m.loginRole || (m.role !== "visitante" ? m.role : "usuario");
    emit();
    return;
  }
  const { error } = await auth.client.auth.signInWithPassword({ email, password });
  fail(error);
}

export async function signUp(email, password) {
  if (auth.mock) return signIn(email, password);
  const redirect = SITIO;
  const { data, error } = await auth.client.auth.signUp({ email, password, options: { emailRedirectTo: redirect } });
  fail(error);
  return { confirm: !data.session };
}

export async function resetPassword(email) {
  if (auth.mock) return;
  const { error } = await auth.client.auth.resetPasswordForEmail(email, { redirectTo: SITIO });
  fail(error);
}

export async function signOut() {
  if (auth.mock) { auth.user = null; auth.role = "visitante"; emit(); return; }
  await auth.client.auth.signOut();
}

// ---------------------------------------------------------------- perfil
// Datos del usuario en los metadatos de su cuenta de Supabase (no hace falta ninguna tabla):
// nombre, apellido, nacimiento, una imagen (foto chica o una prediseñada "av:<id>"),
// dónde vive, oficio, su impresora 3D, su Instagram y unas líneas sobre él.
export const CAMPOS_PERFIL = {
  nombre: 40, apellido: 40, ciudad: 50, provincia: 50, oficio: 50, impresora: 50, instagram: 31, bio: 240,
};

export function perfil() {
  const m = (auth.user && auth.user.user_metadata) || {};
  const p = { nacimiento: m.nacimiento || "", foto: m.foto || "" };
  for (const k of Object.keys(CAMPOS_PERFIL)) p[k] = m[k] || "";
  return p;
}

export async function guardarPerfil(datos) {
  if (!auth.user) throw new Error("Ingresá con tu cuenta para guardar tu perfil.");
  const d = { nacimiento: /^\d{4}-\d{2}-\d{2}$/.test(datos.nacimiento || "") ? datos.nacimiento : "", foto: datos.foto || "" };
  for (const [k, n] of Object.entries(CAMPOS_PERFIL)) d[k] = String(datos[k] || "").trim().replace(/\s+/g, " ").slice(0, n);
  d.instagram = d.instagram.replace(/^@+/, "").replace(/^https?:\/\/(www\.)?instagram\.com\//i, "").replace(/\/.*$/, "");
  if (d.instagram && !/^[A-Za-z0-9._]{1,30}$/.test(d.instagram)) throw new Error("El usuario de Instagram sólo lleva letras, números, punto y guion bajo.");
  const prediseñada = /^av:[a-z]+$/.test(d.foto);
  if (d.foto && !prediseñada && (!d.foto.startsWith("data:image/") || d.foto.length > 40000)) throw new Error("La foto es demasiado grande.");
  if (auth.mock) {
    auth.user = { ...auth.user, user_metadata: { ...(auth.user.user_metadata || {}), ...d } };
    emit();
    return perfil();
  }
  const { data, error } = await auth.client.auth.updateUser({ data: d });
  fail(error);
  auth.user = data.user;
  emit();
  return perfil();
}

// cómo se muestra alguien a los demás (feedback): su nombre o la parte de su email antes de la @
export function nombrePublico() {
  if (!auth.user) return "";
  const p = perfil();
  return [p.nombre, p.apellido].filter(Boolean).join(" ") || auth.user.email.split("@")[0];
}

// para el feedback (feedback.js): el cliente de Supabase o el modo de prueba
export function conexion() {
  return { client: auth.client, user: auth.user, mock: auth.mock, configured: auth.configured, role: auth.role };
}

// ---------------------------------------------------------------- administración
export async function listUsers() {
  if (auth.mock) return auth.mockUsers;
  const { data, error } = await auth.client.from("perfiles").select("id,email,rol,creado").order("creado", { ascending: false });
  fail(error);
  return data;
}

export async function setRole(id, rol) {
  if (!ROLES[rol] || rol === "visitante") throw new Error("rol inválido");
  if (auth.mock) { const u = auth.mockUsers.find((x) => x.id === id); if (u) u.rol = rol; return; }
  const { error } = await auth.client.from("perfiles").update({ rol }).eq("id", id);
  fail(error);
}
