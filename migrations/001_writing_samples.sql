-- Migration: Writing Samples table for Content Creator Bot
-- Run this in Supabase SQL Editor:
-- https://supabase.com/dashboard/project/arwnfufcddhigamlwmyw/sql/new

CREATE TABLE IF NOT EXISTS public.writing_samples (
  id         BIGSERIAL PRIMARY KEY,
  content    TEXT NOT NULL,
  platform   TEXT DEFAULT 'threads',  -- threads, tiktok, instagram, caption, post, custom
  source     TEXT,                     -- URL or "telegram-screenshot"
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable RLS (keeps it secure)
ALTER TABLE public.writing_samples ENABLE ROW LEVEL SECURITY;

-- Policy: allow anon key to read/write (bot uses anon key)
CREATE POLICY "Allow anon full access" 
  ON public.writing_samples
  FOR ALL 
  USING (true)
  WITH CHECK (true);
