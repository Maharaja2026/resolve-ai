"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Bot, Plus, Send, User } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { toast } from "sonner";
import { api } from "@/services/api";
import Button from "@/components/shared/Button";
import { Card, CardBody } from "@/components/shared/Card";
import Skeleton from "@/components/shared/Skeleton";
import EmptyState from "@/components/shared/EmptyState";
import { cn, formatDate } from "@/lib/utils";

export default function ChatWorkspace() {
  const [conversations, setConversations] = useState([]);
  const [activeId, setActiveId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [draft, setDraft] = useState("");
  const [loadingList, setLoadingList] = useState(true);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [sending, setSending] = useState(false);
  const bottomRef = useRef(null);

  const loadConversations = useCallback(async () => {
    setLoadingList(true);
    try {
      const rows = await api.listConversations();
      setConversations(rows);
      setActiveId((prev) => prev ?? rows[0]?.id ?? null);
    } catch (err) {
      toast.error(err.message || "Could not load conversations");
    } finally {
      setLoadingList(false);
    }
  }, []);

  const loadMessages = useCallback(async (conversationId) => {
    if (!conversationId) return;
    setLoadingMessages(true);
    try {
      const rows = await api.listConversationMessages(conversationId);
      setMessages(rows);
    } catch (err) {
      toast.error(err.message || "Could not load messages");
      setMessages([]);
    } finally {
      setLoadingMessages(false);
    }
  }, []);

  useEffect(() => {
    loadConversations();
  }, [loadConversations]);

  useEffect(() => {
    loadMessages(activeId);
  }, [activeId, loadMessages]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, sending]);

  const handleCreate = async () => {
    try {
      const created = await api.createConversation("Support request");
      setConversations((prev) => [created, ...prev]);
      setActiveId(created.id);
      setMessages([]);
      toast.success("Conversation started");
    } catch (err) {
      toast.error(err.message || "Could not create conversation");
    }
  };

  const handleSend = async (e) => {
    e.preventDefault();
    if (!activeId || !draft.trim()) return;
    const text = draft.trim();
    setDraft("");
    setSending(true);
    setMessages((prev) => [
      ...prev,
      {
        id: `local-${Date.now()}`,
        role: "user",
        content: text,
        created_at: new Date().toISOString(),
      },
    ]);
    try {
      await api.sendConversationMessage(activeId, text);
      await loadMessages(activeId);
      await loadConversations();
    } catch (err) {
      toast.error(err.message || "Message failed");
      await loadMessages(activeId);
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="grid h-[min(720px,calc(100vh-12rem))] gap-4 lg:grid-cols-[280px_1fr]">
      <Card className="flex min-h-0 flex-col overflow-hidden">
        <div className="flex shrink-0 items-center justify-between border-b border-zinc-100 px-3 py-3">
          <p className="text-sm font-semibold text-zinc-900">Conversations</p>
          <Button variant="ghost" className="h-8 w-8 px-0 py-0" onClick={handleCreate} aria-label="New conversation">
            <Plus className="h-4 w-4" />
          </Button>
        </div>
        <CardBody className="min-h-0 flex-1 space-y-1 overflow-y-auto p-2">
          {loadingList ? <Skeleton className="h-20 w-full" /> : null}
          {!loadingList && conversations.length === 0 ? (
            <EmptyState
              title="No chats yet"
              description="Create a conversation to talk to the ResolveAI agent."
              action={<Button onClick={handleCreate}>New chat</Button>}
            />
          ) : null}
          {conversations.map((c) => (
            <button
              key={c.id}
              type="button"
              onClick={() => setActiveId(c.id)}
              className={cn(
                "block w-full rounded-lg px-3 py-2.5 text-left text-sm transition-colors",
                activeId === c.id
                  ? "bg-teal-50 text-teal-900 ring-1 ring-teal-100"
                  : "text-zinc-700 hover:bg-zinc-100",
              )}
            >
              <span className="line-clamp-2 block font-medium leading-snug">{c.title}</span>
              <span className="mt-1 block text-xs text-zinc-500">{formatDate(c.updated_at)}</span>
            </button>
          ))}
        </CardBody>
      </Card>

      <Card className="flex min-h-0 flex-col overflow-hidden">
        <div className="shrink-0 border-b border-zinc-100 px-4 py-3">
          <p className="text-sm font-semibold text-zinc-900">AI support chat</p>
          <p className="text-xs text-zinc-500">
            Messages invoke the LangGraph agent on the FastAPI backend.
          </p>
        </div>

        <div className="min-h-0 flex-1 space-y-4 overflow-y-auto px-4 py-4">
          {loadingMessages ? <Skeleton className="h-32 w-full" /> : null}
          {!loadingMessages && messages.length === 0 ? (
            <p className="py-16 text-center text-sm text-zinc-500">
              Send a message about an order, return, or cancellation.
            </p>
          ) : null}
          {messages.map((m) => (
            <MessageBubble key={m.id} message={m} />
          ))}
          {sending ? (
            <div className="flex items-start gap-3">
              <Avatar kind="assistant" />
              <div className="rounded-2xl border border-zinc-200 bg-zinc-50 px-4 py-3 text-sm text-zinc-500">
                Thinking…
              </div>
            </div>
          ) : null}
          <div ref={bottomRef} />
        </div>

        <form
          onSubmit={handleSend}
          className="flex shrink-0 items-end gap-2 border-t border-zinc-100 bg-white p-3"
        >
          <textarea
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleSend(e);
              }
            }}
            rows={2}
            placeholder={activeId ? "Describe your issue…" : "Create a conversation first"}
            disabled={!activeId || sending}
            className="max-h-32 min-h-[44px] w-full resize-y rounded-xl border border-zinc-300 bg-white px-3 py-2.5 text-sm text-zinc-900 shadow-sm placeholder:text-zinc-400 focus:border-teal-500 focus:outline-none focus:ring-2 focus:ring-teal-500/20 disabled:bg-zinc-50"
          />
          <Button
            type="submit"
            className="h-11 w-11 shrink-0 px-0"
            disabled={!activeId || sending || !draft.trim()}
            aria-label="Send message"
          >
            <Send className="h-4 w-4" />
          </Button>
        </form>
      </Card>
    </div>
  );
}

