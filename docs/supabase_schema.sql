
-- 1. Auth Table
create table if not exists public.users (
    id bigint generated always as identity primary key,
    email text not null unique,
    hashed_password text not null,
    created_at timestamptz not null default now()
);

-- 2. The dataset itself

create table if not exists public.purchases (
    id bigint generated always as identity primary key,
    customer_id text,
    product text,
    purchase_date date,
    quantity integer,
    unit_price numeric(10, 2),
    customer_name text,
    product_category text,
    payment_method text,
    review_rating integer,
    total_price numeric(10, 2)
);

-- 3. Chat/research history 
create table if not exists public.analysis_runs (
    id bigint generated always as identity primary key,
    run_id text not null,
    conversation_id text not null,
    turn_number integer not null default 1,
    mode text not null,
    question text not null,
    answer text not null,
    queries_used text not null default '[]',
    key_findings text not null default '[]',
    charts_meta text not null default '[]',
    citations text not null default '[]',
    status text not null,
    errors text not null default '[]',
    user_id bigint references public.users (id),
    created_at timestamptz not null default now()
);
create index if not exists idx_analysis_runs_conversation_id on public.analysis_runs (conversation_id);
create index if not exists idx_analysis_runs_user_id on public.analysis_runs (user_id);
