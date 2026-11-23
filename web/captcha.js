// © 2026 TecnoBear — Yoel Almirón. Todos los derechos reservados.
// Captcha (Cloudflare Turnstile) para crear cuenta, ingresar y recuperar la contraseña.
// Supabase lo exige cuando se activa en Authentication → Attack Protection; la clave del
// sitio sale de la variable TURNSTILE_SITE_KEY del build. Sin clave, no hay captcha.
import { CAPTCHA } from "./config.js";

const SCRIPT = "https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit";
let carga = null;

export const captchaActivo = () => !!(CAPTCHA && CAPTCHA.siteKey);

function cargar() {
  if (window.turnstile) return Promise.resolve(window.turnstile);
  if (!carga) {
    carga = new Promise((res, rej) => {
      const s = document.createElement("script");
      s.src = SCRIPT;
      s.async = true;
      s.onload = () => res(window.turnstile);
      s.onerror = () => { carga = null; rej(new Error("No se pudo cargar la verificación anti-robots. Revisá tu conexión.")); };
      document.head.appendChild(s);
    });
  }
  return carga;
}

// Un widget dentro de `el`. token() espera a que Cloudflare dé el visto bueno (casi
// siempre es invisible; a veces pide un clic). Cada token sirve una sola vez: reiniciar().
export function widgetCaptcha(el) {
  if (!captchaActivo()) return { token: async () => undefined, reiniciar() {} };
  let id = null, actual = null, esperando = [];
  const avisar = (t, err) => { for (const w of esperando) err ? w.rej(err) : w.res(t); esperando = []; };
  const listo = cargar().then((ts) => {
    id = ts.render(el, {
      sitekey: CAPTCHA.siteKey, language: "es", appearance: "interaction-only",
      callback: (t) => { actual = t; avisar(t); },
      "expired-callback": () => { actual = null; },
      "error-callback": () => { actual = null; avisar(null, new Error("La verificación anti-robots falló. Probá de nuevo.")); },
    });
  });
  return {
    async token() {
      await listo;
      if (actual) return actual;
      return new Promise((res, rej) => {
        esperando.push({ res, rej });
        setTimeout(() => avisar(null, new Error("La verificación anti-robots tardó demasiado. Probá de nuevo.")), 30000);
      });
    },
    reiniciar() { actual = null; if (id !== null && window.turnstile) window.turnstile.reset(id); },
  };
}
