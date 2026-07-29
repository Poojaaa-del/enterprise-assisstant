// src/utils/constants.js

export const API_BASE = import.meta.env?.VITE_API_BASE_URL || 'http://localhost:8000';
export const GOOGLE_CLIENT_ID =
  import.meta.env?.VITE_GOOGLE_CLIENT_ID ||
  '1076653187781-fg9gubrn48163ljfst8h83ajscgqta7g.apps.googleusercontent.com';
export const JIRA_BASE_URL =
  import.meta.env?.VITE_JIRA_BASE_URL || 'https://your-company.atlassian.net/browse';

export const DEFAULT_SAMPLE_LOGS = [
  {
    id: 101,
    status: 'MANDATORY',
    file_name: 'prod_database_cluster.log',
    summary: 'PostgreSQL FATAL: remaining connection slots reserved for superuser',
    file_content:
      '2026-07-26 14:22:01.402 UTC [12048] FATAL: remaining connection slots are reserved for non-replication superuser connections\n2026-07-26 14:22:02.100 UTC [12049] ERROR: connection pool exhausted (max 100 clients reached)',
    jira_key: 'JIRA-4029',
    slack_status: 'SUCCESS',
    created_at: new Date().toISOString(),
  },
  {
    id: 102,
    status: 'LOW_PRIORITY',
    file_name: 'auth_microservice_stdout.log',
    summary: 'JWT Token Verification Warning: clock skew detected (+3.2s)',
    file_content:
      '2026-07-26 15:04:12.880 [WARN] auth.jwt: Clock skew between auth node-02 and identity gateway (+3200ms). Tokens remain valid.',
    jira_key: 'NOT_CREATED',
    slack_status: 'Bypassed',
    created_at: new Date().toISOString(),
  },
  {
    id: 103,
    status: 'MANDATORY',
    file_name: 'ingress_nginx_access.log',
    summary: 'HTTP 502 Bad Gateway spike detected on endpoint /api/v1/triage',
    file_content:
      '192.168.1.45 - - [26/Jul/2026:15:30:10 +0000] "POST /api/v1/triage HTTP/1.1" 502 572 "-" "Go-http-client/1.1"\nUpstream upstream_backend failed to respond in 30.00s',
    jira_key: 'JIRA-4034',
    slack_status: 'SUCCESS',
    created_at: new Date().toISOString(),
  },
];

export const DEFAULT_SAMPLE_KNOWLEDGE = [
  {
    id: 1,
    title: 'Kubernetes Pod OOMKilled Troubleshooting & Limits Runbook',
    category: 'RUNBOOK',
    author: 'Platform Ops',
    content:
      'When pods fail with OOMKilled (Exit Code 137), inspect memory limits in deployment specs. Ensure container requests are set to 70% of limit and JVM max heap is configured via -Xmx.',
    created_at: '2026-07-20',
  },
  {
    id: 2,
    title: 'PostgreSQL Connection Pool Tuning & PgBouncer Guide',
    category: 'INCIDENT',
    author: 'DBA Team',
    content:
      'Guidance on resolving max_connections errors. PgBouncer pool mode should be set to transaction pooling with default_pool_size=50 to prevent backend socket starvation.',
    created_at: '2026-07-22',
  },
  {
    id: 3,
    title: 'SOC2 Compliance & API Access Token Rotation Policy',
    category: 'COMPLIANCE',
    author: 'Security Guild',
    content:
      'All service account JWT tokens must rotate every 90 days. Non-expiring tokens are strictly prohibited in production Kubernetes secrets.',
    created_at: '2026-07-25',
  },
];

export const SAMPLE_INCIDENTS = [
  {
    fileName: 'postgres_pool_exhausted.log',
    content: `2026-07-27 14:22:01.409 UTC [14082] FATAL: remaining connection slots are reserved for non-replication superuser connections
2026-07-27 14:22:01.410 UTC [14082] DETAIL: Connection pool max_connections (100) reached by tenant 'prod_db_main'.
2026-07-27 14:22:01.411 UTC [14082] HINT: Consider increasing max_connections or scaling pgbouncer connection pool size.`,
  },
  {
    fileName: 'aws_s3_permission_denied.log',
    content: `2026-07-27 14:25:30.120 [ERROR] [S3StorageService] AccessDenied: Access Denied to bucket 'enterprise-audit-logs-prod'
ClientError: An error occurred (AccessDenied) when calling the PutObject operation.
User ARN: arn:aws:iam::123456789012:user/triage-worker is not authorized to perform: s3:PutObject on resource: arn:aws:s3:::enterprise-audit-logs-prod/*`,
  },
  {
    fileName: 'k8s_oom_killed_node03.log',
    content: `2026-07-27 14:28:45.890 [CRITICAL] [KubeletEngine] Pod 'triage-worker-7f8b9-x2k9l' on node 'ip-10-0-2-14.ec2.internal' killed by OOMKiller.
Container 'triage-core' consumed 2048Mi memory exceeding limit 512Mi. Exit code: 137. Memory pressure flag set to TRUE.`,
  },
];

export const SAMPLE_ARTICLES = [
  {
    title: 'Database Connection Timeout SOP',
    category: 'RUNBOOK',
    author: 'DevOps Core',
    content:
      "When PostgreSQL connection pool is exhausted (max_connections = 100), check active connections via SELECT * FROM pg_stat_activity WHERE state = 'active'. If connections exceed 90%, restart pgbouncer pooler service or scale reader replicas. Increase connection timeout setting from 30s to 60s in database.yml.",
  },
  {
    title: 'Kubernetes OOMKilled Troubleshooting',
    category: 'INCIDENT',
    author: 'SRE Ops',
    content:
      'Pods terminating with Exit Code 137 (OOMKilled) indicate memory limit violations. Inspect pod memory metrics using kubectl top pod -n production. Update Deployment resources.limits.memory from 512Mi to 2Gi. Enable HeapDumpOnOutOfMemoryError for JVM processes to capture heap dumps.',
  },
  {
    title: 'OAuth 500 Rate Limit Runbook',
    category: 'COMPLIANCE',
    author: 'Security SecOps',
    content:
      'HTTP 500 errors during OAuth token exchange indicate rate limit throttling from Google/Auth0 IDP providers. Implement exponential backoff retry with jitter (max 5 retries, base delay 1000ms). Verify JWT payload claims contain valid sub, email, and exp claims. Audit API key rotation schedule every 90 days.',
  },
];
