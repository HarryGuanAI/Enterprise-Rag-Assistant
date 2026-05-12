"use client";

import {
  FileText,
  Gauge,
  Loader2,
  LockKeyhole,
  MessageSquareText,
  RefreshCw,
  SearchCheck,
  SendHorizontal,
  Upload,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { ChangeEvent, FormEvent, useEffect, useRef, useState } from "react";

import { apiGet, apiPost, apiUpload, streamSsePost } from "@/lib/api";
import type { ChatCitation, DocumentListResponse, LoginResponse, StatsResponse } from "@/types/api";

type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
};

const fallbackStats: StatsResponse = {
  document_count: 0,
  ready_document_count: 0,
  chunk_count: 0,
  today_question_count: 0,
  today_refused_count: 0,
  today_model_call_count: 0,
  today_embedding_task_count: 0,
  guest_remaining: 2,
  guest_limit: 2,
};

function statusLabel(status: string) {
  const labels: Record<string, string> = {
    processing: "处理中",
    ready: "已入库",
    failed: "失败",
  };
  return labels[status] ?? status;
}

function createLocalId(prefix: string) {
  return `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export default function HomePage() {
  const [adminToken, setAdminToken] = useState<string | null>(null);
  const [guestId, setGuestId] = useState<string | null>(null);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [isLoginOpen, setIsLoginOpen] = useState(false);
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("");
  const [loginError, setLoginError] = useState<string | null>(null);
  const [isLoggingIn, setIsLoggingIn] = useState(false);
  const [uploadMessage, setUploadMessage] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [question, setQuestion] = useState("");
  const [isAsking, setIsAsking] = useState(false);
  const [chatStatus, setChatStatus] = useState<string | null>(null);
  const [chatError, setChatError] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "welcome",
      role: "assistant",
      content: "你好，我会基于已入库的企业文档回答问题，并在右侧展示引用来源。请先上传制度文档，或直接问一个和示例文档相关的问题。",
    },
  ]);
  const [citations, setCitations] = useState<ChatCitation[]>([]);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    setAdminToken(window.localStorage.getItem("admin_token"));
    const storedGuestId = window.localStorage.getItem("guest_id") ?? createLocalId("guest");
    window.localStorage.setItem("guest_id", storedGuestId);
    setGuestId(storedGuestId);
  }, []);

  const statsQuery = useQuery({
    queryKey: ["stats"],
    queryFn: () => apiGet<StatsResponse>("/api/stats"),
    refetchInterval: 5000,
  });

  const documentsQuery = useQuery({
    queryKey: ["documents"],
    queryFn: () => apiGet<DocumentListResponse>("/api/documents"),
    refetchInterval: 5000,
  });

  const stats = statsQuery.data ?? fallbackStats;
  const documents = documentsQuery.data?.items ?? [];
  const statCards: Array<{ label: string; value: string; icon: LucideIcon }> = [
    { label: "文档数", value: String(stats.document_count), icon: FileText },
    { label: "分块数", value: String(stats.chunk_count), icon: SearchCheck },
    { label: "今日问答", value: String(stats.today_question_count), icon: MessageSquareText },
    { label: "拒答次数", value: String(stats.today_refused_count), icon: Gauge },
    { label: "模型调用", value: String(stats.today_model_call_count), icon: RefreshCw },
  ];
  const guestText =
    stats.guest_remaining !== null && stats.guest_limit !== null
      ? `游客模式：剩余 ${stats.guest_remaining}/${stats.guest_limit} 次`
      : "游客模式";
  const isAdmin = Boolean(adminToken);

  async function handleLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoginError(null);
    setIsLoggingIn(true);

    try {
      const result = await apiPost<LoginResponse>("/api/auth/login", { username, password });
      window.localStorage.setItem("admin_token", result.access_token);
      setAdminToken(result.access_token);
      setIsLoginOpen(false);
      setPassword("");
    } catch (error) {
      setLoginError(error instanceof Error ? error.message : "登录失败，请稍后重试");
    } finally {
      setIsLoggingIn(false);
    }
  }

  function handleLogout() {
    window.localStorage.removeItem("admin_token");
    setAdminToken(null);
  }

  async function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file || !adminToken) {
      return;
    }

    setIsUploading(true);
    setUploadMessage(null);
    const formData = new FormData();
    formData.append("file", file);

    try {
      await apiUpload("/api/documents/upload", formData, adminToken);
      setUploadMessage(`已上传 ${file.name}，正在等待入库处理。`);
      await documentsQuery.refetch();
      await statsQuery.refetch();
    } catch (error) {
      setUploadMessage(error instanceof Error ? error.message : "上传失败，请稍后重试");
    } finally {
      setIsUploading(false);
    }
  }

  async function handleReprocessDocument(documentId: string) {
    if (!adminToken) {
      return;
    }

    setUploadMessage("已提交重试入库任务。");
    try {
      await apiPost(`/api/documents/${documentId}/reprocess`, {}, adminToken);
      await documentsQuery.refetch();
      await statsQuery.refetch();
    } catch (error) {
      setUploadMessage(error instanceof Error ? error.message : "重试入库失败，请稍后重试");
    }
  }

  async function handleAsk(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmedQuestion = question.trim();
    if (!trimmedQuestion || isAsking) {
      return;
    }

    const assistantId = createLocalId("assistant");
    setQuestion("");
    setIsAsking(true);
    setChatError(null);
    setChatStatus("正在提交问题...");
    setCitations([]);
    setMessages((current) => [
      ...current,
      { id: createLocalId("user"), role: "user", content: trimmedQuestion },
      { id: assistantId, role: "assistant", content: "" },
    ]);

    try {
      await streamSsePost(
        "/api/chat/stream",
        {
          question: trimmedQuestion,
          conversation_id: conversationId,
          guest_id: guestId,
        },
        {
          onEvent: (eventName, data) => {
            if (eventName === "status") {
              setChatStatus(String(data.message ?? ""));
            }
            if (eventName === "answer_delta") {
              const content = String(data.content ?? "");
              setMessages((current) =>
                current.map((item) => (item.id === assistantId ? { ...item, content: item.content + content } : item)),
              );
            }
            if (eventName === "citations") {
              setCitations((data.citations as ChatCitation[]) ?? []);
            }
            if (eventName === "error") {
              const message = String(data.message ?? "问答失败，请稍后重试");
              setChatError(message);
              setMessages((current) =>
                current.map((item) => (item.id === assistantId && !item.content ? { ...item, content: message } : item)),
              );
            }
            if (eventName === "done") {
              if (typeof data.conversation_id === "string") {
                setConversationId(data.conversation_id);
              }
              setChatStatus(null);
            }
          },
        },
        adminToken ?? undefined,
      );
      await statsQuery.refetch();
    } catch (error) {
      const message = error instanceof Error ? error.message : "问答失败，请稍后重试";
      setChatError(message);
      setMessages((current) =>
        current.map((item) => (item.id === assistantId && !item.content ? { ...item, content: message } : item)),
      );
    } finally {
      setIsAsking(false);
      setChatStatus(null);
    }
  }

  return (
    <main className="min-h-screen px-6 py-6 text-ink">
      <section className="mx-auto flex max-w-7xl flex-col gap-5">
        <header className="flex flex-wrap items-center justify-between gap-4 rounded-md border border-moss/15 bg-linen/85 px-5 py-4 shadow-panel backdrop-blur">
          <div>
            <p className="text-sm text-moss">Enterprise RAG Assistant</p>
            <h1 className="text-2xl font-semibold tracking-normal">云舟知识库助手</h1>
          </div>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 rounded-md border border-moss/15 bg-white/70 px-3 py-2 text-sm text-moss">
              <LockKeyhole className="h-4 w-4" />
              {isAdmin ? "管理员模式" : guestText}
            </div>
            {isAdmin ? (
              <button
                className="rounded-md border border-moss/20 bg-white/70 px-3 py-2 text-sm text-moss hover:bg-reed/50"
                onClick={handleLogout}
              >
                退出
              </button>
            ) : (
              <button
                className="rounded-md bg-moss px-3 py-2 text-sm font-medium text-white hover:bg-ink"
                onClick={() => setIsLoginOpen(true)}
              >
                管理员登录
              </button>
            )}
          </div>
        </header>

        <section className="grid gap-3 md:grid-cols-5">
          {statCards.map(({ label, value, icon: Icon }) => (
            <div key={label} className="rounded-md border border-moss/15 bg-white/75 p-4 shadow-panel">
              <div className="flex items-center justify-between text-sm text-moss">
                <span>{label}</span>
                <Icon className="h-4 w-4" />
              </div>
              <div className="mt-2 text-2xl font-semibold">{value}</div>
            </div>
          ))}
        </section>

        <section className="grid min-h-[620px] gap-4 lg:grid-cols-[280px_1fr_340px]">
          <aside className="rounded-md border border-moss/15 bg-white/80 p-4 shadow-panel">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="font-semibold">知识库文档</h2>
              <button
                className="rounded-md bg-moss p-2 text-white disabled:cursor-not-allowed disabled:bg-moss/35"
                aria-label="上传文档"
                disabled={!isAdmin || isUploading}
                title={isAdmin ? "上传文档" : "请先登录管理员账号"}
                onClick={() => fileInputRef.current?.click()}
              >
                {isUploading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />}
              </button>
              <input
                ref={fileInputRef}
                className="hidden"
                type="file"
                accept=".pdf,.docx,.md,.txt"
                onChange={handleFileChange}
              />
            </div>
            {uploadMessage ? (
              <div className="mb-3 rounded-md border border-reed bg-linen/70 px-3 py-2 text-xs leading-5 text-moss">
                {uploadMessage}
              </div>
            ) : null}
            <div className="space-y-3">
              {documents.length ? (
                documents.map((doc) => (
                  <div key={doc.id} className="rounded-md border border-reed bg-linen/60 p-3">
                    <div className="flex items-start justify-between gap-2">
                      <div className="break-words text-sm font-medium">{doc.original_filename}</div>
                      {isAdmin && doc.status !== "processing" ? (
                        <button
                          className="shrink-0 rounded-md border border-moss/15 bg-white/70 p-1 text-moss hover:bg-reed/50"
                          title="重新入库"
                          type="button"
                          onClick={() => handleReprocessDocument(doc.id)}
                        >
                          <RefreshCw className="h-3.5 w-3.5" />
                        </button>
                      ) : null}
                    </div>
                    <div className="mt-2 flex items-center justify-between text-xs text-moss">
                      <span>{statusLabel(doc.status)}</span>
                      <span>{doc.chunk_count ? `${doc.chunk_count} chunks` : "等待处理"}</span>
                    </div>
                    {doc.error_message ? <p className="mt-2 text-xs leading-5 text-copper">{doc.error_message}</p> : null}
                  </div>
                ))
              ) : (
                <div className="rounded-md border border-dashed border-moss/25 bg-linen/40 p-4 text-sm leading-6 text-moss">
                  暂无文档。登录管理员账号后上传 Markdown、TXT、PDF 或 DOCX。
                </div>
              )}
            </div>
          </aside>

          <section className="flex flex-col rounded-md border border-moss/15 bg-white/85 shadow-panel">
            <div className="border-b border-moss/10 px-5 py-4">
              <h2 className="font-semibold">企业知识库问答</h2>
              <p className="mt-1 text-sm text-moss">回答严格基于已入库资料；检索不到可靠依据时会拒答。</p>
            </div>
            <div className="flex-1 space-y-4 overflow-y-auto px-5 py-5">
              {messages.map((item) => (
                <div
                  key={item.id}
                  className={
                    item.role === "user"
                      ? "ml-auto max-w-[78%] rounded-md bg-moss px-4 py-3 text-sm leading-6 text-white"
                      : "max-w-[84%] whitespace-pre-wrap rounded-md border border-reed bg-linen/70 px-4 py-3 text-sm leading-6"
                  }
                >
                  {item.content || <span className="text-moss">正在生成回答...</span>}
                </div>
              ))}
            </div>
            <div className="border-t border-moss/10 p-4">
              {chatStatus || chatError ? (
                <div className="mb-3 rounded-md border border-reed bg-linen/60 px-3 py-2 text-xs leading-5 text-moss">
                  {chatError ?? chatStatus}
                </div>
              ) : null}
              <form className="flex gap-3" onSubmit={handleAsk}>
                <textarea
                  className="min-h-16 flex-1 resize-none rounded-md border border-moss/15 bg-white px-3 py-2 text-sm outline-none focus:border-moss"
                  placeholder="输入你的问题，例如：出差报销需要提交哪些材料？"
                  value={question}
                  onChange={(event) => setQuestion(event.target.value)}
                />
                <button
                  className="flex items-center gap-2 rounded-md bg-copper px-5 text-sm font-medium text-white disabled:cursor-not-allowed disabled:bg-copper/40"
                  disabled={isAsking || !question.trim()}
                >
                  {isAsking ? <Loader2 className="h-4 w-4 animate-spin" /> : <SendHorizontal className="h-4 w-4" />}
                  发送
                </button>
              </form>
            </div>
          </section>

          <aside className="rounded-md border border-moss/15 bg-white/80 p-4 shadow-panel">
            <h2 className="font-semibold">引用来源</h2>
            <p className="mt-1 text-sm text-moss">本次回答使用的知识片段</p>
            <div className="mt-4 space-y-3">
              {citations.length ? (
                citations.map((item) => (
                  <article key={item.chunk_id} className="rounded-md border border-reed bg-linen/60 p-3">
                    <div className="text-sm font-medium">{item.title}</div>
                    <div className="mt-1 text-xs text-copper">
                      Top {item.rank} · 相似度 {item.score.toFixed(4)}
                    </div>
                    {item.section ? <div className="mt-1 text-xs text-moss">{item.section}</div> : null}
                    <p className="mt-3 line-clamp-6 text-sm leading-6 text-ink/85">{item.text}</p>
                  </article>
                ))
              ) : (
                <div className="rounded-md border border-dashed border-moss/25 bg-linen/40 p-4 text-sm leading-6 text-moss">
                  发送问题后，这里会显示检索命中的文档片段和相似度分数。
                </div>
              )}
            </div>
          </aside>
        </section>
      </section>

      {isLoginOpen ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink/35 px-4">
          <div className="w-full max-w-sm rounded-md border border-moss/15 bg-linen p-5 shadow-panel">
            <div className="mb-4">
              <h2 className="text-lg font-semibold">管理员登录</h2>
              <p className="mt-1 text-sm text-moss">登录后可以上传文档、绕过游客次数限制，并继续管理知识库。</p>
            </div>
            <form className="space-y-3" onSubmit={handleLogin}>
              <label className="block text-sm">
                <span className="text-moss">账号</span>
                <input
                  className="mt-1 w-full rounded-md border border-moss/15 bg-white px-3 py-2 outline-none focus:border-moss"
                  value={username}
                  onChange={(event) => setUsername(event.target.value)}
                />
              </label>
              <label className="block text-sm">
                <span className="text-moss">密码</span>
                <input
                  className="mt-1 w-full rounded-md border border-moss/15 bg-white px-3 py-2 outline-none focus:border-moss"
                  type="password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  placeholder="请输入 .env 中配置的 ADMIN_PASSWORD"
                />
              </label>
              {loginError ? <div className="rounded-md bg-copper/10 px-3 py-2 text-sm text-copper">{loginError}</div> : null}
              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  className="rounded-md border border-moss/15 px-3 py-2 text-sm text-moss"
                  onClick={() => setIsLoginOpen(false)}
                >
                  取消
                </button>
                <button
                  className="rounded-md bg-moss px-4 py-2 text-sm font-medium text-white disabled:bg-moss/40"
                  disabled={isLoggingIn}
                >
                  {isLoggingIn ? "登录中..." : "登录"}
                </button>
              </div>
            </form>
          </div>
        </div>
      ) : null}
    </main>
  );
}
