-- © 2026 Eden3D — Yoel Almirón. Todos los derechos reservados. Ver LICENSE.
-- Cuentas y roles de las herramientas de TecnoBear (Supabase).
-- Pegar entero en Supabase → SQL Editor → Run. Se puede correr más de una vez.

-- perfil de cada cuenta con su rol: usuario (gratis) · pro (paquete extra) · admin
create table if not exists public.perfiles (
  id uuid primary key references auth.users (id) on delete cascade,
  email text not null,
  rol text not null default 'usuario' check (rol in ('usuario', 'pro', 'admin')),
  creado timestamptz not null default now()
);

alter table public.perfiles enable row level security;

-- ¿la cuenta que hace la consulta es admin? (security definer: no se mete en bucle con RLS)
create or replace function public.es_admin()
returns boolean language sql stable security definer set search_path = public as $$
  select exists (select 1 from public.perfiles where id = auth.uid() and rol = 'admin');
$$;

-- cada uno ve su perfil; el admin ve todos
drop policy if exists "ver perfiles" on public.perfiles;
create policy "ver perfiles" on public.perfiles
  for select using (auth.uid() = id or public.es_admin());

-- sólo el admin cambia roles (nadie se puede hacer Pro solo)
drop policy if exists "admin cambia roles" on public.perfiles;
create policy "admin cambia roles" on public.perfiles
  for update using (public.es_admin()) with check (public.es_admin());

-- un admin no se puede sacar el rol a sí mismo (para no quedar sin administradores)
create or replace function public.proteger_admin()
returns trigger language plpgsql as $$
begin
  if old.id = auth.uid() and old.rol = 'admin' and new.rol <> 'admin' then
    raise exception 'No podés quitarte el rol de administrador';
  end if;
  return new;
end $$;
drop trigger if exists proteger_admin on public.perfiles;
create trigger proteger_admin before update on public.perfiles
  for each row execute function public.proteger_admin();

-- cada cuenta nueva arranca como 'usuario'
create or replace function public.nuevo_perfil()
returns trigger language plpgsql security definer set search_path = public as $$
begin
  insert into public.perfiles (id, email) values (new.id, new.email)
  on conflict (id) do nothing;
  return new;
end $$;
drop trigger if exists al_crear_cuenta on auth.users;
create trigger al_crear_cuenta after insert on auth.users
  for each row execute function public.nuevo_perfil();

-- cuentas que ya existían antes de correr este script
insert into public.perfiles (id, email)
  select id, email from auth.users on conflict (id) do nothing;

-- PRIMER ADMIN: después de crear tu cuenta en la web, cambiá el email y corré sólo esto:
-- update public.perfiles set rol = 'admin' where email = 'TU_EMAIL@ejemplo.com';
