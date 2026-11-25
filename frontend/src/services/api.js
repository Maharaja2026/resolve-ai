import { getAccessToken } from "@/lib/supabase";

const API_BASE = `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001"}/api/v1`;

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function parseError(response) {
  try {
    const body = await response.json();
    if (typeof body.detail === "string") return body.detail;
    if (Array.isArray(body.detail)) {
      return body.detail.map((d) => d.msg || String(d)).join(", ");
    }
    return body.message || response.statusText || "Request failed";
  } catch {
    return response.statusText || "Request failed";
  }
}

async function request(path, options = {}) {
  const token = await getAccessToken();
  const headers = { ...(options.headers || {}) };

  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const isFormData = options.body instanceof FormData;
  if (!isFormData && options.body !== undefined && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    throw new ApiError(await parseError(response), response.status);
  }

  if (response.status === 204) {
    return null;
  }

  const contentType = response.headers.get("content-type");
  if (contentType?.includes("application/json")) {
    return response.json();
  }

  return response.text();
}

export const api = {
  getHealth: () => request("/health"),

  getLlmStatus: () => request("/system/llm-status"),

  getMe: () => request("/me"),

  getPermissions: () => request("/me/permissions"),

  listOrders: () => request("/orders"),

  getOrder: (orderReference) => request(`/orders/${encodeURIComponent(orderReference)}`),

  getOrderEvents: (orderReference) =>
    request(`/orders/${encodeURIComponent(orderReference)}/events`),

  listConversations: () => request("/conversations"),

  createConversation: (title) =>
    request("/conversations", {
      method: "POST",
      body: JSON.stringify({ title: title || "New support chat" }),
    }),

  getConversation: (id) => request(`/conversations/${id}`),

  deleteConversation: (id) =>
    request(`/conversations/${id}`, { method: "DELETE" }),

  listConversationMessages: (conversationId) =>
    request(`/conversations/${conversationId}/messages`),

  sendConversationMessage: (conversationId, content) =>
    request(`/conversations/${conversationId}/messages`, {
      method: "POST",
      body: JSON.stringify({ content }),
    }),

  listTickets: () => request("/tickets"),

  getTicket: (ticketId) => request(`/tickets/${ticketId}`),

  assignTicket: (ticketId, agentUserId) =>
    request(`/tickets/${ticketId}/assign`, {
      method: "POST",
      body: JSON.stringify({ agent_user_id: agentUserId }),
    }),

  resolveTicket: (ticketId, note = "") =>
    request(`/tickets/${ticketId}/resolve`, {
      method: "POST",
      body: JSON.stringify({ note }),
    }),

  escalateTicket: (ticketId) =>
    request(`/tickets/${ticketId}/escalate`, { method: "POST" }),

  listApprovals: () => request("/approvals"),

  getApproval: (approvalId) => request(`/approvals/${approvalId}`),

  approveRequest: (approvalId, comment = "") =>
    request(`/approvals/${approvalId}/approve`, {
      method: "POST",
      body: JSON.stringify({ comment }),
    }),

  rejectRequest: (approvalId, comment = "") =>
    request(`/approvals/${approvalId}/reject`, {
      method: "POST",
      body: JSON.stringify({ comment }),
    }),

  getAnalyticsOverview: () => request("/analytics/overview"),

  getAgentPerformance: () => request("/analytics/agent-performance"),

  getToolUsage: () => request("/analytics/tool-usage"),

  getApprovalStats: () => request("/analytics/approval-stats"),

  listAgentRuns: ({ limit = 50, status } = {}) => {
    const params = new URLSearchParams();
    if (limit) params.set("limit", String(limit));
    if (status) params.set("status", status);
    const q = params.toString();
    return request(`/agent-runs${q ? `?${q}` : ""}`);
  },

  getAgentRun: (runId) => request(`/agent-runs/${runId}`),

  getAgentRunEvents: (runId) => request(`/agent-runs/${runId}/events`),

  getAgentRunTrace: (runId) => request(`/agent-runs/${runId}/trace`),
};