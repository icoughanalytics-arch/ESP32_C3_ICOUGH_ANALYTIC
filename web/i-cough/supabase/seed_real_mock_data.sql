-- Real-ish mock data generated from processed bronchitis train segments.
-- Run after schema_simple_3_tables.sql.

insert into public.device (id, device_name, device_code)
values (
  '22222222-2222-2222-2222-222222222222',
  'iCough Real Mock Device',
  'ICOUGH-REAL-MOCK-001'
)
on conflict (id) do update set
  device_name = excluded.device_name,
  device_code = excluded.device_code;

delete from public.summary_record
where device_id = '22222222-2222-2222-2222-222222222222';

delete from public.cough_record
where device_id = '22222222-2222-2222-2222-222222222222';

insert into public.cough_record (
  id,
  device_id,
  spectrum_path,
  audio_path,
  pneumonia_score,
  croup_score,
  bronchitis_score,
  normal_score,
  noti_time,
  risk_level,
  created_at
)
values
  (
    'bbbbbbbb-0000-0000-0000-000000000001',
    '22222222-2222-2222-2222-222222222222',
    'https://tvbtogovalfhudduqssi.supabase.co/storage/v1/object/public/cough-spectrum/spectrogram-01.png',
    'https://tvbtogovalfhudduqssi.supabase.co/storage/v1/object/public/cough-audio/audio-01.wav',
    0.1800,
    0.0600,
    0.6800,
    0.0800,
    null,
    'moderate',
    now() - interval '11 hours 0 minutes'
  ),
  (
    'bbbbbbbb-0000-0000-0000-000000000002',
    '22222222-2222-2222-2222-222222222222',
    'https://tvbtogovalfhudduqssi.supabase.co/storage/v1/object/public/cough-spectrum/spectrogram-02.png',
    'https://tvbtogovalfhudduqssi.supabase.co/storage/v1/object/public/cough-audio/audio-02.wav',
    0.1200,
    0.0500,
    0.7400,
    0.0900,
    null,
    'moderate',
    now() - interval '10 hours 7 minutes'
  ),
  (
    'bbbbbbbb-0000-0000-0000-000000000003',
    '22222222-2222-2222-2222-222222222222',
    'https://tvbtogovalfhudduqssi.supabase.co/storage/v1/object/public/cough-spectrum/spectrogram-03.png',
    'https://tvbtogovalfhudduqssi.supabase.co/storage/v1/object/public/cough-audio/audio-03.wav',
    0.0900,
    0.0300,
    0.8300,
    0.0500,
    now() - interval '9 hours 14 minutes',
    'high',
    now() - interval '9 hours 14 minutes'
  ),
  (
    'bbbbbbbb-0000-0000-0000-000000000004',
    '22222222-2222-2222-2222-222222222222',
    'https://tvbtogovalfhudduqssi.supabase.co/storage/v1/object/public/cough-spectrum/spectrogram-04.png',
    'https://tvbtogovalfhudduqssi.supabase.co/storage/v1/object/public/cough-audio/audio-04.wav',
    0.2100,
    0.1000,
    0.5700,
    0.1200,
    null,
    'moderate',
    now() - interval '8 hours 21 minutes'
  ),
  (
    'bbbbbbbb-0000-0000-0000-000000000005',
    '22222222-2222-2222-2222-222222222222',
    'https://tvbtogovalfhudduqssi.supabase.co/storage/v1/object/public/cough-spectrum/spectrogram-05.png',
    'https://tvbtogovalfhudduqssi.supabase.co/storage/v1/object/public/cough-audio/audio-05.wav',
    0.0800,
    0.0400,
    0.4600,
    0.4200,
    null,
    'low',
    now() - interval '7 hours 28 minutes'
  ),
  (
    'bbbbbbbb-0000-0000-0000-000000000006',
    '22222222-2222-2222-2222-222222222222',
    'https://tvbtogovalfhudduqssi.supabase.co/storage/v1/object/public/cough-spectrum/spectrogram-06.png',
    'https://tvbtogovalfhudduqssi.supabase.co/storage/v1/object/public/cough-audio/audio-06.wav',
    0.1400,
    0.0800,
    0.6600,
    0.1200,
    null,
    'moderate',
    now() - interval '6 hours 35 minutes'
  ),
  (
    'bbbbbbbb-0000-0000-0000-000000000007',
    '22222222-2222-2222-2222-222222222222',
    'https://tvbtogovalfhudduqssi.supabase.co/storage/v1/object/public/cough-spectrum/spectrogram-07.png',
    'https://tvbtogovalfhudduqssi.supabase.co/storage/v1/object/public/cough-audio/audio-07.wav',
    0.1100,
    0.0500,
    0.7900,
    0.0500,
    now() - interval '5 hours 42 minutes',
    'high',
    now() - interval '5 hours 42 minutes'
  ),
  (
    'bbbbbbbb-0000-0000-0000-000000000008',
    '22222222-2222-2222-2222-222222222222',
    'https://tvbtogovalfhudduqssi.supabase.co/storage/v1/object/public/cough-spectrum/spectrogram-08.png',
    'https://tvbtogovalfhudduqssi.supabase.co/storage/v1/object/public/cough-audio/audio-08.wav',
    0.1900,
    0.0700,
    0.6100,
    0.1300,
    null,
    'moderate',
    now() - interval '4 hours 49 minutes'
  ),
  (
    'bbbbbbbb-0000-0000-0000-000000000009',
    '22222222-2222-2222-2222-222222222222',
    'https://tvbtogovalfhudduqssi.supabase.co/storage/v1/object/public/cough-spectrum/spectrogram-09.png',
    'https://tvbtogovalfhudduqssi.supabase.co/storage/v1/object/public/cough-audio/audio-09.wav',
    0.1000,
    0.0400,
    0.5200,
    0.3400,
    null,
    'low',
    now() - interval '3 hours 56 minutes'
  ),
  (
    'bbbbbbbb-0000-0000-0000-000000000010',
    '22222222-2222-2222-2222-222222222222',
    'https://tvbtogovalfhudduqssi.supabase.co/storage/v1/object/public/cough-spectrum/spectrogram-10.png',
    'https://tvbtogovalfhudduqssi.supabase.co/storage/v1/object/public/cough-audio/audio-10.wav',
    0.1600,
    0.0600,
    0.7000,
    0.0800,
    null,
    'moderate',
    now() - interval '2 hours 3 minutes'
  );
