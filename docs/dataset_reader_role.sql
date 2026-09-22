-- Least-privilege role for the LLM-generated dataset queries.
-- Run once in Supabase's SQL Editor after supabase_schema.sql, replacing
-- <strong-password>, then set DATASET_DATABASE_URL in .env to the Session
-- pooler string with user `dataset_reader.<project-ref>` and that password.
--
-- `_ensure_read_only` in the app is the first layer; this is the one the
-- database enforces. The role can SELECT from `purchases` and nothing else
-- -- `users` (password hashes) and `analysis_runs` are off limits even if
-- a prompt-injected query gets past the regex.

create role dataset_reader login password '<strong-password>';

-- Belt and braces: every transaction is read-only, and runaway queries
-- are killed instead of tying up the pooler.
alter role dataset_reader set default_transaction_read_only = on;
alter role dataset_reader set statement_timeout = '10s';

grant usage on schema public to dataset_reader;
grant select on public.purchases to dataset_reader;

-- RLS is enabled on every table (see supabase_schema.sql), and this role
-- doesn't bypass it, so it needs an explicit read policy on `purchases`.
create policy "dataset_reader can read purchases"
    on public.purchases for select to dataset_reader using (true);
