import http from 'k6/http';
import { check, sleep } from 'k6';

// Read-only local benchmark. Does not invoke LLMs, register users or mutate data.
export const options = {
  scenarios: {
    single_user: { executor: 'constant-vus', vus: 1, duration: '20s', exec: 'health' },
    five_users: { executor: 'constant-vus', vus: 5, duration: '20s', startTime: '25s', exec: 'health' },
  },
  summaryTrendStats: ['avg', 'med', 'p(95)', 'p(99)', 'max', 'count'],
  // A functional check only; this run establishes latency rather than inventing an SLO.
  thresholds: { checks: ['rate==1'], http_req_failed: ['rate==0'] },
};

export function health() {
  const response = http.get(`${__ENV.HAPPYNEST_BASE_URL || 'http://127.0.0.1:8000'}/api/health`, {
    tags: { name: 'GET /api/health' }, timeout: '10s',
  });
  check(response, {
    'HTTP 200': (r) => r.status === 200,
    'database is healthy': (r) => {
      try { return r.json('status') === 'ok' && r.json('db') === 'ok'; }
      catch { return false; }
    },
  });
  sleep(0.2);
}

export function handleSummary(data) {
  return {
    [__ENV.K6_SUMMARY_PATH || 'k6-api-summary.json']: JSON.stringify({
      ...data,
      happynest: {
        environment: 'local Windows; native FastAPI; real Supabase; no LLM calls',
        endpoint: 'GET /api/health (includes SELECT 1)',
        limitation: 'This measures only health/database readiness, not CRUD endpoints, agent performance or full system capacity.',
        percentile: 'k6 Trend aggregates; dashboard histogram estimates may differ',
        scenarios: '1 VU for 20s, then 5 VUs for 20s; 0.2s think time',
      },
    }, null, 2),
    stdout: '\nSaved read-only API benchmark summary (p95/p99, errors, checks, sample count).\n',
  };
}
