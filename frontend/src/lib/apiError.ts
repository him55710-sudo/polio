import axios from 'axios';

function toDetailMessage(detail: unknown): string | null {
  if (!detail) return null;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    const parts = detail
      .map((item) => toDetailMessage(item))
      .filter((item): item is string => Boolean(item && item.trim()));
    return parts.length ? parts.join(' | ') : null;
  }
  if (typeof detail === 'object') {
    const record = detail as Record<string, unknown>;
    if (typeof record.msg === 'string') return record.msg;
    if (typeof record.message === 'string') return record.message;
    if (typeof record.detail === 'string') return record.detail;
    if (Array.isArray(record.detail)) return toDetailMessage(record.detail);
  }
  return null;
}

export function getApiErrorMessage(error: unknown, fallbackMessage: string): string {
  if (axios.isAxiosError(error)) {
    if (!error.response) {
      return '백엔드 서버에 연결할 수 없습니다. API 서버(127.0.0.1:8000)가 실행 중인지 확인해 주세요.';
    }

    const status = error.response.status;
    const data = error.response.data as any;
    
    // UniFoli Specific Error Code Handling
    if (data?.code) {
      const code = data.code;
      if (code === 'AUTH_MISSING') return '인증 정보가 없습니다. 다시 로그인해 주세요.';
      if (code === 'PROJECT_NOT_FOUND') return '요청하신 프로젝트를 찾을 수 없습니다.';
      if (code === 'DOCUMENT_NOT_FOUND') return '요청하신 문서를 찾을 수 없습니다.';
      if (code === 'FILE_MISSING') return '대상 파일을 찾을 수 없습니다.';
      if (code === 'NO_USABLE_TEXT') return '생활기록부에서 읽을 수 있는 텍스트가 부족합니다.';
      if (code === 'PARSE_TIMEOUT') return '문서 분석 시간이 초과되었습니다. 다시 시도해 주세요.';
      if (code === 'DIAGNOSIS_FAILED') return '인공지능 진단 생성에 실패했습니다.';
      if (code === 'INTERNAL_ERROR') return '서버 내부 오류가 발생했습니다.';
    }

    const detailMessage =
      toDetailMessage(data) ||
      toDetailMessage(data?.detail);
    if (detailMessage) return detailMessage;

    if (status === 401) return '인증이 만료되었거나 로그인되지 않았습니다. 다시 로그인해 주세요.';
    if (status === 413) return '파일 용량이 50MB를 초과해 업로드할 수 없습니다.';
    if (status === 429) return '요청이 너무 많습니다. 잠시 후 다시 시도해 주세요.';
    if (status >= 500) return '서버 처리 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.';
  }

  if (error instanceof Error && error.message.trim()) {
    return error.message;
  }

  return fallbackMessage;
}

