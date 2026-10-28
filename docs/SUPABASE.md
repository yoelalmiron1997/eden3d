# Login con Supabase (cuentas y roles)

La web es estática (GitHub Pages), así que las cuentas viven en
[Supabase](https://supabase.com), que tiene plan gratis. Una sola vez:

1. **Crear el proyecto**: supabase.com → *New project* (región São Paulo).
2. **Crear las tablas y reglas**: *SQL Editor* → pegar
   [`supabase/esquema.sql`](../supabase/esquema.sql) → *Run*.
3. **Direcciones permitidas**: *Authentication → URL Configuration*:
   * Site URL: `https://yoelalmiron1997.github.io/eden3d/`
   * Redirect URLs: `https://yoelalmiron1997.github.io/eden3d/**`
4. **Conectar la web**: *Project Settings → API Keys → Legacy* y copiar
   *Project URL* y la clave **anon** (nunca la `service_role`) en
   [`web/config.js`](../web/config.js). (Opcional: en GitHub, *Settings → Secrets and
   variables → Actions → Variables* con `SUPABASE_URL` y `SUPABASE_ANON_KEY`; si
   existen, el build las usa en vez de las de `config.js`.)

> Estado: el proyecto `xjyerniuhecwdgfbteez` ya está creado, con el esquema cargado,
> la Site URL y la Redirect URL configuradas, y la web conectada.
5. **Hacerte admin**: entrá a la web, *Ingresar → Crear cuenta* con tu email,
   confirmá el mail y en el *SQL Editor* corré
   `update public.perfiles set rol = 'admin' where email = 'tu@email';`
   (la última línea del script). Desde ahí los roles se cambian en `admin.html`.

## Roles

| Rol | Qué puede |
|---|---|
| visitante (sin cuenta) | mirar, configurar, foto y guía PDF |
| usuario | además descargar 3MF/STL con la marca **Eden3D** |
| pro (paquete extra) | además cambiar el texto de la marca de agua |
| admin | todo + panel `admin.html`: roles y cobertura de la marca en cada maceta |

Las reglas de la base (RLS) hacen que nadie pueda darse un rol a sí mismo: sólo un
admin cambia roles. Mientras `SUPABASE_URL` no esté configurada la web funciona
como antes, sin cuentas y con descarga libre.

> **Límite a tener en cuenta:** el motor corre en el navegador, así que la regla
> "sólo Pro cambia la marca" la aplica la página. Alguien que sepa programar podría
> saltearla modificando el código en su propio navegador. Para blindarlo del todo,
> las descargas Pro se tendrían que generar en un servidor (por ejemplo, una Edge
> Function de Supabase).
