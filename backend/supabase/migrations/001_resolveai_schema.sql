-- ResolveAI schema — independent from KnowledgePilot tables
-- Uses resolveai_ prefix. Do not modify KnowledgePilot objects.

CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "vector";

-- ---------------------------------------------------------------------------
-- user profiles / customers
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.resolveai_user_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL UNIQUE REFERENCES auth.users(id) ON DELETE CASCADE,
    full_name TEXT NOT NULL DEFAULT 'Customer',
    role TEXT NOT NULL DEFAULT 'customer'
        CHECK (role IN ('customer', 'support_agent', 'admin')),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.resolveai_customers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID UNIQUE REFERENCES auth.users(id) ON DELETE SET NULL,
    customer_reference TEXT NOT NULL UNIQUE,
    full_name TEXT NOT NULL,
    email TEXT NOT NULL,
    phone TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_resolveai_customers_user ON public.resolveai_customers(user_id);
CREATE INDEX IF NOT EXISTS idx_resolveai_customers_email ON public.resolveai_customers(email);

-- ---------------------------------------------------------------------------
-- orders / events
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.resolveai_orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_reference TEXT NOT NULL UNIQUE,
    customer_id UUID NOT NULL REFERENCES public.resolveai_customers(id) ON DELETE CASCADE,
    order_status TEXT NOT NULL DEFAULT 'pending'
        CHECK (order_status IN (
            'pending','confirmed','processing','shipped','out_for_delivery',
            'delivered','cancelled','return_requested','returned'
        )),
    payment_status TEXT NOT NULL DEFAULT 'paid'
        CHECK (payment_status IN ('pending','paid','refunded','partially_refunded','failed')),
    total_amount NUMERIC(12,2) NOT NULL CHECK (total_amount >= 0),
    currency TEXT NOT NULL DEFAULT 'USD',
    shipping_address JSONB NOT NULL DEFAULT '{}'::jsonb,
    tracking_reference TEXT,
    product_summary TEXT NOT NULL DEFAULT '',
    ordered_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expected_delivery_at TIMESTAMPTZ,
    delivered_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_resolveai_orders_customer ON public.resolveai_orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_resolveai_orders_status ON public.resolveai_orders(order_status);

CREATE TABLE IF NOT EXISTS public.resolveai_order_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id UUID NOT NULL REFERENCES public.resolveai_orders(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL,
    description TEXT NOT NULL,
    location TEXT,
    event_timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_resolveai_order_events_order ON public.resolveai_order_events(order_id, event_timestamp);

-- ---------------------------------------------------------------------------
-- policies / chunks
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.resolveai_policy_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    category TEXT NOT NULL,
    content TEXT NOT NULL,
    version TEXT NOT NULL DEFAULT '1.0',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (title, version)
);

CREATE TABLE IF NOT EXISTS public.resolveai_policy_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES public.resolveai_policy_documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL CHECK (chunk_index >= 0),
    content TEXT NOT NULL,
    embedding vector(384),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    content_tsv tsvector GENERATED ALWAYS AS (to_tsvector('english', coalesce(content, ''))) STORED,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (document_id, chunk_index)
);

CREATE INDEX IF NOT EXISTS idx_resolveai_policy_chunks_doc ON public.resolveai_policy_chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_resolveai_policy_chunks_tsv ON public.resolveai_policy_chunks USING GIN (content_tsv);
CREATE INDEX IF NOT EXISTS idx_resolveai_policy_chunks_embedding
    ON public.resolveai_policy_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 50);

-- ---------------------------------------------------------------------------
-- conversations / messages / tickets
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.resolveai_conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    customer_id UUID REFERENCES public.resolveai_customers(id) ON DELETE SET NULL,
    title TEXT NOT NULL DEFAULT 'New support chat',
    status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open','waiting','resolved','closed')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_resolveai_conversations_user ON public.resolveai_conversations(user_id, updated_at DESC);

CREATE TABLE IF NOT EXISTS public.resolveai_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES public.resolveai_conversations(id) ON DELETE CASCADE,
    user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    role TEXT NOT NULL CHECK (role IN ('user','assistant','system')),
    content TEXT NOT NULL,
    message_type TEXT NOT NULL DEFAULT 'text',
    agent_run_id UUID,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_resolveai_messages_conv ON public.resolveai_messages(conversation_id, created_at);

CREATE TABLE IF NOT EXISTS public.resolveai_support_tickets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticket_reference TEXT NOT NULL UNIQUE,
    customer_id UUID NOT NULL REFERENCES public.resolveai_customers(id) ON DELETE CASCADE,
    order_id UUID REFERENCES public.resolveai_orders(id) ON DELETE SET NULL,
    conversation_id UUID REFERENCES public.resolveai_conversations(id) ON DELETE SET NULL,
    category TEXT NOT NULL DEFAULT 'general',
    priority TEXT NOT NULL DEFAULT 'medium' CHECK (priority IN ('low','medium','high','urgent')),
    sentiment TEXT,
    status TEXT NOT NULL DEFAULT 'open'
        CHECK (status IN ('open','in_progress','waiting_for_approval','escalated','resolved','closed')),
    assigned_agent_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    subject TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_resolveai_tickets_status ON public.resolveai_support_tickets(status, priority);

