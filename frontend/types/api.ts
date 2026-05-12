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
  rank: number;
};
