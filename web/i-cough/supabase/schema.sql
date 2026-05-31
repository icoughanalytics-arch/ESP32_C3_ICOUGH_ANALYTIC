-- iCough Analytic MVP schema
-- Run this in Supabase Dashboard > SQL Editor.

create extension if not exists "pgcrypto";

create table if not exists public.devices (
  id uuid primary key default gen_random_uuid(),
  device_code text not null unique,
  name text,
  parent_line_id text,
  note text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.cough_records (
  id uuid primary key default gen_random_uuid(),
  device_id uuid references public.devices(id) on delete set null,

  -- Use this in the Line URL instead of exposing only the record id.
  public_token uuid not null unique default gen_random_uuid(),

  audio_path text,
  audio_url text,
  spectrogram_path text,
  spectrogram_url text,

  ai_class text not null check (
    ai_class in ('healthy', 'pneumonia', 'bronchitis', 'croup', 'unknown')
  ),
  confidence numeric(5,4) check (confidence is null or (confidence >= 0 and confidence <= 1)),
  ai_scores jsonb,

  risk_level text check (
    risk_level is null or risk_level in ('low', 'moderate', 'high')
  ),

  checklist_fast_breathing boolean,
  checklist_chest_retraction boolean,
  checklist_stridor boolean,
  checklist_danger_sign boolean,
  final_risk_level text check (
    final_risk_level is null or final_risk_level in ('low', 'moderate', 'high')
  ),
  checklist_submitted_at timestamptz,

  line_notified_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists devices_device_code_idx
  on public.devices(device_code);

create index if not exists cough_records_device_id_created_at_idx
  on public.cough_records(device_id, created_at desc);

create index if not exists cough_records_public_token_idx
  on public.cough_records(public_token);

create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists set_devices_updated_at on public.devices;
create trigger set_devices_updated_at
before update on public.devices
for each row execute function public.set_updated_at();

drop trigger if exists set_cough_records_updated_at on public.cough_records;
create trigger set_cough_records_updated_at
before update on public.cough_records
for each row execute function public.set_updated_at();

-- MVP note:
-- Keep RLS disabled while testing with FastAPI + Next.js.
-- Before real use, enable RLS and switch server writes to a service role key.
