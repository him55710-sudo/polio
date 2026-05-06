import assert from 'node:assert/strict';
import test from 'node:test';

import { AxiosError, AxiosHeaders } from 'axios';

import { api } from '../src/lib/api';
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
    new Error('Backend API is returning HTML instead of JSON. Check VITE_API_URL...'),
    'fallback',
  );

  assert.match(info.userMessage, /프런트가 백엔드 API 대신 웹페이지 HTML을 받고 있습니다/);
  assert.equal(info.debugCode, 'HTML_MISROUTE');
});

test('frontend surfaces HTML misroute from Axios error response with text/html content-type', () => {
  const error = buildAxiosError(
    '<html><body>Error Page</body></html>',
    404,
    { 'content-type': 'text/html; charset=utf-8' }
  );

  const info = getApiErrorInfo(error, 'fallback');

  assert.equal(info.debugCode, 'HTML_MISROUTE');
  assert.match(info.userMessage, /프런트가 백엔드 API 대신 웹페이지 HTML을 받고 있습니다/);
  assert.equal(info.status, 404);
});

test('frontend surfaces network unreachable with clear Korean message', () => {
  const error = new AxiosError('Network Error', 'ERR_NETWORK');
  // No response object simulates a network failure
  
  const info = getApiErrorInfo(error, 'fallback');

  assert.equal(info.debugCode, 'NETWORK_UNREACHABLE');
  assert.match(info.userMessage, /백엔드 서버에 연결할 수 없습니다/);
  assert.match(info.userMessage, /API 서버 주소, 배포 상태, CORS 설정/);
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

test('standard API retries generic 404s from a stale configured API host against same-origin API', async () => {
  const previousWindow = (globalThis as any).window;
  (globalThis as any).window = {
    location: {
      protocol: 'https:',
      hostname: 'uni-foli.vercel.app',
      origin: 'https://uni-foli.vercel.app',
    },
    localStorage: {
      getItem: () => null,
      setItem: () => undefined,
      removeItem: () => undefined,
    },
  };

  const observedBaseUrls: Array<string | undefined> = [];
  let callCount = 0;

  try {
    const result = await api.get<{ ok: boolean }>('/api/v1/runtime/capabilities', {
      baseURL: 'https://uni-foli-api.vercel.app',
      adapter: async (config) => {
        callCount += 1;
        observedBaseUrls.push(config.baseURL);

        if (callCount === 1) {
          throw new AxiosError(
            'Request failed with status code 404',
            'ERR_BAD_REQUEST',
            config,
            {},
            {
              data: 'Not Found',
              status: 404,
              statusText: 'Not Found',
              headers: { 'content-type': 'text/plain; charset=utf-8' },
              config,
              request: {},
            } as any,
          );
        }

        return {
          data: { ok: true },
          status: 200,
          statusText: 'OK',
          headers: { 'content-type': 'application/json' },
          config,
          request: {},
        } as any;
      },
    });

    assert.deepEqual(result, { ok: true });
    assert.deepEqual(observedBaseUrls, [
      'https://uni-foli-api.vercel.app',
      'https://uni-foli.vercel.app',
    ]);
  } finally {
    (globalThis as any).window = previousWindow;
  }
});