function MessageBubble({ message }) {
  const isUser = message.role === "user";
  return (
    <div className={cn("flex w-full items-start gap-3", isUser ? "flex-row-reverse" : "flex-row")}>
      <Avatar kind={isUser ? "user" : "assistant"} />
      <div
        className={cn(
          "min-w-0 max-w-[min(100%,42rem)] rounded-2xl px-4 py-3 text-sm leading-relaxed shadow-sm",
          isUser
            ? "bg-teal-600 text-white"
            : "border border-zinc-200 bg-white text-zinc-800",
        )}
      >
        {isUser ? (
          <p className="whitespace-pre-wrap break-words">{message.content}</p>
        ) : (
          <AssistantMarkdown content={message.content || ""} />
        )}
        <p className={cn("mt-2 text-[11px]", isUser ? "text-teal-100" : "text-zinc-400")}>
          {formatDate(message.created_at)}
        </p>
      </div>
    </div>
  );
}

function Avatar({ kind }) {
  const Icon = kind === "user" ? User : Bot;
  return (
    <div
      className={cn(
        "flex h-8 w-8 shrink-0 items-center justify-center rounded-full",
        kind === "user" ? "bg-teal-700 text-white" : "bg-teal-100 text-teal-700",
      )}
      aria-hidden
    >
      <Icon className="h-4 w-4" />
    </div>
  );
}

function AssistantMarkdown({ content }) {
  return (
    <div className="space-y-2 break-words [&_a]:text-teal-700 [&_a]:underline [&_code]:rounded [&_code]:bg-zinc-100 [&_code]:px-1 [&_code]:py-0.5 [&_code]:text-[0.85em] [&_h1]:text-base [&_h1]:font-semibold [&_h2]:text-sm [&_h2]:font-semibold [&_h3]:text-sm [&_h3]:font-semibold [&_li]:my-0.5 [&_ol]:my-2 [&_ol]:list-decimal [&_ol]:space-y-1 [&_ol]:pl-5 [&_p]:my-1.5 [&_p]:leading-relaxed [&_strong]:font-semibold [&_ul]:my-2 [&_ul]:list-disc [&_ul]:space-y-1 [&_ul]:pl-5">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
    </div>
  );
}
