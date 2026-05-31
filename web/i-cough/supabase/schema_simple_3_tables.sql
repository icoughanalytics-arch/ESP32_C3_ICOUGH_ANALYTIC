-- iCough Analytic simple 3-table schema
-- Run in Supabase SQL Editor.

create extension if not exists "pgcrypto";

create table if not exists public.device (
  id uuid primary key default gen_random_uuid(),
  device_name text,
  device_code text unique,
  created_at timestamptz not null default now()
);

create table if not exists public.cough_record (
  id uuid primary key default gen_random_uuid(),
  device_id uuid references public.device(id) on delete set null,
  spectrum_path text,
  audio_path text,
  pneumonia_score numeric(5,4),
  croup_score numeric(5,4),
  bronchitis_score numeric(5,4),
  normal_score numeric(5,4),
  noti_time timestamptz,
  risk_level text,
  created_at timestamptz not null default now()
);

create table if not exists public.summary_record (
  id uuid primary key default gen_random_uuid(),
  device_id uuid references public.device(id) on delete set null,
  cough_ids uuid[] not null default '{}',
  start_at timestamptz,
  end_at timestamptz,
  checklist jsonb,
  summary_result jsonb,
  risk_level text,
  created_at timestamptz not null default now()
);

create index if not exists cough_record_device_created_idx
  on public.cough_record(device_id, created_at desc);

create index if not exists summary_record_device_created_idx
  on public.summary_record(device_id, created_at desc);
