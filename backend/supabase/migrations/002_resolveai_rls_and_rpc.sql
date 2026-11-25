-- ResolveAI RLS and policy retrieval RPCs

ALTER TABLE public.resolveai_user_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.resolveai_customers ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.resolveai_orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.resolveai_order_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.resolveai_policy_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.resolveai_policy_chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.resolveai_conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.resolveai_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.resolveai_support_tickets ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.resolveai_agent_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.resolveai_agent_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.resolveai_tool_executions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.resolveai_approval_requests ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.resolveai_refund_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.resolveai_audit_logs ENABLE ROW LEVEL SECURITY;

-- Profiles: users see own; staff see all via service role primarily
DROP POLICY IF EXISTS resolveai_profiles_select_own ON public.resolveai_user_profiles;
CREATE POLICY resolveai_profiles_select_own ON public.resolveai_user_profiles
    FOR SELECT USING (auth.uid() = user_id);

DROP POLICY IF EXISTS resolveai_profiles_update_own_name ON public.resolveai_user_profiles;
CREATE POLICY resolveai_profiles_update_own_name ON public.resolveai_user_profiles
    FOR UPDATE USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id AND role = (SELECT role FROM public.resolveai_user_profiles p WHERE p.user_id = auth.uid()));

-- Customers / orders ownership
DROP POLICY IF EXISTS resolveai_customers_select_own ON public.resolveai_customers;
CREATE POLICY resolveai_customers_select_own ON public.resolveai_customers
    FOR SELECT USING (auth.uid() = user_id);

DROP POLICY IF EXISTS resolveai_orders_select_own ON public.resolveai_orders;
CREATE POLICY resolveai_orders_select_own ON public.resolveai_orders
    FOR SELECT USING (
        customer_id IN (SELECT id FROM public.resolveai_customers WHERE user_id = auth.uid())
    );

DROP POLICY IF EXISTS resolveai_order_events_select_own ON public.resolveai_order_events;
CREATE POLICY resolveai_order_events_select_own ON public.resolveai_order_events
    FOR SELECT USING (
        order_id IN (
            SELECT o.id FROM public.resolveai_orders o
            JOIN public.resolveai_customers c ON c.id = o.customer_id
            WHERE c.user_id = auth.uid()
        )
    );

-- Conversations / messages
DROP POLICY IF EXISTS resolveai_conversations_own ON public.resolveai_conversations;
CREATE POLICY resolveai_conversations_own ON public.resolveai_conversations
    FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS resolveai_messages_own ON public.resolveai_messages;
CREATE POLICY resolveai_messages_own ON public.resolveai_messages
    FOR SELECT USING (
        conversation_id IN (SELECT id FROM public.resolveai_conversations WHERE user_id = auth.uid())
    );

-- Policies readable by authenticated users
DROP POLICY IF EXISTS resolveai_policies_read ON public.resolveai_policy_documents;
CREATE POLICY resolveai_policies_read ON public.resolveai_policy_documents
    FOR SELECT USING (auth.role() = 'authenticated' AND is_active = TRUE);

DROP POLICY IF EXISTS resolveai_policy_chunks_read ON public.resolveai_policy_chunks;
CREATE POLICY resolveai_policy_chunks_read ON public.resolveai_policy_chunks
    FOR SELECT USING (auth.role() = 'authenticated');

-- Semantic policy search
CREATE OR REPLACE FUNCTION public.resolveai_match_policy_chunks(
    p_query_embedding vector(384),
    p_match_count INTEGER DEFAULT 10,
    p_category TEXT DEFAULT NULL
)
RETURNS TABLE (
    id UUID,
    document_id UUID,
    chunk_index INTEGER,
    content TEXT,
    metadata JSONB,
    similarity FLOAT,
    document_title TEXT,
    category TEXT
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    RETURN QUERY
    SELECT
        c.id,
        c.document_id,
        c.chunk_index,
        c.content,
        c.metadata,
        (1 - (c.embedding <=> p_query_embedding))::FLOAT AS similarity,
        d.title AS document_title,
        d.category
    FROM public.resolveai_policy_chunks c
    INNER JOIN public.resolveai_policy_documents d ON d.id = c.document_id
    WHERE d.is_active = TRUE
      AND c.embedding IS NOT NULL
      AND (p_category IS NULL OR d.category = p_category)
    ORDER BY c.embedding <=> p_query_embedding
    LIMIT GREATEST(p_match_count, 1);
END;
$$;

CREATE OR REPLACE FUNCTION public.resolveai_keyword_policy_chunks(
    p_query TEXT,
    p_match_count INTEGER DEFAULT 10,
    p_category TEXT DEFAULT NULL
)
RETURNS TABLE (
    id UUID,
    document_id UUID,
    chunk_index INTEGER,
    content TEXT,
    metadata JSONB,
    rank FLOAT,
    document_title TEXT,
    category TEXT
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    tsq tsquery;
BEGIN
    tsq := plainto_tsquery('english', coalesce(p_query, ''));
    RETURN QUERY
    SELECT
        c.id,
        c.document_id,
        c.chunk_index,
        c.content,
        c.metadata,
        ts_rank_cd(c.content_tsv, tsq)::FLOAT AS rank,
        d.title AS document_title,
        d.category
    FROM public.resolveai_policy_chunks c
    INNER JOIN public.resolveai_policy_documents d ON d.id = c.document_id
    WHERE d.is_active = TRUE
      AND (p_category IS NULL OR d.category = p_category)
      AND c.content_tsv @@ tsq
    ORDER BY rank DESC
    LIMIT GREATEST(p_match_count, 1);
END;
$$;
