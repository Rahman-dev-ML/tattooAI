-- Run in Supabase SQL editor.
-- Table for moderated healing-journey submissions.

create extension if not exists pgcrypto;

create table if not exists public.healing_stories (
  id uuid primary key default gen_random_uuid(),
  display_name text,
  age int check (age is null or (age >= 13 and age <= 120)),
  scar_type text,
  strategy text check (strategy in ('Camouflage', 'Transform', 'Overshadow')),
  quote text not null check (char_length(quote) <= 160),
  story text not null check (char_length(story) <= 1200),
  consent boolean not null default false,
  is_anonymous boolean not null default false,
  photo_url text,
  status text not null default 'pending' check (status in ('pending', 'published', 'rejected')),
  created_at timestamptz not null default now(),
  published_at timestamptz
);

create index if not exists healing_stories_status_idx on public.healing_stories(status, published_at desc, created_at desc);

alter table public.healing_stories enable row level security;

-- Public can read only published stories.
drop policy if exists "Read published healing stories" on public.healing_stories;
create policy "Read published healing stories"
  on public.healing_stories
  for select
  using (status = 'published');

-- Submission insert is intended from server API route (service role key).
-- If you prefer direct browser insert with anon key, add another insert policy.

-- Optional storage bucket for story photos.
insert into storage.buckets (id, name, public)
values ('healing-journeys', 'healing-journeys', true)
on conflict (id) do nothing;

-- Public can read bucket files.
drop policy if exists "Public read healing journey photos" on storage.objects;
create policy "Public read healing journey photos"
  on storage.objects
  for select
  using (bucket_id = 'healing-journeys');

-- Uploads intended via server route (service role bypasses RLS).

