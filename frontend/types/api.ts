export type StatsResponse = {
  document_count: number;
  ready_document_count: number;
  chunk_count: number;
  today_question_count: number;
  today_refused_count: number;
  today_model_call_count: number;
  today_embedding_task_count: number;
  guest_remaining: number | null;
  guest_limit: number | null;
};

export type DocumentItem = {
  id: string;
  original_filename: string;
  file_type: string;
  file_size: number;
  status: string;
  chunk_count: number;
  error_message: string | null;
  created_at: string;
};

export type DocumentListResponse = {
  items: DocumentItem[];
};

export type DocumentPreviewChunk = {
  id: string;
  chunk_index: number;
  section_path: string | null;
  content: string;
  start_offset: number | null;
  end_offset: number | null;
};

export type DocumentPreviewResponse = {
  id: string;
  original_filename: string;
  file_type: string;
  status: string;
  content: string;
  chunks: DocumentPreviewChunk[];
};

export type LoginResponse = {
  access_token: string;
  token_type: string;
};

export type LoginRequest = {
  username: string;
  password: string;
};

export type ChatCitation = {
  document_id: string;
  chunk_id: string;
  title: string;
  section: string | null;
  text: string;
  score: number;
  vector_score?: number;
  keyword_score?: number;
  source?: string;
  rank: number;
};

export type ConversationSummary = {
  id: string;
  title: string | null;
  user_type: string;
  guest_id: string | null;
  message_count: number;
  last_message_preview: string | null;
  created_at: string;
  updated_at: string;
};

export type ConversationListResponse = {
  items: ConversationSummary[];
};

export type ConversationMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations: ChatCitation[];
  created_at: string;
};

export type ConversationDetailResponse = {
  id: string;
  title: string | null;
  messages: ConversationMessage[];
};

export type RetrievalDebug = {
  top_k: number;
  min_similarity: number;
  strict_refusal: boolean;
  enable_hybrid_search: boolean;
  enable_rerank: boolean;
  retrieval_mode?: string;
  vector_candidates?: number;
  keyword_candidates?: number;
  fused_candidates?: number;
  embedding_model: string;
  generation_model: string;
  best_score: number;
  refused: boolean;
  will_call_llm: boolean;
  reason: string;
};

export type AppSettings = {
  retrieval: {
    top_k: number;
    min_similarity: number;
    strict_refusal: boolean;
    enable_hybrid_search: boolean;
    enable_rerank: boolean;
  };
  chunking: {
    chunk_size: number;
    chunk_overlap: number;
    min_chunk_size: number;
    enable_section_path: boolean;
  };
  generation: {
    temperature: number;
    max_tokens: number;
  };
};
