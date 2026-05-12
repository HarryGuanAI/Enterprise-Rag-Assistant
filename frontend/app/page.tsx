"use client";

import {
  BookOpen,
  CircleStop,
  FileText,
  Hash,
  History,
  Loader2,
  LockKeyhole,
  MessageSquareText,
  Phone,
  Plus,
  Quote,
  RefreshCw,
  SendHorizontal,
  SlidersHorizontal,
  Upload,
  X,
  UserRound,
} from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import type { ChangeEvent, FormEvent, RefObject } from "react";
import { useEffect, useRef, useState } from "react";

import { apiGet, apiPost, apiPut, apiUpload, streamSsePost } from "@/lib/api";
import type {
  AppSettings,
  ChatCitation,
  ConversationDetailResponse,
  ConversationListResponse,
  ConversationSummary,
  DocumentListResponse,
  DocumentPreviewChunk,
  DocumentPreviewResponse,
  LoginResponse,
  RetrievalDebug,
  StatsResponse,
} from "@/types/api";

type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations?: ChatCitation[];
};

type SidebarMode = "documents" | "history";

const fallbackStats: StatsResponse = {
  document_count: 0,
  ready_document_count: 0,
  chunk_count: 0,
  today_question_count: 0,
  today_refused_count: 0,
  today_model_call_count: 0,
  today_embedding_task_count: 0,
  guest_remaining: 15,
  guest_limit: 15,
};

const defaultSettings: AppSettings = {
  retrieval: {
    top_k: 5,
    min_similarity: 0.6,
    strict_refusal: true,
    enable_hybrid_search: false,
    enable_rerank: false,
  },
  chunking: {
    chunk_size: 800,
    chunk_overlap: 120,
    min_chunk_size: 100,
    enable_section_path: true,
  },
  generation: {
    temperature: 0.2,
    max_tokens: 1200,
  },
};

const exampleQuestions = [
  "你能做什么？",
  "出差报销需要提交哪些材料？",
  "云舟知识库助手支持哪些文档格式？",
  "P0 工单需要多久响应？",
  "API Key 可以写进 README 或工单评论吗？",
  "折扣超过 35% 的报价需要谁审批？",
  "公司年会抽奖一等奖是什么？",
];

