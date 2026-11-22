-- =====================================================================
-- Cuentas Premium (rol Pro) para regalar o sortear — TecnoBear
-- =====================================================================
-- Pegalo en Supabase → SQL Editor → Run. Crea las cuentas ya confirmadas, con una
-- contraseña al azar cada una, y al final muestra la lista (correo + contraseña) para
-- copiarla. Las contraseñas sólo se ven en ese momento: guardalas antes de cerrar.
--
-- Pro = todo lo premium: descargas, sin la marca, render (foto) y PDF con las
-- consideraciones de impresión. NO es administrador (no ve "Calidad", no modera el
-- feedback ni cambia roles). Si alguna tiene que ser admin, cambiá su rol a mano.
--
-- Se puede correr más de una vez: si un correo ya existe, no lo toca.
-- Para cambiar cuántas son, el prefijo o el dominio, editá las tres líneas de abajo.
-- =====================================================================

create temp table if not exists _premium_nuevas (
  correo text primary key, contrasena text
) on commit preserve rows;
truncate _premium_nuevas;

do $$
declare
  cantidad constant int := 20;                    -- cuántas cuentas
  prefijo  constant text := 'premium';            -- premium01, premium02, …
  dominio  constant text := 'tecnobear.app';      -- @dominio (no hace falta que reciba correo)
  letras   constant text := 'abcdefghjkmnpqrstuvwxyzABCDEFGHJKMNPQRSTUVWXYZ23456789';
  i int;
  correo text;
  clave text;
  uid uuid;
  b bytea;
begin
  for i in 1..cantidad loop
    correo := format('%s%s@%s', prefijo, lpad(i::text, 2, '0'), dominio);
    if exists (select 1 from auth.users where email = correo) then
      continue;
    end if;
    -- contraseña: 12 caracteres sin los que se confunden (0/O, 1/l/I), en grupos de 4
    b := extensions.gen_random_bytes(12);
    clave := '';
    for k in 0..11 loop
      clave := clave || substr(letras, (get_byte(b, k) % length(letras)) + 1, 1);
      if k in (3, 7) then clave := clave || '-'; end if;
    end loop;
    uid := gen_random_uuid();
    insert into auth.users (
      instance_id, id, aud, role, email, encrypted_password, email_confirmed_at,
      raw_app_meta_data, raw_user_meta_data, created_at, updated_at,
      confirmation_token, recovery_token, email_change_token_new, email_change)
    values (
      '00000000-0000-0000-0000-000000000000', uid, 'authenticated', 'authenticated', correo,
      extensions.crypt(clave, extensions.gen_salt('bf')), now(),
      '{"provider": "email", "providers": ["email"]}', '{"premium": "sorteo"}', now(), now(),
      '', '', '', '');
    insert into auth.identities (
      id, user_id, provider_id, identity_data, provider, last_sign_in_at, created_at, updated_at)
    values (
      gen_random_uuid(), uid, uid::text,
      jsonb_build_object('sub', uid::text, 'email', correo, 'email_verified', true),
      'email', now(), now(), now());
    -- el perfil lo crea el disparador al_crear_cuenta (rol usuario): se pasa a Pro
    insert into public.perfiles (id, email, rol) values (uid, correo, 'pro')
      on conflict (id) do update set rol = 'pro';
    insert into _premium_nuevas values (correo, clave);
  end loop;
end $$;

-- la lista para copiar (sólo las que se crearon ahora)
select correo, contrasena from _premium_nuevas order by correo;

-- ---------------------------------------------------------------------
-- Para ver todas las cuentas Pro del sorteo más adelante (sin contraseñas):
--   select email, rol, creado from public.perfiles where email like 'premium%@tecnobear.app' order by email;
-- Para sacarle el Premium a una:
--   update public.perfiles set rol = 'usuario' where email = 'premium07@tecnobear.app';
-- Para borrar una cuenta (no se puede deshacer):
--   delete from auth.users where email = 'premium07@tecnobear.app';
-- ---------------------------------------------------------------------
