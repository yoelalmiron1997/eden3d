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

-- ===========================================================================
-- FEEDBACK DE LA COMUNIDAD (botón "Feedback" de la web)
-- Todos los que tienen cuenta leen el feedback de los demás, dejan el suyo, se suman
-- ("Me sumo") y responden. Cada uno borra lo suyo; el admin marca resuelto y borra todo.
-- ===========================================================================
create table if not exists public.feedback (
  id bigint generated always as identity primary key,
  autor uuid not null default auth.uid() references auth.users (id) on delete cascade,
  nombre text not null check (char_length(nombre) between 1 and 60),
  detalle text not null default '' check (char_length(detalle) <= 90),
  avatar text not null default '' check (char_length(avatar) <= 40000),
  herramienta text not null default 'general'
    check (herramienta in ('general', 'macetas', 'mate', 'sopa', 'topper', 'chapita', 'trofeo')),
  tipo text not null default 'idea' check (tipo in ('idea', 'error', 'comentario')),
  texto text not null check (char_length(texto) between 3 and 1000),
  estado text not null default 'abierto' check (estado in ('abierto', 'resuelto')),
  creado timestamptz not null default now()
);
create index if not exists feedback_creado on public.feedback (creado desc);
-- si la tabla ya existía, la lista de herramientas se actualiza (cada herramienta nueva se suma acá)
alter table public.feedback drop constraint if exists feedback_herramienta_check;
alter table public.feedback add constraint feedback_herramienta_check
  check (herramienta in ('general', 'macetas', 'mate', 'sopa', 'topper', 'chapita', 'trofeo'));
alter table public.feedback enable row level security;

drop policy if exists "feedback: lo leen las cuentas" on public.feedback;
create policy "feedback: lo leen las cuentas" on public.feedback
  for select to authenticated using (true);
drop policy if exists "feedback: cada uno escribe el suyo" on public.feedback;
create policy "feedback: cada uno escribe el suyo" on public.feedback
  for insert to authenticated with check (autor = auth.uid() and estado = 'abierto');
drop policy if exists "feedback: el admin lo marca resuelto" on public.feedback;
create policy "feedback: el admin lo marca resuelto" on public.feedback
  for update to authenticated using (public.es_admin()) with check (public.es_admin());
drop policy if exists "feedback: borra el autor o el admin" on public.feedback;
create policy "feedback: borra el autor o el admin" on public.feedback
  for delete to authenticated using (autor = auth.uid() or public.es_admin());

create table if not exists public.feedback_respuestas (
  id bigint generated always as identity primary key,
  feedback_id bigint not null references public.feedback (id) on delete cascade,
  autor uuid not null default auth.uid() references auth.users (id) on delete cascade,
  nombre text not null check (char_length(nombre) between 1 and 60),
  avatar text not null default '' check (char_length(avatar) <= 40000),
  texto text not null check (char_length(texto) between 1 and 600),
  creado timestamptz not null default now()
);
create index if not exists feedback_respuestas_fb on public.feedback_respuestas (feedback_id);
alter table public.feedback_respuestas enable row level security;

drop policy if exists "respuestas: las leen las cuentas" on public.feedback_respuestas;
create policy "respuestas: las leen las cuentas" on public.feedback_respuestas
  for select to authenticated using (true);
drop policy if exists "respuestas: cada uno escribe la suya" on public.feedback_respuestas;
create policy "respuestas: cada uno escribe la suya" on public.feedback_respuestas
  for insert to authenticated with check (autor = auth.uid());
drop policy if exists "respuestas: borra el autor o el admin" on public.feedback_respuestas;
create policy "respuestas: borra el autor o el admin" on public.feedback_respuestas
  for delete to authenticated using (autor = auth.uid() or public.es_admin());

create table if not exists public.feedback_votos (
  feedback_id bigint not null references public.feedback (id) on delete cascade,
  autor uuid not null default auth.uid() references auth.users (id) on delete cascade,
  creado timestamptz not null default now(),
  primary key (feedback_id, autor)
);
alter table public.feedback_votos enable row level security;

drop policy if exists "votos: los ven las cuentas" on public.feedback_votos;
create policy "votos: los ven las cuentas" on public.feedback_votos
  for select to authenticated using (true);
drop policy if exists "votos: cada uno el suyo" on public.feedback_votos;
create policy "votos: cada uno el suyo" on public.feedback_votos
  for insert to authenticated with check (autor = auth.uid());
drop policy if exists "votos: cada uno saca el suyo" on public.feedback_votos;
create policy "votos: cada uno saca el suyo" on public.feedback_votos
  for delete to authenticated using (autor = auth.uid());