-- ---------------------------------------------------------------------------
-- agent runs / events / tools
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.resolveai_agent_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES public.resolveai_conversations(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    input_message TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'queued'
        CHECK (status IN ('queued','running','waiting_for_approval','completed','failed','cancelled')),
    intent TEXT,
    selected_provider TEXT,
    selected_model TEXT,
    total_steps INTEGER NOT NULL DEFAULT 0,
    total_tool_calls INTEGER NOT NULL DEFAULT 0,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    error_message TEXT,
    final_response TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_resolveai_agent_runs_conv ON public.resolveai_agent_runs(conversation_id, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_resolveai_agent_runs_status ON public.resolveai_agent_runs(status);

ALTER TABLE public.resolveai_messages
    DROP CONSTRAINT IF EXISTS resolveai_messages_agent_run_id_fkey;
ALTER TABLE public.resolveai_messages
    ADD CONSTRAINT resolveai_messages_agent_run_id_fkey
    FOREIGN KEY (agent_run_id) REFERENCES public.resolveai_agent_runs(id) ON DELETE SET NULL;

CREATE TABLE IF NOT EXISTS public.resolveai_agent_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_run_id UUID NOT NULL REFERENCES public.resolveai_agent_runs(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL,
    event_name TEXT NOT NULL,
    summary TEXT NOT NULL,
    safe_input JSONB NOT NULL DEFAULT '{}'::jsonb,
    safe_output JSONB NOT NULL DEFAULT '{}'::jsonb,
    status TEXT NOT NULL DEFAULT 'completed',
    sequence_number INTEGER NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_resolveai_agent_events_run ON public.resolveai_agent_events(agent_run_id, sequence_number);

CREATE TABLE IF NOT EXISTS public.resolveai_tool_executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_run_id UUID NOT NULL REFERENCES public.resolveai_agent_runs(id) ON DELETE CASCADE,
    conversation_id UUID REFERENCES public.resolveai_conversations(id) ON DELETE SET NULL,
    tool_name TEXT NOT NULL,
    tool_arguments JSONB NOT NULL DEFAULT '{}'::jsonb,
    execution_result JSONB NOT NULL DEFAULT '{}'::jsonb,
    status TEXT NOT NULL DEFAULT 'completed',
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    idempotency_key TEXT,
    UNIQUE (idempotency_key)
);

CREATE INDEX IF NOT EXISTS idx_resolveai_tool_exec_run ON public.resolveai_tool_executions(agent_run_id);

-- ---------------------------------------------------------------------------
-- approvals / refunds / audit
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.resolveai_approval_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_run_id UUID REFERENCES public.resolveai_agent_runs(id) ON DELETE SET NULL,
    customer_id UUID NOT NULL REFERENCES public.resolveai_customers(id) ON DELETE CASCADE,
    order_id UUID REFERENCES public.resolveai_orders(id) ON DELETE SET NULL,
    requested_by UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    approval_type TEXT NOT NULL,
    requested_action TEXT NOT NULL,
    action_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    reason TEXT,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending','approved','rejected','expired','cancelled')),
    reviewed_by UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    review_comment TEXT,
    approved_at TIMESTAMPTZ,
    rejected_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_resolveai_approvals_status ON public.resolveai_approval_requests(status, created_at DESC);

CREATE TABLE IF NOT EXISTS public.resolveai_refund_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id UUID NOT NULL REFERENCES public.resolveai_orders(id) ON DELETE CASCADE,
    customer_id UUID NOT NULL REFERENCES public.resolveai_customers(id) ON DELETE CASCADE,
    approval_request_id UUID REFERENCES public.resolveai_approval_requests(id) ON DELETE SET NULL,
    amount NUMERIC(12,2) NOT NULL CHECK (amount >= 0),
    currency TEXT NOT NULL DEFAULT 'USD',
    refund_reason TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'simulated_completed'
        CHECK (status IN ('pending','simulated_completed','failed','cancelled')),
    simulated_transaction_reference TEXT NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.resolveai_audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    actor_user_id UUID,
    actor_role TEXT,
    action TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT,
    old_values JSONB NOT NULL DEFAULT '{}'::jsonb,
    new_values JSONB NOT NULL DEFAULT '{}'::jsonb,
    agent_run_id UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_resolveai_audit_created ON public.resolveai_audit_logs(created_at DESC);

-- updated_at helper
CREATE OR REPLACE FUNCTION public.resolveai_set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_resolveai_profiles_updated ON public.resolveai_user_profiles;
CREATE TRIGGER trg_resolveai_profiles_updated
    BEFORE UPDATE ON public.resolveai_user_profiles
    FOR EACH ROW EXECUTE FUNCTION public.resolveai_set_updated_at();

DROP TRIGGER IF EXISTS trg_resolveai_orders_updated ON public.resolveai_orders;
CREATE TRIGGER trg_resolveai_orders_updated
    BEFORE UPDATE ON public.resolveai_orders
    FOR EACH ROW EXECUTE FUNCTION public.resolveai_set_updated_at();

DROP TRIGGER IF EXISTS trg_resolveai_conversations_updated ON public.resolveai_conversations;
CREATE TRIGGER trg_resolveai_conversations_updated
    BEFORE UPDATE ON public.resolveai_conversations
    FOR EACH ROW EXECUTE FUNCTION public.resolveai_set_updated_at();

DROP TRIGGER IF EXISTS trg_resolveai_tickets_updated ON public.resolveai_support_tickets;
CREATE TRIGGER trg_resolveai_tickets_updated
    BEFORE UPDATE ON public.resolveai_support_tickets
    FOR EACH ROW EXECUTE FUNCTION public.resolveai_set_updated_at();

DROP TRIGGER IF EXISTS trg_resolveai_approvals_updated ON public.resolveai_approval_requests;
CREATE TRIGGER trg_resolveai_approvals_updated
    BEFORE UPDATE ON public.resolveai_approval_requests
    FOR EACH ROW EXECUTE FUNCTION public.resolveai_set_updated_at();
