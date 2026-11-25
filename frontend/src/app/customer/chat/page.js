import PageHeader from "@/components/shared/PageHeader";
import ChatWorkspace from "@/components/chat/ChatWorkspace";

export default function CustomerChatPage() {
  return (
    <>
      <PageHeader
        title="Support chat"
        description="Conversations call the FastAPI LangGraph agent for order support."
      />
      <ChatWorkspace />
    </>
  );
}