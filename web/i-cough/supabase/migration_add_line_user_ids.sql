-- =============================================================
-- iCough: เพิ่มระบบ LINE User ID Registration
-- รันใน Supabase Dashboard > SQL Editor
-- =============================================================

-- 1. เพิ่มคอลัมน์ line_user_ids
ALTER TABLE public.device
ADD COLUMN IF NOT EXISTS line_user_ids text[] DEFAULT '{}';

-- 2. RPC: เพิ่ม LINE user ID (ป้องกันซ้ำ)
CREATE OR REPLACE FUNCTION public.add_line_user_id(
    p_device_code text,
    p_line_user_id text
)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
AS $body$
BEGIN
    UPDATE public.device
    SET line_user_ids = array_append(
        COALESCE(line_user_ids, ARRAY[]::text[]),
        p_line_user_id
    )
    WHERE device_code = p_device_code
      AND NOT (p_line_user_id = ANY(COALESCE(line_user_ids, ARRAY[]::text[])));
END;
$body$;

-- 3. RPC: ลบ LINE user ID
CREATE OR REPLACE FUNCTION public.remove_line_user_id(
    p_device_code text,
    p_line_user_id text
)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
AS $body$
BEGIN
    UPDATE public.device
    SET line_user_ids = array_remove(
        COALESCE(line_user_ids, ARRAY[]::text[]),
        p_line_user_id
    )
    WHERE device_code = p_device_code;
END;
$body$;