const welcomeMessage: ChatMessage = {
  id: "welcome",
  role: "assistant",
  content: "你好，我会基于已入库的企业文档回答问题，并在右侧展示引用来源。请先上传制度文档，或直接问一个和示例文档相关的问题。",
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
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [isContactOpen, setIsContactOpen] = useState(false);
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
  const [settingsDraft, setSettingsDraft] = useState<AppSettings>(defaultSettings);
  const [settingsMessage, setSettingsMessage] = useState<string | null>(null);
  const [isSavingSettings, setIsSavingSettings] = useState(false);
  const [retrievalDebug, setRetrievalDebug] = useState<RetrievalDebug | null>(null);
  const [selectedCitation, setSelectedCitation] = useState<ChatCitation | null>(null);
  const [sidebarMode, setSidebarMode] = useState<SidebarMode>("documents");
  const [isLoadingConversation, setIsLoadingConversation] = useState(false);
  const [conversationMessage, setConversationMessage] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([welcomeMessage]);
  const [citations, setCitations] = useState<ChatCitation[]>([]);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const askAbortControllerRef = useRef<AbortController | null>(null);

  useEffect(() => {
    return () => {
      askAbortControllerRef.current?.abort();
    };
  }, []);

  useEffect(() => {
    setAdminToken(window.localStorage.getItem("admin_token"));
    const storedGuestId = window.localStorage.getItem("guest_id") ?? createLocalId("guest");
    window.localStorage.setItem("guest_id", storedGuestId);
    setGuestId(storedGuestId);
  }, []);

  const statsQuery = useQuery({
    queryKey: ["stats", guestId],
    queryFn: () => apiGet<StatsResponse>(`/api/stats${guestId ? `?guest_id=${encodeURIComponent(guestId)}` : ""}`),
    refetchInterval: 5000,
  });

  const documentsQuery = useQuery({
    queryKey: ["documents"],
    queryFn: () => apiGet<DocumentListResponse>("/api/documents"),
    refetchInterval: 5000,
  });

  const conversationsQuery = useQuery({
    queryKey: ["conversations", guestId, adminToken],
    queryFn: () =>
      apiGet<ConversationListResponse>(
        `/api/chat/conversations${!adminToken && guestId ? `?guest_id=${encodeURIComponent(guestId)}` : ""}`,
        adminToken ?? undefined,
      ),
    enabled: Boolean(adminToken || guestId),
    refetchInterval: 8000,
  });

  const settingsQuery = useQuery({
    queryKey: ["settings"],
    queryFn: () => apiGet<AppSettings>("/api/settings"),
  });

  useEffect(() => {
    if (settingsQuery.data) {
      setSettingsDraft(settingsQuery.data);
    }
  }, [settingsQuery.data]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, chatStatus, isAsking]);

  const stats = statsQuery.data ?? fallbackStats;
  const documents = documentsQuery.data?.items ?? [];
  const conversations = conversationsQuery.data?.items ?? [];
  const statSummary = [
    { label: "文档", value: String(stats.document_count) },
    { label: "分块", value: String(stats.chunk_count) },
    { label: "问答", value: String(stats.today_question_count) },
    { label: "拒答", value: String(stats.today_refused_count) },
    { label: "调用", value: String(stats.today_model_call_count) },
  ];
  const guestText =
    stats.guest_remaining !== null && stats.guest_limit !== null
      ? `游客模式：剩余 ${stats.guest_remaining}/${stats.guest_limit} 次`
      : "游客模式";
  const isAdmin = Boolean(adminToken);
  const hasStartedConversation = messages.some((item) => item.role === "user");
  const currentConversation = conversations.find((item) => item.id === conversationId);

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

  async function handleSaveSettings(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!adminToken) {
      return;
    }
    if (settingsDraft.chunking.chunk_overlap >= settingsDraft.chunking.chunk_size) {
      setSettingsMessage("chunk_overlap 必须小于 chunk_size");
      return;
    }

    setIsSavingSettings(true);
    setSettingsMessage(null);
    try {
      const saved = await apiPut<AppSettings>("/api/settings", settingsDraft, adminToken);
      setSettingsDraft(saved);
      await settingsQuery.refetch();
      setSettingsMessage("设置已保存");
    } catch (error) {
      setSettingsMessage(error instanceof Error ? error.message : "保存失败，请稍后重试");
    } finally {
      setIsSavingSettings(false);
    }
  }

  function updateSettingsDraft(path: string, value: number | boolean) {
    const [group, key] = path.split(".") as [keyof AppSettings, string];
    setSettingsDraft((current) => ({
      ...current,
      [group]: {
        ...current[group],
        [key]: value,
      },
    }));
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

  function handleNewConversation() {
    askAbortControllerRef.current?.abort();
    setConversationId(null);
    setMessages([{ ...welcomeMessage, id: createLocalId("welcome") }]);
    setQuestion("");
    setChatError(null);
    setChatStatus(null);
    setCitations([]);
    setRetrievalDebug(null);
    setConversationMessage(null);
  }

  async function handleOpenConversation(item: ConversationSummary) {
    if (isAsking) {
      return;
    }

    setIsLoadingConversation(true);
    setConversationMessage(null);
    try {
      const detail = await apiGet<ConversationDetailResponse>(
        `/api/chat/conversations/${item.id}${!adminToken && guestId ? `?guest_id=${encodeURIComponent(guestId)}` : ""}`,
        adminToken ?? undefined,
      );
      setConversationId(detail.id);
      setMessages(
        detail.messages.length
          ? detail.messages.map((message) => ({
              id: message.id,
              role: message.role,
              content: message.content,
              citations: message.citations,
            }))
          : [{ ...welcomeMessage, id: createLocalId("welcome") }],
      );
      const lastAssistant = [...detail.messages].reverse().find((message) => message.role === "assistant");
      setCitations(lastAssistant?.citations ?? []);
      setRetrievalDebug(null);
      setChatError(null);
      setChatStatus(null);
      setSidebarMode("history");
    } catch (error) {
      setConversationMessage(error instanceof Error ? error.message : "加载历史对话失败");
    } finally {
      setIsLoadingConversation(false);
    }
  }

  async function handleAsk(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmedQuestion = question.trim();
    if (!trimmedQuestion || isAsking) {
      return;
    }

    const assistantId = createLocalId("assistant");
    const abortController = new AbortController();
    askAbortControllerRef.current = abortController;
    setQuestion("");
    setIsAsking(true);
    setChatError(null);
    setChatStatus("正在提交问题...");
    setCitations([]);
    setRetrievalDebug(null);
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
              const nextCitations = (data.citations as ChatCitation[]) ?? [];
              setCitations(nextCitations);
              setMessages((current) =>
                current.map((item) => (item.id === assistantId ? { ...item, citations: nextCitations } : item)),
              );
            }
            if (eventName === "retrieval_debug") {
              setRetrievalDebug(data as RetrievalDebug);
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
        abortController.signal,
      );
      await statsQuery.refetch();
      await conversationsQuery.refetch();
    } catch (error) {
      if (abortController.signal.aborted) {
        setChatStatus(null);
        setMessages((current) =>
          current.map((item) =>
            item.id === assistantId
              ? {
                  ...item,
                  content: item.content ? `${item.content}\n\n（已手动停止输出）` : "已手动停止输出。",
                }
              : item,
          ),
        );
        return;
      }
      const message = error instanceof Error ? error.message : "问答失败，请稍后重试";
      setChatError(message);
      setMessages((current) =>
        current.map((item) => (item.id === assistantId && !item.content ? { ...item, content: message } : item)),
      );
    } finally {
      if (askAbortControllerRef.current === abortController) {
        askAbortControllerRef.current = null;
      }
      setIsAsking(false);
      setChatStatus(null);
    }
  }

  function handleStopAsking() {
    if (!askAbortControllerRef.current) {
      return;
    }
    setChatStatus("正在停止输出...");
    askAbortControllerRef.current.abort();
  }

  return (
    <main className="h-screen overflow-hidden px-5 py-4 text-ink xl:px-7">
      <section className="mx-auto flex h-full max-w-[1680px] flex-col gap-3">
        <header className="flex shrink-0 items-center justify-between gap-4 px-1">
          <div className="flex min-w-[220px] items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-moss text-base font-semibold text-white shadow-sm">
              云
            </div>
            <div>
              <p className="text-xs uppercase tracking-[0.08em] text-moss/75">Enterprise RAG</p>
              <h1 className="text-xl font-semibold tracking-normal">云舟知识库助手</h1>
            </div>
          </div>

          <div className="hidden min-w-0 flex-1 items-center justify-center lg:flex">
            <div className="flex max-w-full items-center gap-1 overflow-hidden rounded-lg border border-moss/10 bg-white/70 px-2 py-1.5 text-xs text-moss shadow-sm">
              {statSummary.map((item) => (
                <span key={item.label} className="whitespace-nowrap rounded-md px-2 py-1">
                  {item.label} <strong className="font-semibold text-ink">{item.value}</strong>
                </span>
              ))}
            </div>
          </div>

          <div className="flex shrink-0 items-center gap-2">
            <div className="flex items-center gap-2 rounded-md border border-moss/15 bg-white/75 px-3 py-2 text-xs text-moss">
              <LockKeyhole className="h-4 w-4" />
              {isAdmin ? "管理员模式" : guestText}
            </div>
            {isAdmin ? (
              <>
                <button
                  className="flex items-center gap-2 rounded-md border border-moss/20 bg-white/75 px-3 py-2 text-xs text-moss transition hover:bg-reed/50"
                  onClick={() => setIsSettingsOpen(true)}
                >
                  <SlidersHorizontal className="h-4 w-4" />
                  RAG 设置
                </button>
                <button
                  className="rounded-md border border-moss/20 bg-white/75 px-3 py-2 text-xs text-moss transition hover:bg-reed/50"
                  onClick={handleLogout}
                >
                  退出
                </button>
              </>
            ) : (
              <button
                className="rounded-md bg-moss px-3 py-2 text-xs font-medium text-white transition hover:bg-ink"
                onClick={() => setIsLoginOpen(true)}
              >
                管理员登录
              </button>
            )}
          </div>
        </header>

        {!isAdmin ? (
          <section className="flex shrink-0 items-center justify-between gap-3 rounded-lg border border-copper/20 bg-copper/10 px-4 py-3 text-sm text-ink shadow-sm">
            <div className="min-w-0 leading-6">
              <strong className="font-semibold">游客体验提示：</strong>
              由于页面仅用于学习展示，如想体验更多功能，请联系管理员进行登录。
              <span className="ml-2 text-moss">今日剩余 {stats.guest_remaining ?? 0}/{stats.guest_limit ?? 15} 次问答。</span>
            </div>
            <button
              type="button"
              className="flex shrink-0 items-center gap-2 rounded-md bg-moss px-3 py-2 text-xs font-medium text-white transition hover:bg-ink"
              onClick={() => setIsContactOpen(true)}
            >
              <Phone className="h-4 w-4" />
              管理员联系方式
            </button>
          </section>
        ) : null}

        <section className="grid min-h-0 flex-1 gap-4 lg:grid-cols-[230px_minmax(0,1fr)_300px]">
          <aside className="flex min-h-0 flex-col rounded-lg border border-moss/10 bg-white/80 p-3 shadow-panel">
            <div className="mb-3 flex shrink-0 items-center justify-between">
              <h2 className="text-base font-semibold">知识库文档</h2>
              <div className="flex items-center gap-1.5">
                <button
                  className={
                    sidebarMode === "history"
                      ? "rounded-md border border-moss/15 bg-white/75 p-2 text-moss transition hover:bg-reed/50"
                      : "rounded-md border border-moss/15 bg-white/75 p-2 text-moss transition hover:bg-reed/50"
                  }
                  aria-label={sidebarMode === "history" ? "查看知识库文档" : "查看历史对话"}
                  title={sidebarMode === "history" ? "知识库文档" : "历史对话"}
                  onClick={() => setSidebarMode(sidebarMode === "history" ? "documents" : "history")}
                >
                  {sidebarMode === "history" ? <FileText className="h-4 w-4" /> : <History className="h-4 w-4" />}
                </button>
                {sidebarMode === "documents" ? (
                  <button
                    className="rounded-md bg-moss p-2 text-white transition hover:bg-ink disabled:cursor-not-allowed disabled:bg-moss/35"
                    aria-label="上传文档"
                    disabled={!isAdmin || isUploading}
                    title={isAdmin ? "上传文档" : "请先登录管理员账号"}
                    onClick={() => fileInputRef.current?.click()}
                  >
                    {isUploading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />}
                  </button>
                ) : null}
              </div>
              <input
                ref={fileInputRef}
                className="hidden"
                type="file"
                accept=".pdf,.docx,.md,.txt"
                onChange={handleFileChange}
              />
            </div>
            {uploadMessage ? (
              <div className="mb-4 rounded-md border border-reed bg-linen/70 px-3 py-2 text-xs leading-5 text-moss">
                {uploadMessage}
              </div>
            ) : null}
            <div className="min-h-0 flex-1 space-y-2 overflow-y-auto pr-1">
              {sidebarMode === "history" ? (
                <HistoryConversationList
                  conversations={conversations}
                  currentConversationId={conversationId}
                  isLoading={conversationsQuery.isLoading || isLoadingConversation}
                  message={conversationMessage}
                  onOpen={handleOpenConversation}
                />
              ) : documents.length ? (
                documents.map((doc) => (
                  <div key={doc.id} className="rounded-md border border-reed bg-linen/55 px-3 py-2.5">
                    <div className="flex items-center justify-between gap-2">
                      <div className="min-w-0 truncate text-sm font-medium" title={doc.original_filename}>
                        {doc.original_filename}
                      </div>
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
                    <div className="mt-1.5 flex items-center justify-between text-xs text-moss">
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

          <section className="flex min-h-0 flex-col rounded-lg border border-moss/10 bg-white/90 shadow-panel">
            <div className="flex shrink-0 items-start justify-between gap-4 border-b border-moss/10 px-6 py-4">
              <div className="min-w-0">
                <h2 className="truncate text-lg font-semibold">
                  {currentConversation?.title ? currentConversation.title : "企业知识库问答"}
                </h2>
                <p className="mt-1 text-sm text-moss">
                  {conversationId ? "当前为多轮对话，系统会结合最近上下文理解追问。" : "回答严格基于已入库资料；检索不到可靠依据时会拒答。"}
                </p>
              </div>
              <button
                type="button"
                className="flex shrink-0 items-center gap-2 rounded-md border border-moss/20 bg-white/75 px-3 py-2 text-xs text-moss transition hover:bg-reed/50"
                onClick={handleNewConversation}
                disabled={isAsking}
                title="开启新对话"
              >
                <Plus className="h-4 w-4" />
                开启新对话
              </button>
            </div>
            <div className="min-h-0 flex-1 space-y-5 overflow-y-auto px-6 py-5">
              {messages.map((item) => (
                <div
                  key={item.id}
                  className={
                    item.role === "user"
                      ? "ml-auto max-w-[76%] rounded-lg bg-moss px-5 py-4 text-[15px] leading-7 text-white shadow-sm"
                      : "max-w-[86%] rounded-lg border border-reed bg-linen/70 px-5 py-4 text-[15px] leading-7 shadow-sm"
                  }
                >
                  {item.content ? (
                    item.role === "assistant" ? (
                      <>
                        <FormattedAnswer content={item.content} />
                        {item.citations?.length ? (
                          <CitationTags citations={item.citations} onOpen={setSelectedCitation} />
                        ) : null}
                      </>
                    ) : (
                      item.content
                    )
                  ) : (
                    <span className="text-moss">正在生成回答...</span>
                  )}
                </div>
              ))}
              <div ref={messagesEndRef} />
            </div>
            <div className="shrink-0 border-t border-moss/10 bg-white/90 px-6 py-5">
              {chatStatus || chatError ? (
                <div className="mb-4 flex items-center justify-between gap-3 rounded-md border border-reed bg-linen/60 px-3 py-2 text-xs leading-5 text-moss">
                  {chatError ?? chatStatus}
                  {isAsking ? (
                    <button
                      type="button"
                      className="shrink-0 rounded-md border border-copper/20 bg-white/80 px-2 py-1 text-copper transition hover:bg-copper/10"
                      onClick={handleStopAsking}
                    >
                      停止
                    </button>
                  ) : null}
                </div>
              ) : null}
              {!hasStartedConversation ? (
                <div className="mb-4 flex flex-wrap gap-2.5">
                  {exampleQuestions.map((item) => (
                    <button
                      key={item}
                      type="button"
                      className="rounded-md border border-moss/12 bg-linen/55 px-3 py-2 text-xs text-moss transition hover:border-moss/35 hover:bg-linen disabled:cursor-not-allowed disabled:opacity-60"
                      disabled={isAsking}
                      onClick={() => setQuestion(item)}
                      title="点击填入示例问题"
                    >
                      {item}
                    </button>
                  ))}
                </div>
              ) : null}
              <form className="flex gap-4" onSubmit={handleAsk}>
                <textarea
                  className="min-h-[84px] flex-1 resize-none rounded-lg border border-moss/18 bg-white px-4 py-3 text-[15px] leading-6 outline-none transition placeholder:text-moss/45 focus:border-moss focus:ring-2 focus:ring-moss/10"
                  placeholder="输入你的问题，或点击上方示例问题快速体验检索、拒答和引用来源。"
                  value={question}
                  onChange={(event) => setQuestion(event.target.value)}
                />
                <button
                  type={isAsking ? "button" : "submit"}
                  className={
                    isAsking
                      ? "flex min-w-[116px] items-center justify-center gap-2 rounded-lg bg-ink px-5 text-sm font-medium text-white transition hover:bg-copper"
                      : "flex min-w-[116px] items-center justify-center gap-2 rounded-lg bg-copper px-5 text-sm font-medium text-white transition hover:bg-ink disabled:cursor-not-allowed disabled:bg-copper/40"
                  }
                  disabled={!isAsking && !question.trim()}
                  onClick={isAsking ? handleStopAsking : undefined}
                >
                  {isAsking ? <CircleStop className="h-4 w-4" /> : <SendHorizontal className="h-4 w-4" />}
                  {isAsking ? "停止" : "发送"}
                </button>
              </form>
            </div>
          </section>

          <aside className="flex min-h-0 flex-col rounded-lg border border-moss/10 bg-white/80 p-4 shadow-panel">
            <div className="shrink-0">
              <h2 className="text-base font-semibold">引用来源</h2>
              <p className="mt-1 text-xs text-moss">本次回答使用的知识片段</p>
            </div>
            {retrievalDebug ? (
              <section className="mt-4 shrink-0 rounded-md border border-moss/15 bg-white/70 p-3">
                <div className="flex items-center justify-between gap-3">
                  <div className="text-sm font-medium">检索调试</div>
                  <span
                    className={
                      retrievalDebug.refused
                        ? "rounded-md bg-copper/10 px-2 py-1 text-xs text-copper"
                        : "rounded-md bg-moss/10 px-2 py-1 text-xs text-moss"
                    }
                  >
                    {retrievalDebug.refused ? "已拒答" : "已调用模型"}
                  </span>
                </div>
                <p className="mt-2 text-xs leading-5 text-moss">{retrievalDebug.reason}</p>
                <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
                  <DebugMetric label="TopK" value={String(retrievalDebug.top_k)} />
                  <DebugMetric label="阈值" value={retrievalDebug.min_similarity.toFixed(2)} />
                  <DebugMetric label="Top1" value={retrievalDebug.best_score.toFixed(4)} />
                  <DebugMetric label="拒答" value={retrievalDebug.strict_refusal ? "开启" : "关闭"} />
                </div>
                <div className="mt-3 space-y-1 text-xs leading-5 text-moss">
                  <div>Embedding：{retrievalDebug.embedding_model}</div>
                  <div>生成模型：{retrievalDebug.generation_model}</div>
                  <div>
                    Hybrid / Rerank：{retrievalDebug.enable_hybrid_search ? "开" : "关"} /{" "}
                    {retrievalDebug.enable_rerank ? "开" : "关"}
                  </div>
                  <div>检索模式：{retrievalDebug.retrieval_mode ?? "vector"}</div>
                  <div>
                    候选：向量 {retrievalDebug.vector_candidates ?? 0} / 关键词{" "}
                    {retrievalDebug.keyword_candidates ?? 0} / 入选 {retrievalDebug.fused_candidates ?? 0}
                  </div>
                </div>
              </section>
            ) : null}
            <div className="mt-4 min-h-0 flex-1 space-y-3 overflow-y-auto pr-1">
              {citations.length ? (
                citations.map((item) => (
                  <article key={item.chunk_id} className="rounded-md border border-reed bg-linen/60 p-3">
                    <button
                      type="button"
                      className="block w-full text-left text-sm font-medium transition hover:text-moss"
                      onClick={() => setSelectedCitation(item)}
                    >
                      {item.title}
                    </button>
                    <div className="mt-1 text-xs text-copper">
                      Top {item.rank} · 相似度 {item.score.toFixed(4)}
                    </div>
                    <div className="mt-1 text-xs text-moss">
                      {item.source ?? "vector"}
                      {typeof item.vector_score === "number" ? ` · 向量 ${item.vector_score.toFixed(4)}` : ""}
                      {typeof item.keyword_score === "number" ? ` · 关键词 ${item.keyword_score.toFixed(4)}` : ""}
                    </div>
                    {item.section ? <div className="mt-1 text-xs text-moss">{item.section}</div> : null}
                    <p className="mt-3 line-clamp-5 text-sm leading-6 text-ink/85">{item.text}</p>
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

      {selectedCitation ? <CitationPreviewDrawer citation={selectedCitation} onClose={() => setSelectedCitation(null)} /> : null}

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

      {isContactOpen ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink/35 px-4">
          <div className="w-full max-w-md rounded-md border border-moss/15 bg-linen p-5 shadow-panel">
            <div className="mb-4 flex items-start justify-between gap-4">
              <div>
                <div className="mb-2 flex items-center gap-2 text-xs font-medium text-moss">
                  <UserRound className="h-4 w-4" />
                  管理员联系方式 / Admin Contact
                </div>
                <h2 className="text-lg font-semibold">联系管理员获取完整体验</h2>
                <p className="mt-1 text-sm leading-6 text-moss">
                  当前页面仅用于学习展示，更多功能需要管理员登录后体验。
                </p>
              </div>
              <button
                type="button"
                className="rounded-md border border-moss/15 bg-white/70 p-2 text-moss transition hover:bg-reed/50"
                onClick={() => setIsContactOpen(false)}
                aria-label="关闭"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="space-y-3">
              <section className="rounded-md border border-reed bg-white/70 p-4">
                <h3 className="text-sm font-semibold">中文</h3>
                <div className="mt-3 space-y-2 text-sm leading-6 text-ink">
                  <div>管理员姓名：关海龙</div>
                  <div>联系电话：+86 15031597985</div>
                </div>
              </section>
              <section className="rounded-md border border-reed bg-white/70 p-4">
                <h3 className="text-sm font-semibold">English</h3>
                <div className="mt-3 space-y-2 text-sm leading-6 text-ink">
                  <div>Administrator: Harry Guan</div>
                  <div>Phone: +86 15031597985</div>
                </div>
              </section>
            </div>

            <div className="mt-5 flex justify-end">
              <button
                type="button"
                className="rounded-md bg-moss px-4 py-2 text-sm font-medium text-white transition hover:bg-ink"
                onClick={() => setIsContactOpen(false)}
              >
                我知道了
              </button>
            </div>
          </div>
        </div>
      ) : null}

      {isSettingsOpen ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink/35 px-4">
          <div className="max-h-[88vh] w-full max-w-3xl overflow-y-auto rounded-md border border-moss/15 bg-linen p-5 shadow-panel">
            <div className="mb-4 flex items-start justify-between gap-4">
              <div>
                <h2 className="text-lg font-semibold">RAG 设置</h2>
                <p className="mt-1 text-sm text-moss">分块参数对后续上传和重新入库生效。</p>
              </div>
              <button
                className="rounded-md border border-moss/15 px-3 py-2 text-sm text-moss"
                onClick={() => setIsSettingsOpen(false)}
              >
                关闭
              </button>
            </div>

            <form className="space-y-5" onSubmit={handleSaveSettings}>
              <section className="grid gap-3 md:grid-cols-3">
                <NumberField
                  label="TopK"
                  min={1}
                  max={20}
                  value={settingsDraft.retrieval.top_k}
                  onChange={(value) => updateSettingsDraft("retrieval.top_k", value)}
                />
                <NumberField
                  label="相似度阈值"
                  min={0}
                  max={1}
                  step={0.01}
                  value={settingsDraft.retrieval.min_similarity}
                  onChange={(value) => updateSettingsDraft("retrieval.min_similarity", value)}
                />
                <NumberField
                  label="Temperature"
                  min={0}
                  max={2}
                  step={0.1}
                  value={settingsDraft.generation.temperature}
                  onChange={(value) => updateSettingsDraft("generation.temperature", value)}
                />
              </section>

              <section className="grid gap-3 md:grid-cols-3">
                <NumberField
                  label="Chunk Size"
                  min={100}
                  max={3000}
                  value={settingsDraft.chunking.chunk_size}
                  onChange={(value) => updateSettingsDraft("chunking.chunk_size", value)}
                />
                <NumberField
                  label="Overlap"
                  min={0}
                  max={1000}
                  value={settingsDraft.chunking.chunk_overlap}
                  onChange={(value) => updateSettingsDraft("chunking.chunk_overlap", value)}
                />
                <NumberField
                  label="最小分块"
                  min={20}
                  max={1000}
                  value={settingsDraft.chunking.min_chunk_size}
                  onChange={(value) => updateSettingsDraft("chunking.min_chunk_size", value)}
                />
              </section>

              <section className="grid gap-3 md:grid-cols-2">
                <NumberField
                  label="Max Tokens"
                  min={100}
                  max={8000}
                  value={settingsDraft.generation.max_tokens}
                  onChange={(value) => updateSettingsDraft("generation.max_tokens", value)}
                />
                <div className="grid grid-cols-2 gap-2 rounded-md border border-moss/15 bg-white/70 p-3">
                  <ToggleField
                    label="严格拒答"
                    checked={settingsDraft.retrieval.strict_refusal}
                    onChange={(value) => updateSettingsDraft("retrieval.strict_refusal", value)}
                  />
                  <ToggleField
                    label="章节路径"
                    checked={settingsDraft.chunking.enable_section_path}
                    onChange={(value) => updateSettingsDraft("chunking.enable_section_path", value)}
                  />
                  <ToggleField
                    label="Hybrid"
                    checked={settingsDraft.retrieval.enable_hybrid_search}
                    onChange={(value) => updateSettingsDraft("retrieval.enable_hybrid_search", value)}
                  />
                  <ToggleField
                    label="Rerank"
                    checked={settingsDraft.retrieval.enable_rerank}
                    onChange={(value) => updateSettingsDraft("retrieval.enable_rerank", value)}
                  />
                </div>
              </section>

              {settingsMessage ? (
                <div className="rounded-md border border-reed bg-white/70 px-3 py-2 text-sm text-moss">{settingsMessage}</div>
              ) : null}

              <div className="flex justify-end gap-2">
                <button
                  type="button"
                  className="rounded-md border border-moss/15 px-3 py-2 text-sm text-moss"
                  onClick={() => settingsQuery.data && setSettingsDraft(settingsQuery.data)}
                >
                  还原
                </button>
                <button
                  className="rounded-md bg-moss px-4 py-2 text-sm font-medium text-white disabled:bg-moss/40"
                  disabled={isSavingSettings}
                >
                  {isSavingSettings ? "保存中..." : "保存设置"}
                </button>
              </div>
            </form>
          </div>
        </div>
      ) : null}
    </main>
  );
}

function HistoryConversationList({
  conversations,
  currentConversationId,
  isLoading,
  message,
  onOpen,
}: {
  conversations: ConversationSummary[];
  currentConversationId: string | null;
  isLoading: boolean;
  message: string | null;
  onOpen: (conversation: ConversationSummary) => void;
}) {
  if (isLoading && !conversations.length) {
    return (
      <div className="flex items-center gap-2 rounded-md border border-moss/10 bg-linen/45 p-4 text-sm text-moss">
        <Loader2 className="h-4 w-4 animate-spin" />
        正在加载历史对话...
      </div>
    );
  }

  if (!conversations.length) {
    return (
      <div className="rounded-md border border-dashed border-moss/25 bg-linen/40 p-4 text-sm leading-6 text-moss">
        暂无历史对话。发送第一个问题后，这里会保存会话入口。
      </div>
    );
  }

  return (
    <>
      {message ? <div className="rounded-md border border-reed bg-linen/70 px-3 py-2 text-xs text-copper">{message}</div> : null}
      {conversations.map((conversation) => {
        const isActive = conversation.id === currentConversationId;
        return (
          <button
            key={conversation.id}
            type="button"
            className={
              isActive
                ? "w-full rounded-md border border-moss/30 bg-moss/10 px-3 py-2.5 text-left"
                : "w-full rounded-md border border-reed bg-linen/55 px-3 py-2.5 text-left transition hover:border-moss/25 hover:bg-linen"
            }
            onClick={() => onOpen(conversation)}
          >
            <div className="flex items-start gap-2">
              <MessageSquareText className="mt-0.5 h-4 w-4 shrink-0 text-moss" />
              <div className="min-w-0 flex-1">
                <div className="truncate text-sm font-medium" title={conversation.title ?? "未命名对话"}>
                  {conversation.title ?? "未命名对话"}
                </div>
                <div className="mt-1 text-xs text-moss">
                  {conversation.message_count} 条消息 · {formatShortDate(conversation.updated_at)}
                </div>
                {conversation.last_message_preview ? (
                  <p className="mt-2 line-clamp-2 text-xs leading-5 text-ink/72">{conversation.last_message_preview}</p>
                ) : null}
              </div>
            </div>
          </button>
        );
      })}
    </>
  );
}

function formatShortDate(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "";
  }
  return `${date.getMonth() + 1}/${date.getDate()} ${String(date.getHours()).padStart(2, "0")}:${String(
    date.getMinutes(),
  ).padStart(2, "0")}`;
}

function CitationTags({
  citations,
  onOpen,
}: {
  citations: ChatCitation[];
  onOpen: (citation: ChatCitation) => void;
}) {
  return (
    <div className="mt-4 border-t border-moss/10 pt-3">
      <div className="mb-2 flex items-center gap-1.5 text-xs font-medium text-moss">
        <Quote className="h-3.5 w-3.5" />
        引用
      </div>
      <div className="flex flex-wrap gap-2">
        {citations.map((citation) => (
          <button
            key={citation.chunk_id}
            type="button"
            className="rounded-md border border-moss/15 bg-white/70 px-2.5 py-1.5 text-xs text-moss transition hover:border-moss/35 hover:bg-white"
            onClick={() => onOpen(citation)}
            title="查看引用段落"
          >
            来源 {citation.rank} · {citation.title}
          </button>
        ))}
      </div>
    </div>
  );
}

function CitationPreviewDrawer({ citation, onClose }: { citation: ChatCitation; onClose: () => void }) {
  const hitRef = useRef<HTMLDivElement>(null);
  const previewQuery = useQuery({
    queryKey: ["document-preview", citation.document_id],
    queryFn: () => apiGet<DocumentPreviewResponse>(`/api/documents/${citation.document_id}/preview`),
  });

  const preview = previewQuery.data;
  const activeChunk = preview?.chunks.find((chunk) => chunk.id === citation.chunk_id);
  const hasOffsets =
    typeof activeChunk?.start_offset === "number" &&
    typeof activeChunk?.end_offset === "number" &&
    activeChunk.start_offset >= 0 &&
    activeChunk.end_offset > activeChunk.start_offset;

  useEffect(() => {
    if (!previewQuery.isSuccess) {
      return;
    }
    window.setTimeout(() => hitRef.current?.scrollIntoView({ block: "center" }), 0);
  }, [citation.chunk_id, previewQuery.isSuccess]);

  return (
    <div className="fixed inset-0 z-50 bg-ink/20">
      <button className="absolute inset-0 h-full w-full cursor-default" aria-label="关闭引用预览" onClick={onClose} />
      <aside className="absolute right-0 top-0 flex h-full w-full max-w-2xl flex-col border-l border-moss/15 bg-linen shadow-2xl">
        <header className="flex shrink-0 items-start justify-between gap-4 border-b border-moss/10 px-6 py-5">
          <div>
            <div className="mb-2 flex items-center gap-2 text-xs font-medium text-moss">
              <BookOpen className="h-4 w-4" />
              全文预览
            </div>
            <h2 className="text-xl font-semibold">{preview?.original_filename ?? citation.title}</h2>
            {activeChunk?.section_path ?? citation.section ? (
              <p className="mt-1 text-sm text-moss">{activeChunk?.section_path ?? citation.section}</p>
            ) : null}
          </div>
          <button
            type="button"
            className="rounded-md border border-moss/15 bg-white/70 p-2 text-moss transition hover:bg-reed/50"
            onClick={onClose}
            aria-label="关闭"
          >
            <X className="h-4 w-4" />
          </button>
        </header>

        <div className="shrink-0 border-b border-moss/10 px-6 py-3">
          <div className="flex flex-wrap gap-2 text-xs text-moss">
            <span className="rounded-md bg-moss/10 px-2 py-1">Top {citation.rank}</span>
            <span className="rounded-md bg-moss/10 px-2 py-1">相似度 {citation.score.toFixed(4)}</span>
            {typeof activeChunk?.chunk_index === "number" ? (
              <span className="rounded-md bg-moss/10 px-2 py-1">
                Chunk {activeChunk.chunk_index + 1}/{preview?.chunks.length ?? "-"}
              </span>
            ) : null}
            {typeof citation.vector_score === "number" ? (
              <span className="rounded-md bg-moss/10 px-2 py-1">向量 {citation.vector_score.toFixed(4)}</span>
            ) : null}
            {typeof citation.keyword_score === "number" ? (
              <span className="rounded-md bg-moss/10 px-2 py-1">关键词 {citation.keyword_score.toFixed(4)}</span>
            ) : null}
          </div>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto px-6 py-6">
          {previewQuery.isLoading ? (
            <div className="flex items-center gap-2 rounded-md border border-moss/10 bg-white/70 p-4 text-sm text-moss">
              <Loader2 className="h-4 w-4 animate-spin" />
              正在加载全文...
            </div>
          ) : null}
          {previewQuery.isError ? (
            <FallbackCitationHit citation={citation} hitRef={hitRef} label="全文加载失败，显示引用快照" />
          ) : null}
          {preview && hasOffsets && activeChunk ? (
            <FullDocumentText content={preview.content} activeChunk={activeChunk} hitRef={hitRef} />
          ) : null}
          {preview && (!hasOffsets || !activeChunk) ? (
            <div className="space-y-4">
              <FullDocumentText content={preview.content} />
              <FallbackCitationHit citation={citation} hitRef={hitRef} label="引用快照" />
            </div>
          ) : null}
        </div>
      </aside>
    </div>
  );
}

function FullDocumentText({
  content,
  activeChunk,
  hitRef,
}: {
  content: string;
  activeChunk?: DocumentPreviewChunk;
  hitRef?: RefObject<HTMLDivElement>;
}) {
  if (!activeChunk || activeChunk.start_offset === null || activeChunk.end_offset === null) {
    return (
      <article className="rounded-md border border-moss/10 bg-white/70 p-5">
        <p className="whitespace-pre-wrap text-[15px] leading-8 text-ink/88">{content}</p>
      </article>
    );
  }

  const before = content.slice(0, activeChunk.start_offset);
  const hit = content.slice(activeChunk.start_offset, activeChunk.end_offset);
  const after = content.slice(activeChunk.end_offset);

  return (
    <article className="rounded-md border border-moss/10 bg-white/70 p-5">
      {before ? <p className="whitespace-pre-wrap text-[15px] leading-8 text-ink/78">{before}</p> : null}
      <div ref={hitRef} className="my-4 rounded-md border border-copper/35 bg-copper/10 p-4 shadow-sm">
        <div className="mb-2 flex items-center gap-2 text-xs font-semibold text-copper">
          <Hash className="h-3.5 w-3.5" />
          命中分块
        </div>
        <p className="whitespace-pre-wrap text-[15px] leading-8 text-ink">{hit}</p>
      </div>
      {after ? <p className="whitespace-pre-wrap text-[15px] leading-8 text-ink/78">{after}</p> : null}
    </article>
  );
}

function FallbackCitationHit({
  citation,
  hitRef,
  label,
}: {
  citation: ChatCitation;
  hitRef: RefObject<HTMLDivElement>;
  label: string;
}) {
  return (
    <div ref={hitRef} className="rounded-md border border-copper/35 bg-copper/10 p-5 shadow-sm">
      <div className="mb-3 text-xs font-semibold text-copper">{label}</div>
      <p className="whitespace-pre-wrap text-[15px] leading-8 text-ink">{citation.text}</p>
    </div>
  );
}

function NumberField({
  label,
  value,
  min,
  max,
  step = 1,
  onChange,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  step?: number;
  onChange: (value: number) => void;
}) {
  return (
    <label className="block rounded-md border border-moss/15 bg-white/70 p-3 text-sm">
      <span className="text-moss">{label}</span>
      <input
        className="mt-2 w-full rounded-md border border-moss/15 bg-white px-3 py-2 outline-none focus:border-moss"
        max={max}
        min={min}
        step={step}
        type="number"
        value={value}
        onChange={(event) => onChange(Number(event.target.value))}
      />
    </label>
  );
}

function ToggleField({
  label,
  checked,
  onChange,
}: {
  label: string;
  checked: boolean;
  onChange: (value: boolean) => void;
}) {
  return (
    <label className="flex items-center justify-between gap-3 rounded-md border border-reed bg-linen/50 px-3 py-2 text-sm text-moss">
      <span>{label}</span>
      <input className="h-4 w-4 accent-moss" type="checkbox" checked={checked} onChange={(event) => onChange(event.target.checked)} />
    </label>
  );
}

function FormattedAnswer({ content }: { content: string }) {
  const blocks = content
    .replace(/\r\n/g, "\n")
    .split(/\n{2,}/)
    .map((block) => block.trim())
    .filter(Boolean);

  if (!blocks.length) {
    return null;
  }

  return (
    <div className="space-y-3 text-sm leading-7">
      {blocks.map((block, blockIndex) => {
        const lines = block.split("\n").map((line) => line.trim()).filter(Boolean);
        const isBulletList = lines.length > 1 && lines.every((line) => /^[-*]\s+/.test(line));
        const isNumberedList = lines.length > 1 && lines.every((line) => /^\d+[.、]\s*/.test(line));

        if (isBulletList) {
          return (
            <ul key={blockIndex} className="space-y-2 pl-1">
              {lines.map((line, lineIndex) => (
                <li key={lineIndex} className="flex gap-2">
                  <span className="mt-3 h-1.5 w-1.5 shrink-0 rounded-full bg-moss/70" />
                  <span>{renderInlineMarkdown(line.replace(/^[-*]\s+/, ""))}</span>
                </li>
              ))}
            </ul>
          );
        }

        if (isNumberedList) {
          return (
            <ol key={blockIndex} className="space-y-2">
              {lines.map((line, lineIndex) => (
                <li key={lineIndex} className="grid grid-cols-[28px_1fr] gap-2">
                  <span className="mt-0.5 flex h-6 w-6 items-center justify-center rounded-md bg-moss/10 text-xs font-semibold text-moss">
                    {lineIndex + 1}
                  </span>
                  <span>{renderInlineMarkdown(line.replace(/^\d+[.、]\s*/, ""))}</span>
                </li>
              ))}
            </ol>
          );
        }

        return (
          <p key={blockIndex} className="text-ink/95">
            {renderInlineMarkdown(lines.join("\n"))}
          </p>
        );
      })}
    </div>
  );
}

function renderInlineMarkdown(text: string) {
  return text.split(/(\*\*[^*]+\*\*)/g).map((part, index) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return (
        <strong key={index} className="font-semibold text-ink">
          {part.slice(2, -2)}
        </strong>
      );
    }
    return <span key={index}>{part}</span>;
  });
}

function DebugMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-reed bg-linen/60 px-2 py-1.5">
      <div className="text-moss">{label}</div>
      <div className="mt-0.5 font-semibold text-ink">{value}</div>
    </div>
  );
}
