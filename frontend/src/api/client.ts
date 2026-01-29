import axios from "axios";

const axiosInstance = axios.create({
  baseURL: "/api",
});

export interface Call {
  id: number;
  filename: string;
  original_path: string;
  duration_sec: number | null;
  size_bytes: number | null;
  status: string;
  created_at: string;
  has_transcript: boolean;
  transcript_updated_at: string | null;
}

export interface Analysis {
  id: number;
  name: string;
  query_text: string;
  created_at: string;
  status: string;
  progress: number;
}

export interface AnalysisResultRow {
  id: number;
  call_id: number;
  analysis_id: number;
  summary?: string | null;
  json_result?: string | null;
  filename?: string | null;
}

export interface AnalysisCreate {
  name: string;
  query_text: string;
  call_ids: number[];
  force_retranscribe?: boolean;
}

export interface AnalysisStatus {
  id: number;
  status: string;
  progress: number;
  total_calls: number;
  processed_calls: number;
  error_count: number;
}

export interface AnalysisTemplate {
  id: number;
  name: string;
  description: string | null;
  query_text: string;
  category: string;
  is_system: boolean;
  created_at: string;
}

export interface Incident {
  file_id: number;
  filename: string;
  start_time: number;
  end_time: number;
  type: string;
  severity: string;
  description: string;
  quote: string;
}

export interface DashboardStats {
  total_files: number;
  files_with_incidents: number;
  total_incidents: number;
  incidents_by_type: Record<string, number>;
  severity_distribution: Record<string, number>;
}

export interface DashboardData {
  analysis_id: number;
  analysis_name: string;
  stats: DashboardStats;
  incidents: Incident[];
}

// API методы
export const api = {
  // Звонки
  async getCalls(): Promise<Call[]> {
    const response = await axiosInstance.get<Call[]>("/calls");
    return response.data;
  },

  async uploadCalls(files: File[]): Promise<void> {
    const formData = new FormData();
    files.forEach((file) => formData.append("files", file));
    await axiosInstance.post("/calls/upload", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
  },

  async deleteCall(id: number): Promise<void> {
    await axiosInstance.delete(`/calls/${id}`);
  },

  async getCallTranscript(id: number): Promise<any> {
    const response = await axiosInstance.get(`/calls/${id}/transcript`);
    return response.data;
  },

  async retranscribeCall(id: number): Promise<{ status: string; message: string }> {
    const response = await axiosInstance.post(`/calls/${id}/retranscribe`);
    return response.data;
  },

  // Исследования
  async createAnalysis(data: AnalysisCreate): Promise<Analysis> {
    const response = await axiosInstance.post<Analysis>("/analysis", data);
    return response.data;
  },

  async getAnalysisStatus(id: number): Promise<AnalysisStatus> {
    const response = await axiosInstance.get<AnalysisStatus>(`/analysis/${id}`);
    return response.data;
  },

  async getAnalysisResults(id: number): Promise<AnalysisResultRow[]> {
    const response = await axiosInstance.get<AnalysisResultRow[]>(`/analysis/${id}/results`);
    return response.data;
  },

  async listAnalyses(): Promise<Analysis[]> {
    const response = await axiosInstance.get<Analysis[]>("/analysis");
    return response.data;
  },

  // Шаблоны
  async getTemplates(category?: string): Promise<AnalysisTemplate[]> {
    const params = category ? { category } : {};
    const response = await axiosInstance.get<AnalysisTemplate[]>("/templates", { params });
    return response.data;
  },

  async getTemplate(id: number): Promise<AnalysisTemplate> {
    const response = await axiosInstance.get<AnalysisTemplate>(`/templates/${id}`);
    return response.data;
  },

  // Dashboard
  async getAnalysisDashboard(id: number): Promise<DashboardData> {
    const response = await axiosInstance.get<DashboardData>(`/analysis/${id}/dashboard`);
    return response.data;
  },
};