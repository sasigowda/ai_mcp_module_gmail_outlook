"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Sidebar } from "@/components/chat/Sidebar";
import { ChatInterface } from "@/components/chat/ChatInterface";
import { useAuthStore, useChatStore } from "@/lib/store";
import { auth, chat } from "@/lib/api";

export default function HomePage() {
  const router = useRouter();
  const { user, accessToken, setUser } = useAuthStore();
  const { setActiveConversation, activeConversationId, setConversations } = useChatStore();
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const init = async () => {
      if (!accessToken) { router.push("/auth/login"); return; }
      try {
        setUser(await auth.me());
      } catch {
        router.push("/auth/login");
        return;
      } finally {
        setLoading(false);
      }
    };
    init();
  }, []);

  const handleConversationCreated = async (id: string) => {
    setActiveConversation(id);
    setConversations(await chat.listConversations());
  };

  if (loading) return <LoadingScreen />;

  return (
    <div className="flex h-screen overflow-hidden" style={{ background: "hsl(var(--background))" }}>
      <Sidebar
        activeConvId={activeConversationId}
        onSelectConversation={setActiveConversation}
        onNewConversation={() => setActiveConversation(null)}
      />
      <main className="flex-1 overflow-hidden">
        <ChatInterface
          conversationId={activeConversationId}
          onConversationCreated={handleConversationCreated}
        />
      </main>
    </div>
  );
}

function LoadingScreen() {
  return (
    <div
      className="flex items-center justify-center h-screen flex-col gap-4"
      style={{ background: "hsl(var(--background))" }}
    >
      <div
        className="w-10 h-10 rounded-xl flex items-center justify-center"
        style={{ background: "hsl(var(--primary) / 0.15)", border: "1px solid hsl(var(--primary) / 0.3)" }}
      >
        <div className="w-5 h-5 rounded-full border-2 border-primary border-t-transparent animate-spin" style={{ borderColor: "hsl(var(--primary)) transparent transparent" }} />
      </div>
      <p className="text-sm text-muted-foreground">Loading ChatbotMCP…</p>
    </div>
  );
}
