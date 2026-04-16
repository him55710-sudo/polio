import assert from 'node:assert/strict';
import test from 'node:test';

import { AxiosError, AxiosHeaders } from 'axios';

import { getApiErrorInfo } from '../src/lib/apiError';

function buildAxiosError(data: unknown, status = 500, headers?: Record<string, string>): AxiosError {
  return new AxiosError(
    'Request failed',
    'ERR_BAD_RESPONSE',
    {
      headers: new AxiosHeaders(),
      url: '/api/v1/diagnosis/run',
    },
    {},
    {
      data,
      status,
      statusText: 'Error',
      headers: headers || {},
      config: {
        headers: new AxiosHeaders(),
        url: '/api/v1/diagnosis/run',
      } as any,
    } as any,
  );
}

test('frontend surfaces structured backend diagnosis error codes with separated debug info', () => {
  const error = buildAxiosError(
    {
      detail: {
        code: 'DIAGNOSIS_INPUT_EMPTY',
        message: 'Upload and parse at least one student record before running diagnosis.',
        debug_detail: 'combine_project_text reason=no_documents',
        stage: 'combine_project_text',
      },
    },
    400,
  );

  const info = getApiErrorInfo(error, 'fallback');

  assert.equal(info.userMessage, '진단에 사용할 학생부 내용이 아직 없습니다. 업로드와 파싱을 먼저 완료해 주세요.');
  assert.equal(info.debugCode, 'DIAGNOSIS_INPUT_EMPTY');
  assert.match(info.debugDetail || '', /combine_project_text/);
  assert.equal(info.status, 400);
});

test('frontend surfaces HTML misroute as a dedicated debug code', () => {
  const info = getApiErrorInfo(
    new Error('Backend API is returning HTML. Check VITE_API_URL and make sure it points to the backend origin.'),
    'fallback',
  );

  assert.equal(info.userMessage, '프런트가 백엔드 대신 HTML 응답을 받고 있습니다. API 주소 설정을 확인해 주세요.');
  assert.equal(info.debugCode, 'HTML_MISROUTE');
  assert.match(info.debugDetail || '', /VITE_API_URL/);
});

test('frontend surfaces vercel function boot failures as backend startup errors', () => {
  const error = buildAxiosError(
    'A server error has occurred\n\nFUNCTION_INVOCATION_FAILED\n\nicn1::example',
    500,
    { 'x-vercel-error': 'FUNCTION_INVOCATION_FAILED' },
  );

  const info = getApiErrorInfo(error, 'fallback');

  assert.equal(info.userMessage, '백엔드 서버가 정상적으로 기동하지 못했습니다. 배포 설정과 DB 연결 상태를 확인해 주세요.');
  assert.equal(info.debugCode, 'BACKEND_STARTUP_FAILED');
  assert.match(info.debugDetail || '', /FUNCTION_INVOCATION_FAILED/);
  assert.equal(info.status, 500);
});
