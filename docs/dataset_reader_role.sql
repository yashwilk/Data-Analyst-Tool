-- Least-privilege role for the LLM-generated dataset queries.

create role dataset_reader login password '<strong-password>';

-- Belt and braces: every transaction is read-only, and runaway queries
-- are killed instead of tying up the pooler.
alter role dataset_reader set default_transaction_read_only = on;
alter role dataset_reader set statement_timeout = '10s';

grant usage on schema public to dataset_reader;
grant select on public.purchases to dataset_reader;

-- RLS is enabled on every table and this role
-- doesn't bypass it, so it needs an explicit read policy on `purchases`.
create policy "dataset_reader can read purchases"
    on public.purchases for select to dataset_reader using (true);
