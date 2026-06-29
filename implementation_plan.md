# implementation_plan — CAS

## Phase 9E — Production Hardening（次着手）

商用運用ロードマップ [requirements-commercial-ops.md](docs/requirements-commercial-ops.md) の第五フェーズ。API Key 認証、`/health` DB/Redis チェック拡張。

## Phase 9D — 完了

艦隊 10k + チャンク Celery、worker 水平スケール、Space-Track Redis レートリミット、Prometheus `/metrics`。v1.6.0 ship 済み。

## Phase 9C — 完了

`conjunction_alerts` 永続化、triage API、Ops UI タブ、新規 open のみ webhook。v1.5.0 ship 済み。

## Phase 9B — 完了

Celery + Redis 定期スクリーニング。v1.4.0 ship 済み。
