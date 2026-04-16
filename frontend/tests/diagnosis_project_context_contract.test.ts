import assert from 'node:assert/strict';
import test from 'node:test';

import type { DiagnosisRunResponse } from '@shared-contracts';

import {
  isDiagnosisProjectNotFound,
  resolveDiagnosisHydrationDecision,
  resolvePreferredDiagnosisProjectId,
  selectLatestDiagnosisProjectDocument,
  shouldApplyDiagnosisResource,
  type DiagnosisProjectDocumentSummary,
} from '../src/lib/diagnosisProjectContext';

function makeRun(partial: Partial<DiagnosisRunResponse>): DiagnosisRunResponse {
  return {
    id: 'run-1',
    project_id: 'project-1',
    status: 'PENDING',
    status_message: null,
    result_payload: null,
    error_message: null,
    review_required: false,
    policy_flags: [],
    citations: [],
    response_trace_id: null,
    async_job_id: null,
    async_job_status: null,
    report_status: null,
    report_async_job_id: null,
    report_async_job_status: null,
    report_artifact_id: null,
    report_error_message: null,
    ...partial,
  };
}

function makeDocument(partial: Partial<DiagnosisProjectDocumentSummary>): DiagnosisProjectDocumentSummary {
  return {
    id: 'doc-1',
    project_id: 'project-1',
    status: 'parsed',
    updated_at: '2026-04-17T00:00:00.000Z',
    latest_async_job_id: null,
    latest_async_job_status: null,
    latest_async_job_error: null,
    last_error: null,
    ...partial,
  };
}

test('query project id wins over stale store project id', () => {
  assert.equal(resolvePreferredDiagnosisProjectId('query-project', 'stale-project'), 'query-project');
  assert.equal(resolvePreferredDiagnosisProjectId(null, 'store-project'), 'store-project');
});

test('stale polling results are ignored unless ids match the active resource', () => {
  assert.equal(shouldApplyDiagnosisResource('doc-1', 'doc-1'), true);
  assert.equal(shouldApplyDiagnosisResource('doc-1', 'doc-2'), false);
  assert.equal(shouldApplyDiagnosisResource(null, 'doc-1'), false);
});

test('latest project document is selected by updated_at descending', () => {
  const latest = selectLatestDiagnosisProjectDocument([
    makeDocument({ id: 'older', updated_at: '2026-04-16T00:00:00.000Z' }),
    makeDocument({ id: 'newer', updated_at: '2026-04-17T00:00:00.000Z' }),
  ]);

  assert.equal(latest?.id, 'newer');
});

test('parsed document without a diagnosis run auto-starts diagnosis hydration', () => {
  const decision = resolveDiagnosisHydrationDecision({
    latestRun: null,
    latestDocument: makeDocument({ id: 'doc-success', status: 'parsed' }),
  });

  assert.equal(decision.mode, 'start_diagnosis');
  assert.equal(decision.step, 'ANALYSING');
  assert.equal(decision.activeDocumentId, 'doc-success');
  assert.equal(decision.shouldStartDiagnosis, true);
});

test('existing failed run restores failed state instead of restarting diagnosis', () => {
  const decision = resolveDiagnosisHydrationDecision({
    latestRun: makeRun({
      id: 'run-failed',
      status: 'FAILED',
      error_message: 'run failed',
    }),
    latestDocument: makeDocument({ id: 'doc-success', status: 'parsed' }),
  });

  assert.equal(decision.mode, 'run_failed');
  assert.equal(decision.step, 'FAILED');
  assert.equal(decision.activeDiagnosisRunId, null);
  assert.match(decision.flowError || '', /run failed/);
});

test('project-not-found detection is driven by the structured backend code', () => {
  assert.equal(isDiagnosisProjectNotFound({ debugCode: 'PROJECT_NOT_FOUND', status: 404 }), true);
  assert.equal(isDiagnosisProjectNotFound({ debugCode: 'DOCUMENT_NOT_FOUND', status: 404 }), false);
});
