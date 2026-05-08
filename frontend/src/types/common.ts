/** 通用类型定义 */

export interface ResponseMeta {
  page: number;
  page_size: number;
  total: number;
}

export interface UnifiedResponse<T> {
  code: number;
  message: string;
  data: T | null;
  meta?: ResponseMeta | null;
}

export interface PageParams {
  page: number;
  page_size: number;
}

export interface ErrorDetail {
  field: string;
  message: string;
}

export interface ErrorResponse {
  code: number;
  message: string;
  errors: ErrorDetail[];
}
