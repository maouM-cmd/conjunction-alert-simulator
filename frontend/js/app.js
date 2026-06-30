/** Main UI: TLE input, conjunction scan, batch, CDM compare, maneuver preview. */

import {
  initViewer,
  showOrbits,
  getTcaPositionFromOrbits,
} from "./cesium_viewer.js";

const API_BASE =
  window.location.port === "8080" ? "http://127.0.0.1:8000" : "";

const ISS_SAMPLE = `ISS (ZARYA)
1 25544U 98067A   25179.51782528  .00016717  00000+0  10270-3 0  9993
2 25544  51.6347  74.8662 0004176 315.5599 138.2340 15.50909589423071`;

const DEMO_THRESHOLD_KM = 50;

const els = {
  tabSingle: document.getElementById("tab-single"),
  tabConstellation: document.getElementById("tab-constellation"),
  tabCdm: document.getElementById("tab-cdm"),
  tabAlerts: document.getElementById("tab-alerts"),
  tabOps: document.getElementById("tab-ops"),
  panelSingle: document.getElementById("panel-single"),
  panelConstellation: document.getElementById("panel-constellation"),
  panelCdm: document.getElementById("panel-cdm"),
  panelAlerts: document.getElementById("panel-alerts"),
  panelOps: document.getElementById("panel-ops"),
  tleInput: document.getElementById("tle-input"),
  btnLoadSample: document.getElementById("btn-load-sample"),
  btnLoadDemo: document.getElementById("btn-load-demo"),
  thresholdKm: document.getElementById("threshold-km"),
  sigmaKm: document.getElementById("sigma-km"),
  useAdvancedPc: document.getElementById("use-advanced-pc"),
  useAnisotropicCov: document.getElementById("use-anisotropic-cov"),
  useAltitudePrefilter: document.getElementById("use-altitude-prefilter"),
  notifyWebhook: document.getElementById("notify-webhook"),
  btnWebhookTest: document.getElementById("btn-webhook-test"),
  scanCdmInput: document.getElementById("scan-cdm-input"),
  applyCdmCovariance: document.getElementById("apply-cdm-covariance"),
  autoSpacetrackCdm: document.getElementById("auto-spacetrack-cdm"),
  autoSpacetrackCdmWrap: document.getElementById("auto-spacetrack-cdm-wrap"),
  btnScan: document.getElementById("btn-scan"),
  statusMsg: document.getElementById("status-msg"),
  constellationInput: document.getElementById("constellation-input"),
  batchThresholdKm: document.getElementById("batch-threshold-km"),
  batchUseAdvancedPc: document.getElementById("batch-use-advanced-pc"),
  batchUseAnisotropicCov: document.getElementById("batch-use-anisotropic-cov"),
  batchUseAltitudePrefilter: document.getElementById("batch-use-altitude-prefilter"),
  batchNotifyWebhook: document.getElementById("batch-notify-webhook"),
  batchAutoSpacetrackCdm: document.getElementById("batch-auto-spacetrack-cdm"),
  batchAutoSpacetrackCdmWrap: document.getElementById("batch-auto-spacetrack-cdm-wrap"),
  btnLoadConstellationDemo: document.getElementById("btn-load-constellation-demo"),
  btnBatchScan: document.getElementById("btn-batch-scan"),
  batchStatusMsg: document.getElementById("batch-status-msg"),
  satelliteSelectWrap: document.getElementById("satellite-select-wrap"),
  satelliteSelect: document.getElementById("satellite-select"),
  batchSummary: document.getElementById("batch-summary"),
  cdmInput: document.getElementById("cdm-input"),
  cdmSatTle: document.getElementById("cdm-sat-tle"),
  cdmDebTle: document.getElementById("cdm-deb-tle"),
  btnLoadCdmDemo: document.getElementById("btn-load-cdm-demo"),
  btnCdmCompare: document.getElementById("btn-cdm-compare"),
  btnCdmToScan: document.getElementById("btn-cdm-to-scan"),
  cdmStatusMsg: document.getElementById("cdm-status-msg"),
  cdmResult: document.getElementById("cdm-result"),
  alertNoradId: document.getElementById("alert-norad-id"),
  alertPcMin: document.getElementById("alert-pc-min"),
  alertSatTle: document.getElementById("alert-sat-tle"),
  btnAlertLoadIss: document.getElementById("btn-alert-load-iss"),
  btnFetchAlerts: document.getElementById("btn-fetch-alerts"),
  alertStatusMsg: document.getElementById("alert-status-msg"),
  alertTable: document.getElementById("alert-table"),
  alertTableBody: document.getElementById("alert-table-body"),
  alertCompareResult: document.getElementById("alert-compare-result"),
  scanMeta: document.getElementById("scan-meta"),
  conjunctionList: document.getElementById("conjunction-list"),
  maneuverSection: document.getElementById("maneuver-section"),
  selectedDebris: document.getElementById("selected-debris"),
  maneuverDirection: document.getElementById("maneuver-direction"),
  deltaV: document.getElementById("delta-v"),
  btnManeuver: document.getElementById("btn-maneuver"),
  maneuverResult: document.getElementById("maneuver-result"),
  opsFleetSelect: document.getElementById("ops-fleet-select"),
  opsStatusFilter: document.getElementById("ops-status-filter"),
  btnOpsRefresh: document.getElementById("btn-ops-refresh"),
  opsSummary: document.getElementById("ops-summary"),
  opsStatusMsg: document.getElementById("ops-status-msg"),
  opsAlertTable: document.getElementById("ops-alert-table"),
  opsAlertTableBody: document.getElementById("ops-alert-table-body"),
  opsApiKeyInput: document.getElementById("ops-api-key"),
  opsAuthBar: document.getElementById("ops-auth-bar"),
  opsAuthStatus: document.getElementById("ops-auth-status"),
  btnOpsSsoLogin: document.getElementById("btn-ops-sso-login"),
  btnOpsSsoLogout: document.getElementById("btn-ops-sso-logout"),
  opsSilencesSection: document.getElementById("ops-silences-section"),
  opsBreachStatesSection: document.getElementById("ops-breach-states-section"),
  opsBreachStatesStatus: document.getElementById("ops-breach-states-status"),
  opsBreachStatesTableBody: document.getElementById("ops-breach-states-table-body"),
  opsBreachStatesActionsHeader: document.getElementById("ops-breach-states-actions-header"),
  opsBreachStatesAllSection: document.getElementById("ops-breach-states-all-section"),
  opsBreachStatesAllStatus: document.getElementById("ops-breach-states-all-status"),
  opsBreachStatesAllTableBody: document.getElementById("ops-breach-states-all-table-body"),
  opsBreachStatesBreachingOnly: document.getElementById("ops-breach-states-breaching-only"),
  opsBreachStatesAllBreachingOnly: document.getElementById("ops-breach-states-all-breaching-only"),
  opsBreachHistorySection: document.getElementById("ops-breach-history-section"),
  opsBreachHistoryStatus: document.getElementById("ops-breach-history-status"),
  opsBreachHistoryTableBody: document.getElementById("ops-breach-history-table-body"),
  btnOpsBreachHistoryCsv: document.getElementById("btn-ops-breach-history-csv"),
  btnOpsBreachHistorySummaryCsv: document.getElementById("btn-ops-breach-history-summary-csv"),
  opsBreachHistorySource: document.getElementById("ops-breach-history-source"),
  opsBreachHistoryBreachingOnly: document.getElementById("ops-breach-history-breaching-only"),
  opsBreachHistoryAlertnameOpen: document.getElementById("ops-breach-history-alertname-open"),
  opsBreachHistoryAlertnameHighrisk: document.getElementById("ops-breach-history-alertname-highrisk"),
  opsBreachHistoryRetentionRow: document.getElementById("ops-breach-history-retention-row"),
  opsBreachHistoryRetentionDays: document.getElementById("ops-breach-history-retention-days"),
  btnOpsBreachHistoryRetentionSave: document.getElementById("btn-ops-breach-history-retention-save"),
  opsBreachHistorySince: document.getElementById("ops-breach-history-since"),
  opsBreachHistoryUntil: document.getElementById("ops-breach-history-until"),
  opsBreachRetentionAllSection: document.getElementById("ops-breach-retention-all-section"),
  opsBreachRetentionAllStatus: document.getElementById("ops-breach-retention-all-status"),
  opsBreachRetentionAllTableBody: document.getElementById("ops-breach-retention-all-table-body"),
  opsBreachRetentionBulkDays: document.getElementById("ops-breach-retention-bulk-days"),
  btnOpsBreachRetentionBulkSave: document.getElementById("btn-ops-breach-retention-bulk-save"),
  btnOpsBreachRetentionCsv: document.getElementById("btn-ops-breach-retention-csv"),
  opsBreachRetentionImportFile: document.getElementById("ops-breach-retention-import-file"),
  btnOpsBreachRetentionImport: document.getElementById("btn-ops-breach-retention-import"),
  btnOpsBreachRetentionDryRun: document.getElementById("btn-ops-breach-retention-dry-run"),
  btnOpsBreachRetentionDryRunCsv: document.getElementById("btn-ops-breach-retention-dry-run-csv"),
  opsBreachRetentionPreviewChangesOnly: document.getElementById("ops-breach-retention-preview-changes-only"),
  opsBreachRetentionImportPreviewTable: document.getElementById("ops-breach-retention-import-preview-table"),
  opsBreachRetentionImportPreviewTableBody: document.getElementById("ops-breach-retention-import-preview-table-body"),
  opsBreachRetentionSelectAll: document.getElementById("ops-breach-retention-select-all"),
  opsBreachHistorySummaryTable: document.getElementById("ops-breach-history-summary-table"),
  opsBreachHistorySummaryTableBody: document.getElementById("ops-breach-history-summary-table-body"),
  opsBreachHistoryAllSection: document.getElementById("ops-breach-history-all-section"),
  opsBreachHistoryAllStatus: document.getElementById("ops-breach-history-all-status"),
  opsBreachHistoryAllTableBody: document.getElementById("ops-breach-history-all-table-body"),
  btnOpsBreachHistoryAllCsv: document.getElementById("btn-ops-breach-history-all-csv"),
  btnOpsBreachHistoryAllSummaryCsv: document.getElementById("btn-ops-breach-history-all-summary-csv"),
  btnOpsBreachHistoryAllFleetSummaryCsv: document.getElementById("btn-ops-breach-history-all-fleet-summary-csv"),
  opsBreachHistoryAllSource: document.getElementById("ops-breach-history-all-source"),
  opsBreachHistoryAllBreachingOnly: document.getElementById("ops-breach-history-all-breaching-only"),
  opsBreachHistoryAllAlertnameOpen: document.getElementById("ops-breach-history-all-alertname-open"),
  opsBreachHistoryAllAlertnameHighrisk: document.getElementById("ops-breach-history-all-alertname-highrisk"),
  opsBreachHistoryAllSince: document.getElementById("ops-breach-history-all-since"),
  opsBreachHistoryAllUntil: document.getElementById("ops-breach-history-all-until"),
  opsBreachHistoryAllFleetName: document.getElementById("ops-breach-history-all-fleet-name"),
  opsBreachHistoryAllFleetSummaryLimit: document.getElementById("ops-breach-history-all-fleet-summary-limit"),
  opsBreachHistoryAllSummaryTable: document.getElementById("ops-breach-history-all-summary-table"),
  opsBreachHistoryAllSummaryTableBody: document.getElementById("ops-breach-history-all-summary-table-body"),
  opsBreachHistoryAllFleetSummaryTable: document.getElementById("ops-breach-history-all-fleet-summary-table"),
  opsBreachHistoryAllFleetSummaryTableBody: document.getElementById("ops-breach-history-all-fleet-summary-table-body"),
  opsBreachHistoryAllFleetSummaryPaging: document.getElementById("ops-breach-history-all-fleet-summary-paging"),
  btnOpsBreachHistoryAllFleetSummaryPrev: document.getElementById("btn-ops-breach-history-all-fleet-summary-prev"),
  btnOpsBreachHistoryAllFleetSummaryNext: document.getElementById("btn-ops-breach-history-all-fleet-summary-next"),
  opsBreachHistoryAllFleetSummaryPage: document.getElementById("ops-breach-history-all-fleet-summary-page"),
  opsBreachHistoryAllFleetSummaryOffset: document.getElementById("ops-breach-history-all-fleet-summary-offset"),
  btnOpsBreachHistoryAllFleetSummaryGo: document.getElementById("btn-ops-breach-history-all-fleet-summary-go"),
  opsFleetAlertRulesSection: document.getElementById("ops-fleet-alert-rules-section"),
  opsFleetAlertRulesStatus: document.getElementById("ops-fleet-alert-rules-status"),
  opsFleetAlertRulesBreachingOnly: document.getElementById("ops-fleet-alert-rules-breaching-only"),
  opsFleetAlertRulesBreachingFleetsOnly: document.getElementById("ops-fleet-alert-rules-breaching-fleets-only"),
  opsFleetAlertRulesFormat: document.getElementById("ops-fleet-alert-rules-format"),
  btnOpsFleetAlertRulesDownload: document.getElementById("btn-ops-fleet-alert-rules-download"),
  btnOpsFleetAlertRulesApply: document.getElementById("btn-ops-fleet-alert-rules-apply"),
  btnOpsPrometheusReload: document.getElementById("btn-ops-prometheus-reload"),
  opsPrometheusReloadStatus: document.getElementById("ops-prometheus-reload-status"),
  opsPrometheusReloadHistoryTable: document.getElementById("ops-prometheus-reload-history-table"),
  opsPrometheusReloadHistoryTableBody: document.getElementById("ops-prometheus-reload-history-table-body"),
  opsSilencesStatus: document.getElementById("ops-silences-status"),
  opsSilenceAlertname: document.getElementById("ops-silence-alertname"),
  opsSilenceHours: document.getElementById("ops-silence-hours"),
  opsSilenceComment: document.getElementById("ops-silence-comment"),
  btnOpsSilenceCreate: document.getElementById("btn-ops-silence-create"),
  btnOpsSilencesDeleteAll: document.getElementById("btn-ops-silences-delete-all"),
  btnOpsSilencesDeleteSelected: document.getElementById("btn-ops-silences-delete-selected"),
  opsSilencesSelectAll: document.getElementById("ops-silences-select-all"),
  opsSilencesTable: document.getElementById("ops-silences-table"),
  opsSilencesTableBody: document.getElementById("ops-silences-table-body"),
};

let opsOidcEnabled = false;
let opsAuthMe = { authenticated: false };
let lastOpsBreachRetentionImportPreview = null;

function opsFetchOptions(extraHeaders = {}, { ops = false } = {}) {
  const options = {};
  if (ops) {
    options.headers = getOpsApiHeaders(extraHeaders);
    options.credentials = "include";
  } else if (Object.keys(extraHeaders).length) {
    options.headers = extraHeaders;
  }
  return options;
}

function getOpsApiHeaders(extra = {}) {
  const headers = { ...extra };
  const key = localStorage.getItem("casApiKey") || (els.opsApiKeyInput && els.opsApiKeyInput.value.trim());
  if (key) {
    headers["X-API-Key"] = key;
  }
  return headers;
}

function saveOpsApiKeyFromInput() {
  if (!els.opsApiKeyInput) return;
  const key = els.opsApiKeyInput.value.trim();
  if (key) {
    localStorage.setItem("casApiKey", key);
  } else {
    localStorage.removeItem("casApiKey");
  }
}

async function refreshOpsAuthStatus() {
  if (!els.opsAuthBar) return;
  try {
    const config = await apiGet("/api/v1/auth/oidc/config");
    opsOidcEnabled = Boolean(config.enabled);
    els.opsAuthBar.classList.toggle("hidden", !opsOidcEnabled);
    if (!opsOidcEnabled) {
      return;
    }
    opsAuthMe = await apiGet("/api/v1/auth/me", { ops: true });
    if (opsAuthMe.authenticated) {
      const role = opsAuthMe.is_admin
        ? "admin"
        : opsAuthMe.fleet_id
          ? `fleet ${opsAuthMe.fleet_id}`
          : "user";
      els.opsAuthStatus.textContent = `ログイン: ${opsAuthMe.email} (${role})`;
      els.btnOpsSsoLogin.classList.add("hidden");
      els.btnOpsSsoLogout.classList.remove("hidden");
      if (!opsAuthMe.is_admin && opsAuthMe.fleet_id) {
        els.opsFleetSelect.value = opsAuthMe.fleet_id;
      }
    } else {
      els.opsAuthStatus.textContent = "SSO 未ログイン";
      els.btnOpsSsoLogin.classList.remove("hidden");
      els.btnOpsSsoLogout.classList.add("hidden");
    }
  } catch (err) {
    els.opsAuthStatus.textContent = err.message;
  }
}

function ensureOpsAuthenticated() {
  if (!opsOidcEnabled) {
    return true;
  }
  if (opsAuthMe.authenticated) {
    return true;
  }
  const hasApiKey =
    localStorage.getItem("casApiKey") ||
    (els.opsApiKeyInput && els.opsApiKeyInput.value.trim());
  return Boolean(hasApiKey);
}

let selectedConjunction = null;
let lastSatelliteTle = "";
let batchResults = [];
let currentMode = "single";
let cdmAlerts = [];

function setAlertStatus(msg, isError = false) {
  els.alertStatusMsg.textContent = msg;
  els.alertStatusMsg.classList.toggle("error", isError);
}

function setStatus(msg, isError = false) {
  els.statusMsg.textContent = msg;
  els.statusMsg.classList.toggle("error", isError);
}

function setBatchStatus(msg, isError = false) {
  els.batchStatusMsg.textContent = msg;
  els.batchStatusMsg.classList.toggle("error", isError);
}

function setCdmStatus(msg, isError = false) {
  els.cdmStatusMsg.textContent = msg;
  els.cdmStatusMsg.classList.toggle("error", isError);
}

async function waitForBackend(maxSec = 60, intervalMs = 2000) {
  const deadline = Date.now() + maxSec * 1000;
  while (Date.now() < deadline) {
    try {
      const res = await fetch(`${API_BASE}/health`);
      if (res.ok) {
        return res.json();
      }
    } catch {
      // cold start 中は接続失敗を許容
    }
    setStatus("サーバー起動中（Render cold start で 30〜60 秒かかることがあります）...");
    await new Promise((resolve) => setTimeout(resolve, intervalMs));
  }
  setStatus("サーバーに接続できません。しばらく待ってからページを再読み込みしてください。", true);
  return null;
}

async function apiGet(path, { ops = false } = {}) {
  const res = await fetch(`${API_BASE}${path}`, opsFetchOptions({}, { ops }));
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = data.detail;
    const msg =
      typeof detail === "string"
        ? detail
        : Array.isArray(detail)
          ? detail.map((d) => d.msg).join(", ")
          : `API エラー (${res.status})`;
    throw new Error(msg);
  }
  return data;
}

async function apiPatch(path, body, { ops = false } = {}) {
  const headers = ops
    ? getOpsApiHeaders({ "Content-Type": "application/json" })
    : { "Content-Type": "application/json" };
  const res = await fetch(`${API_BASE}${path}`, {
    method: "PATCH",
    headers,
    body: JSON.stringify(body),
    credentials: ops ? "include" : "same-origin",
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = data.detail;
    const msg = typeof detail === "string" ? detail : `API エラー (${res.status})`;
    throw new Error(msg);
  }
  return data;
}

async function apiPut(path, body, { ops = false } = {}) {
  const headers = ops
    ? getOpsApiHeaders({ "Content-Type": "application/json" })
    : { "Content-Type": "application/json" };
  const res = await fetch(`${API_BASE}${path}`, {
    method: "PUT",
    headers,
    body: JSON.stringify(body),
    credentials: ops ? "include" : "same-origin",
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = data.detail;
    const msg = typeof detail === "string" ? detail : `API エラー (${res.status})`;
    throw new Error(msg);
  }
  return data;
}

async function apiDelete(path, { ops = false } = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "DELETE",
    ...opsFetchOptions({}, { ops }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = data.detail;
    const msg =
      typeof detail === "string"
        ? detail
        : Array.isArray(detail)
          ? detail.map((d) => d.msg).join(", ")
          : `API エラー (${res.status})`;
    throw new Error(msg);
  }
  return data;
}

async function loadOpsFleets() {
  try {
    const fleets = await apiGet("/api/v1/fleets", { ops: true });
    const current = els.opsFleetSelect.value;
    els.opsFleetSelect.innerHTML = '<option value="">— 艦隊を選択 —</option>';
    for (const f of fleets) {
      const opt = document.createElement("option");
      opt.value = f.id;
      opt.textContent = `${f.name} (${f.satellite_count ?? 0} sat)`;
      els.opsFleetSelect.appendChild(opt);
    }
    if (current) {
      els.opsFleetSelect.value = current;
    }
    setOpsStatus("艦隊一覧を読み込みました。");
  } catch (err) {
    setOpsStatus(
      err.message.includes("503")
        ? "DATABASE_URL 未設定 — docker compose で起動してください。"
        : err.message,
      true
    );
  }
}

const OPS_TRANSITION_LABELS = {
  open: "再オープン",
  acknowledged: "Ack",
  false_positive: "誤検知",
  escalated: "エスカレーション",
  mitigation_planned: "対策計画",
  closed: "クローズ",
};

function opsStatusBadge(status) {
  return `<span class="ops-status-badge ops-status-${status}">${status}</span>`;
}

function opsStatusCell(alert) {
  let html = opsStatusBadge(alert.status);
  if (alert.auto_mitigation_planned) {
    html += '<br/><span class="ops-auto-planned">auto-planned</span>';
  }
  return html;
}

function formatSlaLag(hours) {
  if (hours == null) return "—";
  return `${hours.toFixed(1)}h`;
}

function formatSlaLine(slaItem) {
  if (!slaItem || !slaItem.has_active_schedule) {
    return `Screening lag: <span class="ops-sla-na">N/A（schedule なし）</span>`;
  }
  const lag = formatSlaLag(slaItem.screening_lag_hours);
  if (slaItem.screening_sla_ok) {
    return `Screening lag: ${lag} — <span class="ops-sla-ok">OK</span>`;
  }
  return `Screening lag: ${lag} — <span class="ops-sla-overdue">OVERDUE</span>`;
}

function formatApiSloLine(slaResponse, slaItem = null) {
  const fleetCount = slaItem?.fleet_api_request_count ?? 0;
  if (fleetCount > 0) {
    const pct = slaItem.fleet_api_availability_percent.toFixed(2);
    const target = slaResponse?.api_slo_target_percent ?? 99.9;
    if (slaItem.fleet_api_slo_ok) {
      return `Fleet API availability: ${pct}% (target ${target}%) — <span class="ops-slo-ok">OK</span>`;
    }
    return `Fleet API availability: ${pct}% (target ${target}%) — <span class="ops-slo-breach">BREACH</span>`;
  }
  if (!slaResponse || slaResponse.api_request_count === 0) {
    return `API availability: <span class="ops-sla-na">N/A（サンプルなし）</span>`;
  }
  const pct = slaResponse.api_availability_percent.toFixed(2);
  const target = slaResponse.api_slo_target_percent;
  if (slaResponse.api_slo_ok) {
    return `API availability: ${pct}% (target ${target}%) — <span class="ops-slo-ok">OK</span>`;
  }
  return `API availability: ${pct}% (target ${target}%) — <span class="ops-slo-breach">BREACH</span>`;
}

function formatApiSloHistoryLine(history, slaItem = null) {
  const fleetCount = slaItem?.fleet_api_request_count ?? 0;
  const label = fleetCount > 0 ? "Fleet 7d trend" : "7d trend";
  if (!history || !history.items || !history.items.length) {
    return "";
  }
  const sampled = history.items.filter((item) => item.request_count > 0);
  if (!sampled.length) {
    return `<div class="ops-slo-history">${label}: <span class="ops-sla-na">N/A</span></div>`;
  }
  const avg =
    sampled.reduce((sum, item) => sum + item.availability_percent, 0) / sampled.length;
  const breaches = sampled.filter((item) => !item.slo_ok).length;
  const statusClass = breaches === 0 ? "ops-slo-ok" : "ops-slo-breach";
  const statusLabel = breaches === 0 ? "OK" : `${breaches}d BREACH`;
  return `<div class="ops-slo-history">${label}: ${avg.toFixed(2)}% avg — <span class="${statusClass}">${statusLabel}</span></div>`;
}

function formatMitigationPreviewLabel(preview, { prefix = "最新" } = {}) {
  const autoBadge =
    preview.trigger_source === "screening_auto"
      ? ' <span class="ops-mitigation-auto">auto</span>'
      : "";
  return (
    `${prefix}: Δv ${preview.delta_v_ms} m/s (${preview.direction}): ` +
    `miss ${preview.before_miss_distance_km.toFixed(3)} → ${preview.after_miss_distance_km.toFixed(3)} km${autoBadge}`
  );
}

function showMitigationResult(actions, result, { best = false } = {}) {
  let resultDiv = actions.querySelector(".ops-mitigation-result-live");
  if (!resultDiv) {
    resultDiv = document.createElement("div");
    resultDiv.className = "ops-mitigation-result ops-mitigation-result-live";
    actions.appendChild(resultDiv);
  }
  resultDiv.classList.toggle("ops-mitigation-best", best);
  const prefix = best ? "best" : "試算";
  resultDiv.innerHTML = formatMitigationPreviewLabel(result, { prefix });
}

function updateOpsSilencesDeleteSelectedButton() {
  if (!els.btnOpsSilencesDeleteSelected) {
    return;
  }
  const checked = els.opsSilencesTableBody?.querySelectorAll(
    "input.ops-silence-select:checked"
  );
  els.btnOpsSilencesDeleteSelected.disabled = !checked || checked.length === 0;
}

function formatBreachStateLabel(isBreaching) {
  return isBreaching ? "breaching" : "ok";
}

function formatBreachStateBackend(backend) {
  const labels = { redis: "Redis", db: "DB", memory: "in-memory" };
  return labels[backend] || backend;
}

async function setOpsBreachState(fleetId, alertname, isBreaching, sticky = true) {
  const label = isBreaching ? "breaching" : "ok";
  const stickyNote = sticky ? "（sticky）" : "";
  if (!confirm(`${alertname} を ${label} に上書きしますか？${stickyNote}`)) {
    return;
  }
  try {
    await apiPut(
      "/api/v1/ops/prometheus/alertmanager/breach-states",
      { fleet_id: fleetId, alertname, is_breaching: isBreaching, sticky },
      { ops: true }
    );
    await refreshOpsBreachStates();
    if (opsAuthMe.is_admin) {
      await refreshOpsBreachStatesAll();
    }
    await refreshOpsBreachHistory();
    setOpsStatus(`breach 状態を ${label} に設定しました。`);
  } catch (err) {
    setOpsStatus(err.message, true);
  }
}

function appendOpsBreachStateActions(tr, fleetId, item, manualOverrideEnabled, stickyOverrideEnabled) {
  if (!manualOverrideEnabled) {
    return;
  }
  const actionsTd = document.createElement("td");
  actionsTd.className = "ops-breach-states-actions";
  const breachBtn = document.createElement("button");
  breachBtn.type = "button";
  breachBtn.textContent = "breaching";
  breachBtn.disabled = item.is_breaching;
  breachBtn.addEventListener("click", () =>
    setOpsBreachState(fleetId, item.alertname, true, stickyOverrideEnabled)
  );
  const okBtn = document.createElement("button");
  okBtn.type = "button";
  okBtn.textContent = "ok";
  okBtn.disabled = !item.is_breaching;
  okBtn.addEventListener("click", () =>
    setOpsBreachState(fleetId, item.alertname, false, stickyOverrideEnabled)
  );
  actionsTd.appendChild(breachBtn);
  actionsTd.appendChild(okBtn);
  if (stickyOverrideEnabled && item.is_sticky) {
    const clearBtn = document.createElement("button");
    clearBtn.type = "button";
    clearBtn.textContent = "自動同期";
    clearBtn.className = "ops-breach-clear-sticky";
    clearBtn.addEventListener("click", () => clearOpsBreachSticky(fleetId, item.alertname));
    actionsTd.appendChild(clearBtn);
  }
  tr.appendChild(actionsTd);
}

async function clearOpsBreachSticky(fleetId, alertname) {
  if (!confirm(`${alertname} の sticky 上書きを解除しますか？`)) {
    return;
  }
  try {
    await apiDelete(
      `/api/v1/ops/prometheus/alertmanager/breach-states/sticky?fleet_id=${fleetId}&alertname=${encodeURIComponent(alertname)}`,
      { ops: true }
    );
    await refreshOpsBreachStates();
    if (opsAuthMe.is_admin) {
      await refreshOpsBreachStatesAll();
    }
    await refreshOpsBreachHistory();
    setOpsStatus("sticky 上書きを解除しました。");
  } catch (err) {
    setOpsStatus(err.message, true);
  }
}

function breachStatesQuerySuffix({ breachingOnly = false } = {}) {
  return breachingOnly ? "&breaching_only=true" : "";
}

function datetimeLocalToIso(value) {
  if (!value) {
    return null;
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return null;
  }
  return parsed.toISOString();
}

function fleetSummaryLimitValue() {
  const raw = els.opsBreachHistoryAllFleetSummaryLimit?.value?.trim() ?? "100";
  const limit = Number(raw);
  if (!Number.isInteger(limit) || limit < 1 || limit > 500) {
    return 100;
  }
  return limit;
}

let fleetSummaryOffset = 0;
let lastFleetSummaryTotalRows = 0;

function syncFleetSummaryOffsetInput(offset = fleetSummaryOffset) {
  if (els.opsBreachHistoryAllFleetSummaryOffset) {
    els.opsBreachHistoryAllFleetSummaryOffset.value = String(offset);
  }
}

function resetFleetSummaryOffset() {
  fleetSummaryOffset = 0;
  syncFleetSummaryOffsetInput(0);
}

function fleetSummaryPagingParams() {
  return `limit=${fleetSummaryLimitValue()}&offset=${fleetSummaryOffset}`;
}

function fleetSummaryLimitParam() {
  return fleetSummaryPagingParams();
}

function updateFleetSummaryPagingUI(summary) {
  const pagingEl = els.opsBreachHistoryAllFleetSummaryPaging;
  if (!pagingEl) {
    return;
  }
  const totalRows = summary?.total_rows ?? 0;
  const itemCount = summary?.items?.length ?? 0;
  const limit = fleetSummaryLimitValue();
  if (totalRows <= 0) {
    pagingEl.classList.add("hidden");
    return;
  }
  pagingEl.classList.remove("hidden");
  lastFleetSummaryTotalRows = totalRows;
  const rangeStart = itemCount ? fleetSummaryOffset + 1 : fleetSummaryOffset;
  const rangeEnd = fleetSummaryOffset + itemCount;
  if (els.opsBreachHistoryAllFleetSummaryPage) {
    els.opsBreachHistoryAllFleetSummaryPage.textContent =
      `${rangeStart}〜${rangeEnd} / ${totalRows} 件`;
  }
  syncFleetSummaryOffsetInput(summary?.offset ?? fleetSummaryOffset);
  if (els.btnOpsBreachHistoryAllFleetSummaryPrev) {
    els.btnOpsBreachHistoryAllFleetSummaryPrev.disabled = fleetSummaryOffset <= 0;
  }
  if (els.btnOpsBreachHistoryAllFleetSummaryNext) {
    els.btnOpsBreachHistoryAllFleetSummaryNext.disabled =
      fleetSummaryOffset + limit >= totalRows;
  }
}

function breachHistoryFilterOptions(scope = "fleet") {
  if (scope === "all") {
    return {
      sourceEl: els.opsBreachHistoryAllSource,
      breachingOnlyEl: els.opsBreachHistoryAllBreachingOnly,
      alertnameEls: [els.opsBreachHistoryAllAlertnameOpen, els.opsBreachHistoryAllAlertnameHighrisk],
      sinceEl: els.opsBreachHistoryAllSince,
      untilEl: els.opsBreachHistoryAllUntil,
      fleetNameEl: els.opsBreachHistoryAllFleetName,
    };
  }
  return {
    sourceEl: els.opsBreachHistorySource,
    breachingOnlyEl: els.opsBreachHistoryBreachingOnly,
    alertnameEls: [els.opsBreachHistoryAlertnameOpen, els.opsBreachHistoryAlertnameHighrisk],
    sinceEl: els.opsBreachHistorySince,
    untilEl: els.opsBreachHistoryUntil,
  };
}

function breachHistoryQuerySuffix({ sourceEl, breachingOnlyEl, alertnameEls = [], sinceEl, untilEl, fleetNameEl } = {}) {
  const params = [];
  const source = sourceEl?.value?.trim();
  if (source) {
    params.push(`source=${encodeURIComponent(source)}`);
  }
  if (breachingOnlyEl?.checked) {
    params.push("breaching_only=true");
  }
  for (const el of alertnameEls) {
    if (el?.checked && el.value) {
      params.push(`alertnames=${encodeURIComponent(el.value)}`);
    }
  }
  const since = datetimeLocalToIso(sinceEl?.value);
  if (since) {
    params.push(`since=${encodeURIComponent(since)}`);
  }
  const until = datetimeLocalToIso(untilEl?.value);
  if (until) {
    params.push(`until=${encodeURIComponent(until)}`);
  }
  const fleetName = fleetNameEl?.value?.trim();
  if (fleetName) {
    params.push(`fleet_name_contains=${encodeURIComponent(fleetName)}`);
  }
  return params.length ? `&${params.join("&")}` : "";
}

let retentionImportDryRun = false;
let retentionImportDryRunCsv = false;

function renderOpsBreachHistoryFleetSummary(summary, { tableEl, bodyEl } = {}) {
  if (!bodyEl || !tableEl) {
    return;
  }
  if (!summary?.items?.length) {
    tableEl.classList.add("hidden");
    bodyEl.innerHTML = "";
    return;
  }
  tableEl.classList.remove("hidden");
  bodyEl.innerHTML = "";
  for (const item of summary.items) {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${item.day}</td>
      <td>${item.fleet_name || item.fleet_id}</td>
      <td>${item.total}</td>
      <td>${item.breaching_count}</td>
    `;
    bodyEl.appendChild(tr);
  }
  return summary;
}

function renderOpsBreachHistorySummary(summary, { tableEl, bodyEl } = {}) {
  if (!bodyEl || !tableEl) {
    return;
  }
  if (!summary?.items?.length) {
    tableEl.classList.add("hidden");
    bodyEl.innerHTML = "";
    return;
  }
  tableEl.classList.remove("hidden");
  bodyEl.innerHTML = "";
  for (const item of summary.items.slice(0, 14)) {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${item.day}</td>
      <td>${item.total}</td>
      <td>${item.breaching_count}</td>
    `;
    bodyEl.appendChild(tr);
  }
}

async function loadOpsBreachHistorySummary(scope = "fleet", { groupBy = "day" } = {}) {
  const fleetId = els.opsFleetSelect.value;
  const filterSuffix = breachHistoryQuerySuffix(breachHistoryFilterOptions(scope));
  let url = "/api/v1/ops/prometheus/alertmanager/breach-states/history/summary";
  const groupSuffix = groupBy === "fleet" ? "group_by=fleet" : "";
  if (scope === "fleet" && fleetId) {
    url += `?fleet_id=${fleetId}${filterSuffix}`;
  } else {
    const parts = [];
    if (groupSuffix) {
      parts.push(groupSuffix);
    }
    if (groupBy === "fleet") {
      parts.push(fleetSummaryLimitParam());
    }
    if (filterSuffix) {
      parts.push(filterSuffix.slice(1));
    }
    if (parts.length) {
      url += `?${parts.join("&")}`;
    }
  }
  try {
    const summary = await apiGet(url, { ops: true });
    if (scope === "all" && groupBy === "fleet") {
      const fleetSummary = renderOpsBreachHistoryFleetSummary(summary, {
        tableEl: els.opsBreachHistoryAllFleetSummaryTable,
        bodyEl: els.opsBreachHistoryAllFleetSummaryTableBody,
      });
      if (fleetSummary && els.opsBreachHistoryAllStatus) {
        const base = els.opsBreachHistoryAllStatus.textContent.split(" / fleet summary:")[0];
        const rangeStart = fleetSummary.items.length ? fleetSummaryOffset + 1 : fleetSummaryOffset;
        const rangeEnd = fleetSummaryOffset + fleetSummary.items.length;
        els.opsBreachHistoryAllStatus.textContent =
          `${base} / fleet summary: ${fleetSummary.total_rows} 件中 ${rangeStart}〜${rangeEnd} 件表示`;
      }
      updateFleetSummaryPagingUI(fleetSummary);
      return fleetSummary;
    }
    if (scope === "all") {
      renderOpsBreachHistorySummary(summary, {
        tableEl: els.opsBreachHistoryAllSummaryTable,
        bodyEl: els.opsBreachHistoryAllSummaryTableBody,
      });
    } else {
      renderOpsBreachHistorySummary(summary, {
        tableEl: els.opsBreachHistorySummaryTable,
        bodyEl: els.opsBreachHistorySummaryTableBody,
      });
    }
  } catch {
    if (scope === "all" && groupBy === "fleet") {
      els.opsBreachHistoryAllFleetSummaryTable?.classList.add("hidden");
      if (els.opsBreachHistoryAllFleetSummaryTableBody) {
        els.opsBreachHistoryAllFleetSummaryTableBody.innerHTML = "";
      }
      els.opsBreachHistoryAllFleetSummaryPaging?.classList.add("hidden");
    } else if (scope === "all") {
      els.opsBreachHistoryAllSummaryTable?.classList.add("hidden");
      if (els.opsBreachHistoryAllSummaryTableBody) {
        els.opsBreachHistoryAllSummaryTableBody.innerHTML = "";
      }
    } else {
      els.opsBreachHistorySummaryTable?.classList.add("hidden");
      if (els.opsBreachHistorySummaryTableBody) {
        els.opsBreachHistorySummaryTableBody.innerHTML = "";
      }
    }
  }
}

async function refreshOpsBreachStates() {
  const fleetId = els.opsFleetSelect.value;
  if (!fleetId || !els.opsBreachStatesSection) {
    els.opsBreachStatesSection?.classList.add("hidden");
    els.opsBreachStatesAllSection?.classList.add("hidden");
    els.opsBreachHistorySection?.classList.add("hidden");
    return;
  }
  els.opsBreachStatesSection.classList.remove("hidden");
  const breachingOnly = Boolean(els.opsBreachStatesBreachingOnly?.checked);
  try {
    const listing = await apiGet(
      `/api/v1/ops/prometheus/alertmanager/breach-states?fleet_id=${fleetId}${breachStatesQuerySuffix({ breachingOnly })}`,
      { ops: true }
    );
    const overrideOn = listing.manual_override_enabled === true;
    const stickyOn = listing.sticky_override_enabled === true;
    els.opsBreachStatesActionsHeader?.classList.toggle("hidden", !overrideOn);
    els.opsBreachStatesStatus.textContent = `store: ${formatBreachStateBackend(listing.backend)}${stickyOn ? " / sticky ON" : ""}`;
    els.opsBreachStatesTableBody.innerHTML = "";
    for (const item of listing.items) {
      const tr = document.createElement("tr");
      const stateClass = item.is_breaching ? "ops-breach-active" : "ops-breach-ok";
      const stickyLabel = item.is_sticky ? ' <span class="ops-breach-sticky-badge">sticky</span>' : "";
      tr.innerHTML = `
        <td>${item.alertname}</td>
        <td class="${stateClass}">${formatBreachStateLabel(item.is_breaching)}${stickyLabel}</td>
      `;
      appendOpsBreachStateActions(tr, fleetId, item, overrideOn, stickyOn);
      els.opsBreachStatesTableBody.appendChild(tr);
    }
  } catch (err) {
    if (err.message.includes("無効")) {
      els.opsBreachStatesStatus.textContent = "Alertmanager push は無効です。";
      els.opsBreachStatesTableBody.innerHTML = "";
      els.opsBreachStatesActionsHeader?.classList.add("hidden");
      return;
    }
    els.opsBreachStatesStatus.textContent = err.message;
  }
}

async function refreshOpsBreachStatesAll() {
  if (!opsAuthMe.is_admin || !els.opsBreachStatesAllSection) {
    els.opsBreachStatesAllSection?.classList.add("hidden");
    return;
  }
  els.opsBreachStatesAllSection.classList.remove("hidden");
  const breachingOnly = Boolean(els.opsBreachStatesAllBreachingOnly?.checked);
  try {
    const listing = await apiGet(
      `/api/v1/ops/prometheus/alertmanager/breach-states${breachingOnly ? "?breaching_only=true" : ""}`,
      { ops: true }
    );
    els.opsBreachStatesAllStatus.textContent = `store: ${formatBreachStateBackend(listing.backend)} / ${listing.total} 行`;
    els.opsBreachStatesAllTableBody.innerHTML = "";
    for (const item of listing.items) {
      const tr = document.createElement("tr");
      const stateClass = item.is_breaching ? "ops-breach-active" : "ops-breach-ok";
      const stickyLabel = item.is_sticky ? ' <span class="ops-breach-sticky-badge">sticky</span>' : "";
      tr.innerHTML = `
        <td>${item.fleet_name || item.fleet_id}</td>
        <td>${item.alertname}</td>
        <td class="${stateClass}">${formatBreachStateLabel(item.is_breaching)}${stickyLabel}</td>
      `;
      els.opsBreachStatesAllTableBody.appendChild(tr);
    }
  } catch (err) {
    if (err.message.includes("無効")) {
      els.opsBreachStatesAllStatus.textContent = "Alertmanager push は無効です。";
      els.opsBreachStatesAllTableBody.innerHTML = "";
      return;
    }
    els.opsBreachStatesAllStatus.textContent = err.message;
  }
}

async function refreshOpsBreachHistory() {
  const fleetId = els.opsFleetSelect.value;
  if (!fleetId || !els.opsBreachHistorySection) {
    els.opsBreachHistorySection?.classList.add("hidden");
    return;
  }
  els.opsBreachHistorySection.classList.remove("hidden");
  const filterSuffix = breachHistoryQuerySuffix(breachHistoryFilterOptions("fleet"));
  els.opsBreachHistoryRetentionRow?.classList.toggle("hidden", !opsAuthMe.is_admin);
  if (opsAuthMe.is_admin && els.opsBreachHistoryRetentionDays) {
    try {
      const settings = await apiGet("/api/v1/ops/fleets/breach-history-settings", { ops: true });
      const row = settings.items.find((item) => item.fleet_id === fleetId);
      if (row) {
        els.opsBreachHistoryRetentionDays.value =
          row.retention_days != null ? String(row.retention_days) : "";
        els.opsBreachHistoryRetentionDays.placeholder = String(row.effective_retention_days);
      }
    } catch {
      // retention 一覧取得失敗時は入力欄をそのまま
    }
  }
  try {
    const listing = await apiGet(
      `/api/v1/ops/prometheus/alertmanager/breach-states/history?fleet_id=${fleetId}&limit=50${filterSuffix}`,
      { ops: true }
    );
    els.opsBreachHistoryStatus.textContent = `${listing.total} 件の履歴（直近 ${listing.items.length} 件表示）`;
    els.opsBreachHistoryTableBody.innerHTML = "";
    for (const item of listing.items) {
      const tr = document.createElement("tr");
      const stateClass = item.is_breaching ? "ops-breach-active" : "ops-breach-ok";
      tr.innerHTML = `
        <td>${formatTime(item.created_at)}</td>
        <td>${item.alertname}</td>
        <td class="${stateClass}">${formatBreachStateLabel(item.is_breaching)}</td>
        <td>${item.source}</td>
        <td>${item.is_sticky ? "yes" : "—"}</td>
      `;
      els.opsBreachHistoryTableBody.appendChild(tr);
    }
    await loadOpsBreachHistorySummary("fleet");
  } catch (err) {
    if (err.message.includes("履歴は無効")) {
      els.opsBreachHistoryStatus.textContent = "breach 履歴は無効です。";
      els.opsBreachHistoryTableBody.innerHTML = "";
      return;
    }
    els.opsBreachHistoryStatus.textContent = err.message;
  }
}

async function downloadOpsBreachHistoryCsv() {
  const fleetId = els.opsFleetSelect.value;
  if (!fleetId) {
    return;
  }
  const filterSuffix = breachHistoryQuerySuffix(breachHistoryFilterOptions("fleet"));
  try {
    const res = await fetch(
      `${API_BASE}/api/v1/ops/prometheus/alertmanager/breach-states/history?fleet_id=${fleetId}&format=csv${filterSuffix}`,
      {
        headers: getOpsApiHeaders(),
        credentials: "include",
      }
    );
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new Error(data.detail || `API エラー (${res.status})`);
    }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `breach-history-${fleetId}.csv`;
    a.click();
    URL.revokeObjectURL(url);
    setOpsStatus("CSV をダウンロードしました。");
  } catch (err) {
    setOpsStatus(err.message, true);
  }
}

function breachHistorySummaryDownloadUrl(scope, { groupBy = "day" } = {}) {
  const fleetId = els.opsFleetSelect.value;
  const filterSuffix = breachHistoryQuerySuffix(breachHistoryFilterOptions(scope));
  let url = `${API_BASE}/api/v1/ops/prometheus/alertmanager/breach-states/history/summary?format=csv`;
  if (scope === "all" && groupBy === "fleet") {
    url += "&group_by=fleet";
    url += `&${fleetSummaryLimitParam()}`;
  }
  if (scope === "fleet" && fleetId) {
    url += `&fleet_id=${fleetId}${filterSuffix}`;
  } else if (filterSuffix) {
    url += filterSuffix;
  }
  return url;
}

async function downloadOpsBreachHistorySummaryCsv() {
  const fleetId = els.opsFleetSelect.value;
  if (!fleetId) {
    return;
  }
  try {
    const res = await fetch(breachHistorySummaryDownloadUrl("fleet"), {
      headers: getOpsApiHeaders(),
      credentials: "include",
    });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new Error(data.detail || `API エラー (${res.status})`);
    }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `breach-history-summary-${fleetId}.csv`;
    a.click();
    URL.revokeObjectURL(url);
    setOpsStatus("summary CSV をダウンロードしました。");
  } catch (err) {
    setOpsStatus(err.message, true);
  }
}

async function refreshOpsBreachHistoryAll() {
  if (!opsAuthMe.is_admin || !els.opsBreachHistoryAllSection) {
    els.opsBreachHistoryAllSection?.classList.add("hidden");
    return;
  }
  resetFleetSummaryOffset();
  els.opsBreachHistoryAllSection.classList.remove("hidden");
  const filterSuffix = breachHistoryQuerySuffix(breachHistoryFilterOptions("all"));
  try {
    const listing = await apiGet(
      `/api/v1/ops/prometheus/alertmanager/breach-states/history?limit=50${filterSuffix}`,
      { ops: true }
    );
    els.opsBreachHistoryAllStatus.textContent = `${listing.total} 件の履歴（直近 ${listing.items.length} 件表示）`;
    els.opsBreachHistoryAllTableBody.innerHTML = "";
    for (const item of listing.items) {
      const tr = document.createElement("tr");
      const stateClass = item.is_breaching ? "ops-breach-active" : "ops-breach-ok";
      tr.innerHTML = `
        <td>${formatTime(item.created_at)}</td>
        <td>${item.fleet_name || item.fleet_id}</td>
        <td>${item.alertname}</td>
        <td class="${stateClass}">${formatBreachStateLabel(item.is_breaching)}</td>
        <td>${item.source}</td>
        <td>${item.is_sticky ? "yes" : "—"}</td>
      `;
      els.opsBreachHistoryAllTableBody.appendChild(tr);
    }
    await loadOpsBreachHistorySummary("all");
    await loadOpsBreachHistorySummary("all", { groupBy: "fleet" });
  } catch (err) {
    if (err.message.includes("履歴は無効")) {
      els.opsBreachHistoryAllStatus.textContent = "breach 履歴は無効です。";
      els.opsBreachHistoryAllTableBody.innerHTML = "";
      return;
    }
    els.opsBreachHistoryAllStatus.textContent = err.message;
  }
}

async function downloadOpsBreachHistoryAllCsv() {
  const filterSuffix = breachHistoryQuerySuffix(breachHistoryFilterOptions("all"));
  try {
    const res = await fetch(
      `${API_BASE}/api/v1/ops/prometheus/alertmanager/breach-states/history?format=csv${filterSuffix}`,
      {
        headers: getOpsApiHeaders(),
        credentials: "include",
      }
    );
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new Error(data.detail || `API エラー (${res.status})`);
    }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "breach-history-all.csv";
    a.click();
    URL.revokeObjectURL(url);
    setOpsStatus("全艦隊 CSV をダウンロードしました。");
  } catch (err) {
    setOpsStatus(err.message, true);
  }
}

async function downloadOpsBreachHistoryAllSummaryCsv() {
  try {
    const res = await fetch(breachHistorySummaryDownloadUrl("all"), {
      headers: getOpsApiHeaders(),
      credentials: "include",
    });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new Error(data.detail || `API エラー (${res.status})`);
    }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "breach-history-summary-all.csv";
    a.click();
    URL.revokeObjectURL(url);
    setOpsStatus("全艦隊 summary CSV をダウンロードしました。");
  } catch (err) {
    setOpsStatus(err.message, true);
  }
}

async function downloadOpsBreachHistoryAllFleetSummaryCsv() {
  try {
    const res = await fetch(breachHistorySummaryDownloadUrl("all", { groupBy: "fleet" }), {
      headers: getOpsApiHeaders(),
      credentials: "include",
    });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new Error(data.detail || `API エラー (${res.status})`);
    }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "breach-history-fleet-summary.csv";
    a.click();
    URL.revokeObjectURL(url);
    setOpsStatus("fleet summary CSV をダウンロードしました。");
  } catch (err) {
    setOpsStatus(err.message, true);
  }
}

async function downloadOpsBreachRetentionCsv() {
  if (!opsAuthMe.is_admin) {
    return;
  }
  try {
    const res = await fetch(`${API_BASE}/api/v1/ops/fleets/breach-history-settings?format=csv`, {
      headers: getOpsApiHeaders(),
      credentials: "include",
    });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new Error(data.detail || `API エラー (${res.status})`);
    }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "breach-history-retention.csv";
    a.click();
    URL.revokeObjectURL(url);
    setOpsStatus("retention CSV をダウンロードしました。");
  } catch (err) {
    setOpsStatus(err.message, true);
  }
}

function retentionImportChangesOnlyQuery() {
  if (els.opsBreachRetentionPreviewChangesOnly?.checked !== false) {
    return "&changes_only=true";
  }
  return "";
}

async function changeFleetSummaryPage(delta) {
  const limit = fleetSummaryLimitValue();
  const nextOffset = fleetSummaryOffset + delta * limit;
  if (nextOffset < 0) {
    return;
  }
  fleetSummaryOffset = nextOffset;
  await loadOpsBreachHistorySummary("all", { groupBy: "fleet" });
}

async function goToFleetSummaryOffset(raw) {
  const parsed = Number(String(raw ?? "").trim());
  if (!Number.isInteger(parsed) || parsed < 0) {
    setOpsStatus("offset は 0 以上の整数を指定してください。", true);
    return;
  }
  if (lastFleetSummaryTotalRows <= 0) {
    fleetSummaryOffset = 0;
  } else {
    fleetSummaryOffset = Math.min(parsed, lastFleetSummaryTotalRows - 1);
  }
  await loadOpsBreachHistorySummary("all", { groupBy: "fleet" });
}

async function importOpsBreachRetentionCsv(dryRun = false) {
  if (!opsAuthMe.is_admin) {
    return;
  }
  const file = els.opsBreachRetentionImportFile?.files?.[0];
  if (!file) {
    return;
  }
  const formData = new FormData();
  formData.append("file", file, file.name);
  const query = dryRun ? "?dry_run=true" : "";
  try {
    const res = await fetch(`${API_BASE}/api/v1/ops/fleets/breach-history-settings/import${query}`, {
      method: "POST",
      headers: getOpsApiHeaders(),
      credentials: "include",
      body: formData,
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(data.detail || `API エラー (${res.status})`);
    }
    const errNote = data.errors?.length ? ` / 警告 ${data.errors.length} 件` : "";
    if (dryRun) {
      els.opsBreachRetentionAllStatus.textContent =
        `dry-run: ${data.preview?.length ?? 0} 件プレビュー、${data.skipped} 件スキップ${errNote}`;
      lastOpsBreachRetentionImportPreview = {
        preview: data.preview ?? [],
        errors: data.errors ?? [],
      };
      renderOpsBreachRetentionImportPreview(
        lastOpsBreachRetentionImportPreview.preview,
        lastOpsBreachRetentionImportPreview.errors
      );
      setOpsStatus("retention CSV dry-run を完了しました（DB 変更なし）。");
    } else {
      els.opsBreachRetentionAllStatus.textContent =
        `${data.updated} 件更新、${data.skipped} 件スキップ${errNote}`;
      els.opsBreachRetentionImportPreviewTable?.classList.add("hidden");
      if (els.opsBreachRetentionImportPreviewTableBody) {
        els.opsBreachRetentionImportPreviewTableBody.innerHTML = "";
      }
      lastOpsBreachRetentionImportPreview = null;
      await refreshOpsBreachRetentionAll();
      setOpsStatus(`retention CSV をインポートしました（${data.updated} 件更新）。`);
    }
    if (data.errors?.length) {
      console.warn("retention import errors:", data.errors);
    }
  } catch (err) {
    setOpsStatus(err.message, true);
  } finally {
    if (els.opsBreachRetentionImportFile) {
      els.opsBreachRetentionImportFile.value = "";
    }
  }
}

async function downloadOpsBreachRetentionDryRunCsv() {
  if (!opsAuthMe.is_admin) {
    return;
  }
  const file = els.opsBreachRetentionImportFile?.files?.[0];
  if (!file) {
    setOpsStatus("CSV ファイルを選択してください。", true);
    return;
  }
  const formData = new FormData();
  formData.append("file", file, file.name);
  try {
    const res = await fetch(
      `${API_BASE}/api/v1/ops/fleets/breach-history-settings/import?dry_run=true&format=csv${retentionImportChangesOnlyQuery()}`,
      {
        method: "POST",
        headers: getOpsApiHeaders(),
        credentials: "include",
        body: formData,
      }
    );
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new Error(data.detail || `API エラー (${res.status})`);
    }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "breach-history-retention-preview.csv";
    a.click();
    URL.revokeObjectURL(url);
    setOpsStatus("dry-run preview CSV をダウンロードしました。");
  } catch (err) {
    setOpsStatus(err.message, true);
  }
}

function renderOpsBreachRetentionImportPreview(preview, errors) {
  if (!els.opsBreachRetentionImportPreviewTable || !els.opsBreachRetentionImportPreviewTableBody) {
    return;
  }
  els.opsBreachRetentionImportPreviewTableBody.innerHTML = "";
  if (!preview.length) {
    els.opsBreachRetentionImportPreviewTable.classList.add("hidden");
    return;
  }
  const changesOnly = els.opsBreachRetentionPreviewChangesOnly?.checked !== false;
  const changedItems = preview.filter((item) => item.will_change);
  const unchangedItems = preview.filter((item) => !item.will_change);

  function appendPreviewRow(item) {
    const tr = document.createElement("tr");
    const stateClass = item.will_change ? "ops-breach-active" : "";
    tr.innerHTML = `
      <td class="${stateClass}">${item.fleet_name || item.fleet_id}</td>
      <td class="${stateClass}">${item.retention_days != null ? item.retention_days : "—"}</td>
      <td class="${stateClass}">${item.current_retention_days != null ? item.current_retention_days : "—"}</td>
      <td class="${stateClass}">${item.effective_retention_days}</td>
    `;
    els.opsBreachRetentionImportPreviewTableBody.appendChild(tr);
  }

  const itemsToShow = changesOnly ? changedItems : preview;
  for (const item of itemsToShow) {
    appendPreviewRow(item);
  }

  if (changesOnly && unchangedItems.length) {
    const toggleRow = document.createElement("tr");
    toggleRow.className = "ops-breach-retention-preview-toggle-row";
    toggleRow.innerHTML = `<td colspan="4"><button type="button" class="ops-breach-preview-toggle-btn">変更なし ${unchangedItems.length} 件（表示）</button></td>`;
    const btn = toggleRow.querySelector(".ops-breach-preview-toggle-btn");
    btn?.addEventListener("click", () => {
      const insertBefore = toggleRow;
      for (const item of unchangedItems) {
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td>${item.fleet_name || item.fleet_id}</td>
          <td>${item.retention_days != null ? item.retention_days : "—"}</td>
          <td>${item.current_retention_days != null ? item.current_retention_days : "—"}</td>
          <td>${item.effective_retention_days}</td>
        `;
        els.opsBreachRetentionImportPreviewTableBody.insertBefore(tr, insertBefore);
      }
      toggleRow.remove();
    });
    els.opsBreachRetentionImportPreviewTableBody.appendChild(toggleRow);
  }

  if (errors.length) {
    const tr = document.createElement("tr");
    tr.innerHTML = `<td colspan="4" class="ops-breach-active">警告: ${errors.join("; ")}</td>`;
    els.opsBreachRetentionImportPreviewTableBody.appendChild(tr);
  }
  els.opsBreachRetentionImportPreviewTable.classList.remove("hidden");
}

function fleetAlertRulesQueryString() {
  const fleetId = els.opsFleetSelect.value;
  const params = [];
  if (fleetId) {
    params.push(`fleet_id=${fleetId}`);
  }
  if (els.opsFleetAlertRulesBreachingOnly?.checked) {
    params.push("breaching_only=true");
  }
  if (els.opsFleetAlertRulesBreachingFleetsOnly?.checked) {
    params.push("breaching_fleets_only=true");
  }
  const format = els.opsFleetAlertRulesFormat?.value || "yaml";
  params.push(`format=${format}`);
  return `?${params.join("&")}`;
}

function refreshOpsFleetAlertRulesSection() {
  if (!els.opsFleetAlertRulesSection) {
    return;
  }
  const fleetId = els.opsFleetSelect.value;
  if (!fleetId && !opsAuthMe.is_admin) {
    els.opsFleetAlertRulesSection.classList.add("hidden");
    return;
  }
  els.opsFleetAlertRulesSection.classList.remove("hidden");
  if (els.opsFleetAlertRulesBreachingFleetsOnly) {
    els.opsFleetAlertRulesBreachingFleetsOnly.disabled = Boolean(fleetId);
  }
  els.opsFleetAlertRulesStatus.textContent = fleetId
    ? "艦隊スコープのルール雛形をダウンロードできます。"
    : "管理者: 全艦隊または breaching 艦隊のみで出力できます。";
  els.btnOpsFleetAlertRulesApply?.classList.toggle("hidden", !opsAuthMe.is_admin);
  els.btnOpsPrometheusReload?.classList.toggle("hidden", !opsAuthMe.is_admin);
  els.opsPrometheusReloadStatus?.classList.toggle("hidden", !opsAuthMe.is_admin);
  els.opsPrometheusReloadHistoryTable?.classList.toggle("hidden", !opsAuthMe.is_admin);
  if (opsAuthMe.is_admin) {
    refreshOpsPrometheusReloadHistory();
  }
}

async function refreshOpsPrometheusReloadHistory() {
  if (!opsAuthMe.is_admin || !els.opsPrometheusReloadHistoryTableBody) {
    els.opsPrometheusReloadHistoryTable?.classList.add("hidden");
    return;
  }
  try {
    const listing = await apiGet("/api/v1/ops/prometheus/reload/history?limit=20", { ops: true });
    els.opsPrometheusReloadHistoryTableBody.innerHTML = "";
    for (const item of listing.items) {
      const tr = document.createElement("tr");
      const reloadClass = item.reloaded ? "ops-breach-ok" : "ops-breach-active";
      tr.innerHTML = `
        <td>${formatTime(item.enqueued_at)}</td>
        <td>${item.task_id || "—"}</td>
        <td>${item.source}</td>
        <td>${item.state}</td>
        <td class="${reloadClass}">${item.reloaded ? "yes" : "no"}</td>
        <td>${item.message}</td>
      `;
      els.opsPrometheusReloadHistoryTableBody.appendChild(tr);
    }
    els.opsPrometheusReloadHistoryTable?.classList.remove("hidden");
  } catch (err) {
    els.opsPrometheusReloadHistoryTable?.classList.add("hidden");
  }
}

async function saveOpsBreachHistoryRetention() {
  const fleetId = els.opsFleetSelect.value;
  if (!fleetId || !opsAuthMe.is_admin) {
    return;
  }
  const raw = els.opsBreachHistoryRetentionDays?.value?.trim() ?? "";
  const retentionDays = raw === "" ? null : Number(raw);
  if (raw !== "" && (!Number.isInteger(retentionDays) || retentionDays < 1 || retentionDays > 3650)) {
    setOpsStatus("retention 日数は 1〜3650 の整数か空にしてください。", true);
    return;
  }
  try {
    const result = await apiPatch(
      `/api/v1/ops/fleets/${fleetId}/breach-history-settings`,
      { retention_days: retentionDays },
      { ops: true }
    );
    if (els.opsBreachHistoryRetentionDays) {
      els.opsBreachHistoryRetentionDays.placeholder = String(result.effective_retention_days);
    }
    setOpsStatus(`retention 保存済み（effective: ${result.effective_retention_days} 日）`);
    await refreshOpsBreachRetentionAll();
  } catch (err) {
    setOpsStatus(err.message, true);
  }
}

async function refreshOpsBreachRetentionAll() {
  if (!opsAuthMe.is_admin || !els.opsBreachRetentionAllSection) {
    els.opsBreachRetentionAllSection?.classList.add("hidden");
    return;
  }
  els.opsBreachRetentionAllSection.classList.remove("hidden");
  try {
    const listing = await apiGet("/api/v1/ops/fleets/breach-history-settings", { ops: true });
    els.opsBreachRetentionAllStatus.textContent = `${listing.total} 艦隊`;
    els.opsBreachRetentionAllTableBody.innerHTML = "";
    for (const item of listing.items) {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td><input type="checkbox" class="ops-breach-retention-row-select" data-fleet-id="${item.fleet_id}" /></td>
        <td>${item.fleet_name}</td>
        <td>${item.retention_days != null ? item.retention_days : "—"}</td>
        <td>${item.effective_retention_days}</td>
      `;
      els.opsBreachRetentionAllTableBody.appendChild(tr);
    }
    if (els.opsBreachRetentionSelectAll) {
      els.opsBreachRetentionSelectAll.checked = false;
    }
  } catch (err) {
    if (err.message.includes("履歴は無効")) {
      els.opsBreachRetentionAllStatus.textContent = "breach 履歴は無効です。";
      els.opsBreachRetentionAllTableBody.innerHTML = "";
      return;
    }
    els.opsBreachRetentionAllStatus.textContent = err.message;
  }
}

async function saveOpsBreachRetentionBulk() {
  if (!opsAuthMe.is_admin || !els.opsBreachRetentionAllTableBody) {
    return;
  }
  const selected = [...els.opsBreachRetentionAllTableBody.querySelectorAll(".ops-breach-retention-row-select:checked")];
  if (!selected.length) {
    setOpsStatus("一括適用する艦隊を選択してください。", true);
    return;
  }
  const raw = els.opsBreachRetentionBulkDays?.value?.trim() ?? "";
  const retentionDays = raw === "" ? null : Number(raw);
  if (raw !== "" && (!Number.isInteger(retentionDays) || retentionDays < 1 || retentionDays > 3650)) {
    setOpsStatus("retention 日数は 1〜3650 の整数か空にしてください。", true);
    return;
  }
  try {
    const result = await apiPatch(
      "/api/v1/ops/fleets/breach-history-settings/bulk",
      {
        items: selected.map((el) => ({
          fleet_id: el.dataset.fleetId,
          retention_days: retentionDays,
        })),
      },
      { ops: true }
    );
    setOpsStatus(`${result.updated} 艦隊の retention を更新しました。`);
    await refreshOpsBreachRetentionAll();
    await refreshOpsBreachHistory();
  } catch (err) {
    setOpsStatus(err.message, true);
  }
}

async function downloadOpsFleetAlertRules() {
  try {
    const format = els.opsFleetAlertRulesFormat?.value || "yaml";
    const res = await fetch(
      `${API_BASE}/api/v1/ops/prometheus/fleet-alert-rules${fleetAlertRulesQueryString()}`,
      {
        headers: getOpsApiHeaders(),
        credentials: "include",
      }
    );
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new Error(data.detail || `API エラー (${res.status})`);
    }
    const data = await res.json();
    const blob = new Blob([data.content], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    const fleetId = els.opsFleetSelect.value || "all";
    a.download = `fleet-alert-rules-${fleetId}.${format}`;
    a.click();
    URL.revokeObjectURL(url);
    setOpsStatus("アラートルール雛形をダウンロードしました。");
  } catch (err) {
    if (err.message.includes("無効")) {
      els.opsFleetAlertRulesStatus.textContent = "Fleet alert metrics は無効です。";
      return;
    }
    setOpsStatus(err.message, true);
  }
}

async function pollPrometheusReloadTask(taskId, options = {}) {
  const {
    attempt = 0,
    statusEl = els.opsFleetAlertRulesStatus,
    timeoutMessage = "Prometheus reload タスクの確認がタイムアウトしました。",
  } = options;
  const maxAttempts = 15;
  if (!taskId || !statusEl || attempt >= maxAttempts) {
    if (attempt >= maxAttempts && statusEl) {
      statusEl.textContent += " / reload タスク確認タイムアウト";
      setOpsStatus(timeoutMessage, true);
    }
    return;
  }
  try {
    const status = await apiGet(`/api/v1/ops/prometheus/reload/tasks/${taskId}`, { ops: true });
    if (status.state === "SUCCESS" || status.state === "FAILURE") {
      const base = statusEl.textContent.replace(/ \/ reload.*$/, "");
      const reloadNote = status.reloaded
        ? " / reload OK (Celery)"
        : ` / reload: ${status.message}`;
      statusEl.textContent = `${base}${reloadNote}`;
      setOpsStatus(
        status.reloaded ? "Prometheus reload が完了しました。" : status.message,
        !status.reloaded
      );
      refreshOpsPrometheusReloadHistory();
      return;
    }
    window.setTimeout(
      () => pollPrometheusReloadTask(taskId, { ...options, attempt: attempt + 1 }),
      2000
    );
  } catch (err) {
    setOpsStatus(err.message, true);
  }
}

async function triggerOpsPrometheusReload() {
  if (!opsAuthMe.is_admin) {
    return;
  }
  try {
    const res = await fetch(`${API_BASE}/api/v1/ops/prometheus/reload`, {
      method: "POST",
      headers: getOpsApiHeaders(),
      credentials: "include",
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(data.detail || `API エラー (${res.status})`);
    }
    const reloadNote = data.reload_queued
      ? "reload をキューに登録しました。"
      : data.reloaded
        ? "reload OK"
        : data.message;
    if (els.opsPrometheusReloadStatus) {
      els.opsPrometheusReloadStatus.textContent = reloadNote;
      els.opsPrometheusReloadStatus.classList.remove("hidden");
    }
    setOpsStatus(reloadNote, !data.reloaded && !data.reload_queued);
    await refreshOpsPrometheusReloadHistory();
    if (data.reload_queued && data.reload_task_id) {
      pollPrometheusReloadTask(data.reload_task_id, {
        statusEl: els.opsPrometheusReloadStatus,
      });
    }
  } catch (err) {
    setOpsStatus(err.message, true);
  }
}

async function applyOpsFleetAlertRules() {
  if (!opsAuthMe.is_admin) {
    return;
  }
  try {
    const res = await fetch(
      `${API_BASE}/api/v1/ops/prometheus/fleet-alert-rules/apply${fleetAlertRulesQueryString()}`,
      {
        method: "POST",
        headers: getOpsApiHeaders(),
        credentials: "include",
      }
    );
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(data.detail || `API エラー (${res.status})`);
    }
    if (data.applied) {
      const reloadNote = data.reload_queued
        ? " / reload をキューに登録"
        : data.reloaded
          ? " / reload OK"
          : data.reload_message
            ? ` / reload: ${data.reload_message}`
            : "";
      els.opsFleetAlertRulesStatus.textContent = `${data.message} (${data.path})${reloadNote}`;
      const statusMsg = data.reload_queued
        ? "ルールを適用し Prometheus reload をキューに登録しました。"
        : data.reloaded
          ? "ルールを適用し Prometheus reload しました。"
          : "ルールを適用しました。";
      setOpsStatus(statusMsg, !data.reloaded && !data.reload_queued && Boolean(data.reload_message));
      if (data.reload_queued && data.reload_task_id) {
        pollPrometheusReloadTask(data.reload_task_id, {
          statusEl: els.opsFleetAlertRulesStatus,
        });
      }
    } else {
      els.opsFleetAlertRulesStatus.textContent = data.message;
      setOpsStatus(data.message, true);
    }
  } catch (err) {
    if (err.message.includes("無効")) {
      els.opsFleetAlertRulesStatus.textContent = "Fleet alert metrics は無効です。";
      return;
    }
    setOpsStatus(err.message, true);
  }
}

async function refreshOpsSilences() {
  const fleetId = els.opsFleetSelect.value;
  if (!fleetId || !els.opsSilencesSection) {
    els.opsSilencesSection?.classList.add("hidden");
    return;
  }
  els.opsSilencesSection.classList.remove("hidden");
  try {
    const listing = await apiGet(
      `/api/v1/ops/prometheus/alertmanager/silences?fleet_id=${fleetId}`,
      { ops: true }
    );
    els.opsSilencesStatus.textContent = `${listing.total} 件の active silence`;
    els.opsSilencesTableBody.innerHTML = "";
    if (els.opsSilencesSelectAll) {
      els.opsSilencesSelectAll.checked = false;
    }
    for (const item of listing.items) {
      const tr = document.createElement("tr");
      tr.dataset.silenceId = item.silence_id;
      tr.innerHTML = `
        <td class="ops-silences-select-col">
          <input type="checkbox" class="ops-silence-select" value="${item.silence_id}" />
        </td>
        <td>${item.alertname || "（艦隊全体）"}</td>
        <td>${formatTime(item.ends_at)}</td>
        <td>${item.comment || "—"}</td>
        <td class="ops-silences-actions"></td>
      `;
      const checkbox = tr.querySelector(".ops-silence-select");
      checkbox.addEventListener("change", updateOpsSilencesDeleteSelectedButton);
      const actions = tr.querySelector(".ops-silences-actions");
      const delBtn = document.createElement("button");
      delBtn.type = "button";
      delBtn.textContent = "削除";
      delBtn.addEventListener("click", () => deleteOpsSilence(item.silence_id));
      actions.appendChild(delBtn);
      els.opsSilencesTableBody.appendChild(tr);
    }
    els.opsSilencesTable.classList.toggle("hidden", listing.items.length === 0);
    updateOpsSilencesDeleteSelectedButton();
  } catch (err) {
    if (err.message.includes("無効")) {
      els.opsSilencesStatus.textContent = "Alertmanager silences は無効です。";
      els.opsSilencesTable.classList.add("hidden");
      return;
    }
    els.opsSilencesStatus.textContent = err.message;
  }
}

async function createOpsSilence() {
  const fleetId = els.opsFleetSelect.value;
  if (!fleetId) {
    setOpsStatus("艦隊を選択してください。", true);
    return;
  }
  const alertname = els.opsSilenceAlertname.value || null;
  const duration_hours = parseFloat(els.opsSilenceHours.value) || 4;
  const comment = els.opsSilenceComment.value.trim() || null;
  try {
    const payload = { fleet_id: fleetId, duration_hours, comment };
    if (alertname) {
      payload.alertname = alertname;
    }
    await apiPost("/api/v1/ops/prometheus/alertmanager/silences", payload, { ops: true });
    await refreshOpsSilences();
    setOpsStatus("silence を作成しました。");
  } catch (err) {
    setOpsStatus(err.message, true);
  }
}

async function deleteOpsSilence(silenceId) {
  try {
    await apiDelete(`/api/v1/ops/prometheus/alertmanager/silences/${silenceId}`, { ops: true });
    await refreshOpsSilences();
    setOpsStatus("silence を削除しました。");
  } catch (err) {
    setOpsStatus(err.message, true);
  }
}

async function deleteAllOpsSilences() {
  const fleetId = els.opsFleetSelect.value;
  if (!fleetId) {
    return;
  }
  if (!confirm("この艦隊の active silence をすべて削除しますか？")) {
    return;
  }
  try {
    const result = await apiDelete(
      `/api/v1/ops/prometheus/alertmanager/silences?fleet_id=${fleetId}`,
      { ops: true }
    );
    await refreshOpsSilences();
    setOpsStatus(result.message);
  } catch (err) {
    setOpsStatus(err.message, true);
  }
}

async function deleteSelectedOpsSilences() {
  const checked = els.opsSilencesTableBody?.querySelectorAll(
    "input.ops-silence-select:checked"
  );
  if (!checked || checked.length === 0) {
    setOpsStatus("削除する silence を選択してください。", true);
    return;
  }
  const silenceIds = Array.from(checked).map((el) => el.value);
  if (!confirm(`${silenceIds.length} 件の silence を削除しますか？`)) {
    return;
  }
  try {
    const result = await apiPost(
      "/api/v1/ops/prometheus/alertmanager/silences/bulk-delete",
      { silence_ids: silenceIds },
      { ops: true }
    );
    await refreshOpsSilences();
    setOpsStatus(result.message);
  } catch (err) {
    setOpsStatus(err.message, true);
  }
}

async function refreshOpsDashboard() {
  const fleetId = els.opsFleetSelect.value;
  if (!ensureOpsAuthenticated()) {
    setOpsStatus("SSO ログインまたは API Key を設定してください。", true);
    return;
  }
  if (!fleetId) {
    els.opsSilencesSection?.classList.add("hidden");
    els.opsBreachStatesSection?.classList.add("hidden");
    els.opsBreachHistorySection?.classList.add("hidden");
    if (opsAuthMe.is_admin) {
      await refreshOpsBreachStatesAll();
      await refreshOpsBreachHistoryAll();
      await refreshOpsBreachRetentionAll();
      refreshOpsFleetAlertRulesSection();
      setOpsStatus("艦隊を選択するか、全艦隊 breach 状態を確認してください。");
    } else {
      els.opsBreachStatesAllSection?.classList.add("hidden");
      els.opsBreachHistoryAllSection?.classList.add("hidden");
      els.opsBreachRetentionAllSection?.classList.add("hidden");
      els.opsFleetAlertRulesSection?.classList.add("hidden");
      setOpsStatus("艦隊を選択してください。", true);
    }
    return;
  }
  try {
    const [summary, sla, apiHistory] = await Promise.all([
      apiGet(`/api/v1/ops/fleets/${fleetId}/summary`, { ops: true }),
      apiGet(`/api/v1/ops/sla?fleet_id=${fleetId}`, { ops: true }),
      apiGet(`/api/v1/ops/sla/api-history?days=7&fleet_id=${fleetId}`, { ops: true }),
    ]);
    const slaItem = sla.items && sla.items.length ? sla.items[0] : null;
    els.opsSummary.innerHTML = `
      <strong>${summary.fleet_name}</strong><br/>
      open: ${summary.open_count} /
      escalated: ${summary.escalated_count ?? 0} /
      ack: ${summary.acknowledged_count} /
      対策計画: ${summary.mitigation_planned_count} /
      closed: ${summary.closed_count}<br/>
      open risk: high ${summary.open_high_count ?? 0} /
      medium ${summary.open_medium_count ?? 0} /
      low ${summary.open_low_count ?? 0}<br/>
      最新 Run: ${summary.latest_run_status ?? "—"} ${formatTime(summary.latest_run_finished_at)}<br/>
      ${formatSlaLine(slaItem)}<br/>
      ${formatApiSloLine(sla, slaItem)}<br/>
      ${formatApiSloHistoryLine(apiHistory, slaItem)}
    `;
    const statusQ = els.opsStatusFilter.value;
    const path = statusQ
      ? `/api/v1/ops/alerts?fleet_id=${fleetId}&status=${statusQ}`
      : `/api/v1/ops/alerts?fleet_id=${fleetId}`;
    const listing = await apiGet(path, { ops: true });
    els.opsAlertTableBody.innerHTML = "";
    for (const a of listing.items) {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>${a.satellite_name}<br/><small>NORAD ${a.satellite_norad_id}</small></td>
        <td>${a.debris_name}<br/><small>NORAD ${a.debris_norad_id}</small></td>
        <td>${formatTime(a.tca)}</td>
        <td>${formatOpsPcHtml(a)}</td>
        <td>${opsStatusCell(a)}</td>
        <td class="ops-actions" data-alert-id="${a.id}"></td>
      `;
      const actions = tr.querySelector(".ops-actions");
      const commentInput = document.createElement("input");
      commentInput.type = "text";
      commentInput.className = "ops-comment-input";
      commentInput.placeholder = "コメント（任意）";
      commentInput.value = a.comment || "";
      actions.appendChild(commentInput);

      const mitControls = document.createElement("div");
      mitControls.className = "ops-mitigation-controls";
      const dirSelect = document.createElement("select");
      dirSelect.className = "ops-mitigation-direction";
      for (const dir of ["prograde", "retrograde", "normal"]) {
        const opt = document.createElement("option");
        opt.value = dir;
        opt.textContent = dir;
        dirSelect.appendChild(opt);
      }
      const deltaInput = document.createElement("input");
      deltaInput.type = "number";
      deltaInput.className = "ops-mitigation-delta";
      deltaInput.min = "0.001";
      deltaInput.step = "0.001";
      deltaInput.value = "0.01";
      deltaInput.title = "Δv (m/s)";
      const sweepMin = document.createElement("input");
      sweepMin.type = "number";
      sweepMin.className = "ops-mitigation-sweep-min";
      sweepMin.min = "0.001";
      sweepMin.step = "0.01";
      sweepMin.value = "0.01";
      sweepMin.title = "スイープ min Δv";
      const sweepMax = document.createElement("input");
      sweepMax.type = "number";
      sweepMax.className = "ops-mitigation-sweep-max";
      sweepMax.min = "0.001";
      sweepMax.step = "0.01";
      sweepMax.value = "0.10";
      sweepMax.title = "スイープ max Δv";
      mitControls.appendChild(dirSelect);
      mitControls.appendChild(deltaInput);
      mitControls.appendChild(sweepMin);
      mitControls.appendChild(sweepMax);
      actions.appendChild(mitControls);

      const pcRefineBtn = document.createElement("button");
      pcRefineBtn.type = "button";
      pcRefineBtn.className = "ops-pc-refine-btn";
      pcRefineBtn.textContent = "Pc 再計算";
      pcRefineBtn.addEventListener("click", async () => {
        try {
          pcRefineBtn.disabled = true;
          const result = await apiPost(
            `/api/v1/ops/alerts/${a.id}/pc-refine`,
            {},
            { ops: true }
          );
          const pcCell = tr.children[3];
          pcCell.innerHTML = formatOpsPcHtml({
            ...a,
            latest_pc_refinement: result,
          });
          showPcRefinementResult(actions, result);
          const methodLabel =
            result.pc_method === "cdm_rtn" ? "CDM RTN" : "TLE RTN";
          setOpsStatus(
            `Pc 再計算完了 — screening ${formatPc(result.pc_screening)} → refined ${formatPc(result.pc_refined)} (${methodLabel})`
          );
        } catch (err) {
          setOpsStatus(err.message, true);
        } finally {
          pcRefineBtn.disabled = false;
        }
      });
      actions.appendChild(pcRefineBtn);

      if (a.latest_pc_refinement) {
        showPcRefinementResult(actions, a.latest_pc_refinement);
      }

      const transitions = (a.allowed_next_statuses || []).map((status) => ({
        label: OPS_TRANSITION_LABELS[status] || status,
        status,
      }));
      for (const t of transitions) {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.textContent = t.label;
        btn.addEventListener("click", async () => {
          try {
            await apiPatch(
              `/api/v1/ops/alerts/${a.id}`,
              {
                status: t.status,
                comment: commentInput.value || null,
              },
              { ops: true }
            );
            await refreshOpsDashboard();
            setOpsStatus(`${t.label} しました。`);
          } catch (err) {
            setOpsStatus(err.message, true);
          }
        });
        actions.appendChild(btn);
      }
      if (a.latest_mitigation_preview) {
        const p = a.latest_mitigation_preview;
        const latestDiv = document.createElement("div");
        latestDiv.className = "ops-mitigation-result";
        latestDiv.innerHTML = formatMitigationPreviewLabel(p);
        actions.appendChild(latestDiv);
      }
      const mitBtn = document.createElement("button");
      mitBtn.type = "button";
      mitBtn.className = "ops-mitigation-btn";
      mitBtn.textContent = "回避試算";
      mitBtn.addEventListener("click", async () => {
        try {
          mitBtn.disabled = true;
          const result = await apiPost(
            `/api/v1/ops/alerts/${a.id}/mitigation-preview`,
            {
              direction: dirSelect.value,
              delta_v_ms: parseFloat(deltaInput.value) || 0.01,
            },
            { ops: true }
          );
          showMitigationResult(actions, result);
          setOpsStatus(
            `回避試算完了 — miss ${result.before_miss_distance_km.toFixed(3)} → ${result.after_miss_distance_km.toFixed(3)} km（Δv ${result.delta_v_ms} m/s ${result.direction}）`
          );
        } catch (err) {
          setOpsStatus(err.message, true);
        } finally {
          mitBtn.disabled = false;
        }
      });
      actions.appendChild(mitBtn);

      const sweepBtn = document.createElement("button");
      sweepBtn.type = "button";
      sweepBtn.className = "ops-mitigation-btn";
      sweepBtn.textContent = "Δv スイープ";
      sweepBtn.addEventListener("click", async () => {
        try {
          sweepBtn.disabled = true;
          const minV = parseFloat(sweepMin.value) || 0.01;
          const maxV = parseFloat(sweepMax.value) || 0.1;
          const stepV = 0.01;
          const result = await apiPost(
            `/api/v1/ops/alerts/${a.id}/mitigation-sweep`,
            {
              direction: dirSelect.value,
              delta_v_min_ms: minV,
              delta_v_max_ms: maxV,
              delta_v_step_ms: stepV,
            },
            { ops: true }
          );
          if (result.best) {
            showMitigationResult(actions, result.best, { best: true });
          }
          setOpsStatus(`Δv スイープ完了 — ${result.total} 試算、best Δv ${result.best?.delta_v_ms ?? "—"} m/s`);
        } catch (err) {
          setOpsStatus(err.message, true);
        } finally {
          sweepBtn.disabled = false;
        }
      });
      actions.appendChild(sweepBtn);

      if (a.status === "acknowledged") {
        const planBtn = document.createElement("button");
        planBtn.type = "button";
        planBtn.className = "ops-mitigation-btn ops-mitigation-plan-btn";
        planBtn.textContent = "試算→対策計画";
        planBtn.addEventListener("click", async () => {
          try {
            planBtn.disabled = true;
            await apiPost(
              `/api/v1/ops/alerts/${a.id}/mitigation-plan`,
              { comment: commentInput.value || null },
              { ops: true }
            );
            await refreshOpsDashboard();
            setOpsStatus("試算結果を含めて対策計画へ遷移しました。");
          } catch (err) {
            setOpsStatus(err.message, true);
          } finally {
            planBtn.disabled = false;
          }
        });
        actions.appendChild(planBtn);
      }

      els.opsAlertTableBody.appendChild(tr);
    }
    els.opsAlertTable.classList.toggle("hidden", listing.items.length === 0);
    setOpsStatus(`${listing.total} 件のアラートを表示中。`);
    await Promise.all([
      refreshOpsBreachStates(),
      refreshOpsBreachStatesAll(),
      refreshOpsBreachHistory(),
      refreshOpsBreachHistoryAll(),
      refreshOpsBreachRetentionAll(),
      refreshOpsFleetAlertRulesSection(),
      refreshOpsSilences(),
    ]);
  } catch (err) {
    setOpsStatus(err.message, true);
  }
}

async function apiPost(path, body, { ops = false } = {}) {
  let lastErr = null;
  const headers = ops
    ? getOpsApiHeaders({ "Content-Type": "application/json" })
    : { "Content-Type": "application/json" };
  for (let attempt = 0; attempt < 2; attempt++) {
    try {
      const res = await fetch(`${API_BASE}${path}`, {
        method: "POST",
        headers,
        body: JSON.stringify(body),
        credentials: ops ? "include" : "same-origin",
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        const detail = data.detail;
        const msg =
          typeof detail === "string"
            ? detail
            : Array.isArray(detail)
              ? detail.map((d) => d.msg).join(", ")
              : `API エラー (${res.status})`;
        throw new Error(msg);
      }
      return data;
    } catch (err) {
      if (err instanceof Error && err.message.startsWith("API エラー")) {
        throw err;
      }
      lastErr = err;
      if (attempt === 0) {
        await new Promise((resolve) => setTimeout(resolve, 2000));
      }
    }
  }
  throw lastErr instanceof Error ? lastErr : new Error("API 接続に失敗しました。");
}

function formatTime(iso) {
  if (!iso) return "—";
  return iso.replace("T", " ").replace("Z", " UTC");
}

function formatPc(pc) {
  if (pc == null) return "—";
  if (pc >= 0.0001) return pc.toExponential(2);
  if (pc === 0) return "0";
  return pc.toExponential(1);
}

function formatOpsPcHtml(alert) {
  const screening = formatPc(alert.pc);
  const ref = alert.latest_pc_refinement;
  if (!ref) {
    return `<span class="ops-pc-screening">${screening}</span>`;
  }
  const methodLabel = ref.pc_method === "cdm_rtn" ? "CDM RTN" : "TLE RTN";
  const autoBadge =
    ref.trigger_source === "screening_auto"
      ? ' <span class="ops-pc-auto">auto</span>'
      : "";
  const propagatedBadge =
    ref.covariance_source === "tle_rtn_propagated"
      ? ' <span class="ops-pc-propagated">propagated σ</span>'
      : "";
  const escalatedBadge =
    alert.escalated && alert.status !== "escalated"
      ? '<br/><span class="ops-pc-escalated">ESCALATED</span>'
      : "";
  return (
    `<span class="ops-pc-screening">${screening}</span>` +
    `<br/><span class="ops-pc-refinement">→ ${formatPc(ref.pc_refined)} (${methodLabel})${autoBadge}${propagatedBadge}</span>` +
    escalatedBadge
  );
}

function showPcRefinementResult(container, refinement) {
  const existing = container.querySelector(".ops-pc-refinement-result");
  if (existing) existing.remove();
  const div = document.createElement("div");
  div.className = "ops-pc-refinement-result";
  const methodLabel =
    refinement.pc_method === "cdm_rtn" ? "CDM RTN" : "TLE RTN";
  const propagatedBadge =
    refinement.covariance_source === "tle_rtn_propagated" ? " propagated σ" : "";
  div.textContent = `Pc refined: ${formatPc(refinement.pc_screening)} → ${formatPc(refinement.pc_refined)} (${methodLabel}${propagatedBadge})`;
  container.appendChild(div);
}

function parseConstellationBlocks(text) {
  const blocks = text.split("---").map((b) => b.trim()).filter(Boolean);
  return blocks.map((block, i) => {
    const firstLine = block.split("\n")[0].trim();
    const name = firstLine.startsWith("1 ") ? `SAT-${i + 1}` : firstLine;
    return { name, tle: block };
  });
}

function setOpsStatus(msg, isError = false) {
  els.opsStatusMsg.textContent = msg;
  els.opsStatusMsg.classList.toggle("error", isError);
}

function switchMode(mode) {
  currentMode = mode;
  for (const tab of [els.tabSingle, els.tabConstellation, els.tabCdm, els.tabAlerts, els.tabOps]) {
    tab.classList.toggle("active", tab.dataset.mode === mode);
  }
  els.panelSingle.classList.toggle("hidden", mode !== "single");
  els.panelConstellation.classList.toggle("hidden", mode !== "constellation");
  els.panelCdm.classList.toggle("hidden", mode !== "cdm");
  els.panelAlerts.classList.toggle("hidden", mode !== "alerts");
  els.panelOps.classList.toggle("hidden", mode !== "ops");
  if (mode === "alerts" && !els.alertSatTle.value.trim()) {
    els.alertSatTle.value = els.tleInput.value.trim() || ISS_SAMPLE;
  }
  if (mode === "ops") {
    refreshOpsAuthStatus().then(() => loadOpsFleets());
  }
}

function syncAnisotropicCheckbox(advancedEl, anisotropicEl) {
  const enabled = advancedEl.checked;
  anisotropicEl.disabled = !enabled;
  if (!enabled) {
    anisotropicEl.checked = false;
  }
}

function formatWebhookStatus(webhook) {
  if (!webhook) return "";
  if (webhook.sent) {
    return ` / Webhook: ${webhook.alert_count} 件送信`;
  }
  if (webhook.degraded) {
    return ` / Webhook 失敗: ${webhook.message}`;
  }
  return ` / Webhook: ${webhook.message}`;
}

function formatAnalysisMeta(data) {
  const filterNote = data.altitude_prefilter_applied ? "高度帯フィルタ ON / " : "";
  const cdmNote =
    data.spacetrack_cdm_records_fetched > 0 || data.spacetrack_cdm_events_merged > 0
      ? `Space-Track CDM: ${data.spacetrack_cdm_events_merged} 件マージ / `
      : "";
  return (
    `${filterNote}${cdmNote}${data.conjunctions.length} 件 / 候補 ${data.debris_candidates_count} / ` +
    `カタログ ${data.debris_catalog_count} / ${data.computation_time_ms} ms / ` +
    `TLE: ${data.tle_provider || "celestrak"}`
  );
}

function renderConjunctions(data) {
  els.scanMeta.textContent = formatAnalysisMeta(data);
  els.conjunctionList.innerHTML = "";

  if (data.conjunctions.length === 0) {
    els.conjunctionList.innerHTML =
      "<li>指定閾値以内の接近は検出されませんでした。デモ用に閾値を 50 km などに広げて再試行できます。</li>";
    return;
  }

  for (const c of data.conjunctions) {
    const pcLine =
      c.pc_method_used === "encounter_advanced"
        ? `Pc: ${formatPc(c.pc)} (Alfriend) / Foster: ${formatPc(c.pc_foster)}` +
          (c.pc_monte_carlo != null ? ` / MC: ${formatPc(c.pc_monte_carlo)}` : "") +
          (c.covariance_source === "tle_rtn_anisotropic" ? " (非等方 σ)" : "") +
          (c.covariance_source === "tle_rtn_propagated" ? " (伝播 σ)" : "") +
          (c.sigma_source === "cdm_covariance" ? " (CDM σ)" : "")
        : `Pc: ${formatPc(c.pc)} (Foster)` +
          (c.sigma_source === "cdm_covariance" ? " (CDM σ)" : "");
    const li = document.createElement("li");
    li.className = `risk-${c.risk_level}`;
    li.innerHTML = `
      <strong>${c.debris_name}</strong> (NORAD ${c.debris_norad_id})<br />
      TCA: ${formatTime(c.tca)}<br />
      距離: ${c.miss_distance_km.toFixed(2)} km /
      ${pcLine} /
      相対速度: ${c.relative_velocity_kms.toFixed(2)} km/s /
      <span class="risk-${c.risk_level}">${c.risk_level}</span>
      <br /><button type="button" class="btn-export-cdm">CDM エクスポート</button>
    `;
    li.querySelector(".btn-export-cdm").addEventListener("click", (e) => {
      e.stopPropagation();
      exportConjunctionCdm(c);
    });
    li.addEventListener("click", () => selectConjunction(c, li));
    els.conjunctionList.appendChild(li);
  }
}

async function exportConjunctionCdm(conjunction) {
  if (!lastSatelliteTle) {
    setStatus("衛星 TLE がありません。先に接近解析を実行してください。", true);
    return;
  }
  try {
    const data = await apiPost("/api/v1/cdm/export", {
      satellite_tle: lastSatelliteTle,
      debris_tle: conjunction.debris_tle,
      tca: conjunction.tca,
      miss_distance_km: conjunction.miss_distance_km,
      relative_velocity_kms: conjunction.relative_velocity_kms,
      pc: conjunction.pc,
    });
    await navigator.clipboard.writeText(data.cdm_text);
    setStatus("CDM KVN をクリップボードにコピーしました。");
  } catch (err) {
    setStatus(err.message, true);
  }
}

function renderCdmCompareResult(data, targetEl) {
  const missDelta =
    data.delta_miss_km != null
      ? `${data.delta_miss_km >= 0 ? "+" : ""}${data.delta_miss_km.toFixed(3)} km`
      : "—";
  const pcRatio =
    data.delta_pc_ratio != null
      ? `${(data.delta_pc_ratio * 100).toFixed(1)}% (CAS/CDM)`
      : "—";

  const sigmaLabels = {
    manual: "手動指定",
    cdm_covariance: "CDM 共分散",
    tle_age: "TLE 経過日数推定",
  };
  const sigmaHighlight =
    data.sigma_source === "cdm_covariance"
      ? ' <span class="risk-medium">（CDM RTN σ 適用）</span>'
      : "";
  const sigmaLabel = sigmaLabels[data.sigma_source] || data.sigma_source;

  const pm = data.pc_methods || {};
  const pcTableRows = [
    ["CDM（外部）", data.cdm.pc],
    ["Foster", pm.foster],
    ["Alfriend", pm.alfriend],
    ["Monte Carlo", pm.monte_carlo],
  ]
    .map(
      ([label, val]) =>
        `<tr><td>${label}</td><td>${val != null ? formatPc(val) : "—"}</td></tr>`
    )
    .join("");

  const methodLabel =
    data.pc_method_used === "encounter_advanced"
      ? "encounter plane（Alfriend 優先）"
      : "Foster のみ";

  targetEl.innerHTML = `
    <div class="compare-grid">
      <div class="compare-col">
        <h3>CDM（外部）</h3>
        <div>TCA: ${formatTime(data.cdm.tca)}</div>
        <div>Miss distance: ${data.cdm.miss_distance_km?.toFixed(3) ?? "—"} km</div>
        <div>Pc: ${formatPc(data.cdm.pc)}</div>
        <div>相対速度: ${data.cdm.relative_velocity_kms?.toFixed(3) ?? "—"} km/s</div>
      </div>
      <div class="compare-col">
        <h3>CAS 計算（${methodLabel}）</h3>
        <div>TCA: ${formatTime(data.cas.tca)}</div>
        <div>Miss distance: ${data.cas.miss_distance_km?.toFixed(3) ?? "—"} km</div>
        <div>Pc (primary): ${formatPc(data.cas.pc)}</div>
        <div>相対速度: ${data.cas.relative_velocity_kms?.toFixed(3) ?? "—"} km/s</div>
        <div>σ: ${data.cas_sigma_km?.toFixed(4) ?? "—"} km (${sigmaLabel})${sigmaHighlight}</div>
        ${
          data.encounter_miss_km != null
            ? `<div>Encounter |b|: ${data.encounter_miss_km.toFixed(3)} km</div>`
            : ""
        }
      </div>
    </div>
    <table class="pc-methods-table">
      <thead><tr><th>方式</th><th>Pc</th></tr></thead>
      <tbody>${pcTableRows}</tbody>
    </table>
    <div class="compare-delta">
      <strong>差分:</strong> Miss Δ = ${missDelta} / Pc 比 = ${pcRatio}
    </div>
  `;
  targetEl.classList.remove("hidden");
}

async function selectConjunction(conjunction, liEl) {
  selectedConjunction = conjunction;
  document.querySelectorAll("#conjunction-list li").forEach((el) => {
    el.classList.remove("selected");
  });
  liEl.classList.add("selected");

  els.maneuverSection.classList.remove("hidden");
  els.selectedDebris.textContent = `選択: ${conjunction.debris_name} (NORAD ${conjunction.debris_norad_id})`;
  els.maneuverResult.textContent = "";
  setStatus("軌道を読み込み中...");

  try {
    const [satOrbit, debOrbit] = await Promise.all([
      apiPost("/api/v1/orbit", { tle: lastSatelliteTle, duration_days: 7, step_minutes: 5 }),
      apiPost("/api/v1/orbit", { tle: conjunction.debris_tle, duration_days: 7, step_minutes: 5 }),
    ]);

    const tcaPos = getTcaPositionFromOrbits(
      satOrbit.points,
      debOrbit.points,
      conjunction.tca
    );

    showOrbits({
      satellite: satOrbit,
      debris: debOrbit,
      tcaTime: conjunction.tca,
      tcaPositionKm: tcaPos,
    });
    setStatus("3D 表示を更新しました。");
  } catch (err) {
    setStatus(err.message, true);
  }
}

async function runScan() {
  const tle = els.tleInput.value.trim();
  if (!tle) {
    setStatus("TLE を入力してください。", true);
    return;
  }

  lastSatelliteTle = tle;
  selectedConjunction = null;
  els.maneuverSection.classList.add("hidden");
  els.conjunctionList.innerHTML = "";
  els.scanMeta.textContent = "";
  setStatus("接近解析を実行中（数十秒かかる場合があります）...");
  els.btnScan.disabled = true;

  try {
    const threshold = parseFloat(els.thresholdKm.value) || 5.0;
    const sigmaRaw = els.sigmaKm.value.trim();
    const payload = {
      tle,
      duration_days: 7,
      threshold_km: threshold,
      step_minutes: 1,
      use_advanced_pc: els.useAdvancedPc.checked,
      use_altitude_prefilter: els.useAltitudePrefilter.checked,
      notify_webhook: els.notifyWebhook.checked,
    };
    const cdmText = els.scanCdmInput.value.trim();
    if (cdmText) {
      payload.cdm_text = cdmText;
    }
    if (els.applyCdmCovariance.checked) {
      payload.apply_cdm_covariance = true;
    }
    if (els.autoSpacetrackCdm.checked) {
      payload.auto_spacetrack_cdm = true;
      payload.use_advanced_pc = true;
      els.useAdvancedPc.checked = true;
    }
    if (els.useAdvancedPc.checked) {
      payload.use_anisotropic_cov = els.useAnisotropicCov.checked;
    }
    if (sigmaRaw) {
      payload.sigma_km = parseFloat(sigmaRaw);
    }
    const data = await apiPost("/api/v1/conjunctions", payload);
    renderConjunctions(data);
    setStatus(`解析完了（${data.computation_time_ms} ms）${formatWebhookStatus(data.webhook)}`);
  } catch (err) {
    setStatus(err.message, true);
  } finally {
    els.btnScan.disabled = false;
  }
}

async function runBatchScan() {
  const text = els.constellationInput.value.trim();
  if (!text) {
    setBatchStatus("TLE を入力してください。", true);
    return;
  }

  const satellites = parseConstellationBlocks(text);
  if (satellites.length > 25) {
    setBatchStatus("衛星数は最大 25 件です。", true);
    return;
  }

  selectedConjunction = null;
  els.maneuverSection.classList.add("hidden");
  els.conjunctionList.innerHTML = "";
  els.scanMeta.textContent = "";
  els.satelliteSelectWrap.classList.add("hidden");
  els.batchSummary.textContent = "";
  setBatchStatus(`一括解析中（${satellites.length} 衛星）...`);
  els.btnBatchScan.disabled = true;

  try {
    const threshold = parseFloat(els.batchThresholdKm.value) || 50.0;
    const payload = {
      satellites,
      duration_days: 7,
      threshold_km: threshold,
      step_minutes: 1,
      use_advanced_pc: els.batchUseAdvancedPc.checked,
      use_altitude_prefilter: els.batchUseAltitudePrefilter.checked,
      notify_webhook: els.batchNotifyWebhook.checked,
    };
    if (els.batchUseAdvancedPc.checked) {
      payload.use_anisotropic_cov = els.batchUseAnisotropicCov.checked;
    }
    if (els.batchAutoSpacetrackCdm.checked) {
      payload.auto_spacetrack_cdm = true;
      payload.use_advanced_pc = true;
      els.batchUseAdvancedPc.checked = true;
    }
    const data = await apiPost("/api/v1/conjunctions/batch", payload);

    batchResults = data.results.map((r, i) => ({
      ...r,
      tle: satellites[i].tle,
    }));

    const s = data.summary;
    els.batchSummary.textContent =
      `全 ${s.satellite_count} 衛星 / 合計 ${s.total_events} 件 / ` +
      `最高 Pc = ${formatPc(s.highest_pc)}` +
      (s.highest_pc_satellite
        ? `（${s.highest_pc_satellite} vs ${s.highest_pc_debris || "—"}）`
        : "") +
      (s.spacetrack_cdm_events_merged > 0
        ? ` / Space-Track CDM: ${s.spacetrack_cdm_events_merged} 件マージ（${s.spacetrack_cdm_satellites_with_merge} 衛星）`
        : "") +
      (data.parallel
        ? ` / 並列 ${data.worker_count} workers`
        : "");

    els.satelliteSelect.innerHTML = "";
    batchResults.forEach((r, i) => {
      const opt = document.createElement("option");
      opt.value = String(i);
      opt.textContent =
        `${r.satellite.name} (${r.conjunctions.length} 件, 候補 ${r.debris_candidates_count}, ${r.computation_time_ms} ms)`;
      els.satelliteSelect.appendChild(opt);
    });
    els.satelliteSelectWrap.classList.remove("hidden");

    if (batchResults.length > 0) {
      showBatchSatellite(0);
    }
    setBatchStatus(`一括解析完了（${data.computation_time_ms} ms）${formatWebhookStatus(data.webhook)}`);
  } catch (err) {
    setBatchStatus(err.message, true);
  } finally {
    els.btnBatchScan.disabled = false;
  }
}

function showBatchSatellite(index) {
  const result = batchResults[index];
  if (!result) return;
  lastSatelliteTle = result.tle;
  renderConjunctions(result);
}

async function runWebhookTest() {
  els.btnWebhookTest.disabled = true;
  setStatus("Webhook テスト送信中...");
  try {
    const data = await apiPost("/api/v1/alerts/webhook/test", {});
    setStatus(
      data.sent
        ? `Webhook テスト成功: ${data.message}`
        : `Webhook: ${data.message}`,
      data.degraded
    );
  } catch (err) {
    setStatus(err.message, true);
  } finally {
    els.btnWebhookTest.disabled = false;
  }
}

function transferCdmToScan() {
  const cdmText = els.cdmInput.value.trim();
  const satTle = els.cdmSatTle.value.trim();
  if (!cdmText) {
    setCdmStatus("CDM テキストを入力してください。", true);
    return;
  }
  els.scanCdmInput.value = cdmText;
  els.applyCdmCovariance.checked = true;
  if (satTle) {
    els.tleInput.value = satTle;
  }
  switchMode("single");
  setStatus("CDM を単一衛星解析に引き渡しました。「接近解析」を実行してください。");
}

async function runCdmCompare() {
  const cdmText = els.cdmInput.value.trim();
  const satTle = els.cdmSatTle.value.trim();
  const debTle = els.cdmDebTle.value.trim();

  if (!cdmText || !satTle || !debTle) {
    setCdmStatus("CDM と TLE ペアを入力してください。", true);
    return;
  }

  els.btnCdmCompare.disabled = true;
  els.cdmResult.classList.add("hidden");
  setCdmStatus("CDM 比較を実行中...");

  try {
    const data = await apiPost("/api/v1/cdm/compare", {
      cdm_text: cdmText,
      satellite_tle: satTle,
      debris_tle: debTle,
      duration_days: 7,
      step_minutes: 1,
    });

    renderCdmCompareResult(data, els.cdmResult);
    setCdmStatus("比較完了。");
  } catch (err) {
    setCdmStatus(err.message, true);
  } finally {
    els.btnCdmCompare.disabled = false;
  }
}

async function fetchCdmAlerts() {
  const noradId = parseInt(els.alertNoradId.value, 10);
  const pcMinRaw = els.alertPcMin.value.trim();
  const pcMin = pcMinRaw ? parseFloat(pcMinRaw) : null;

  if (Number.isNaN(noradId) || noradId < 1) {
    setAlertStatus("NORAD ID を入力してください。", true);
    return;
  }

  els.btnFetchAlerts.disabled = true;
  els.alertTable.classList.add("hidden");
  els.alertCompareResult.classList.add("hidden");
  setAlertStatus("Space-Track から CDM を取得中...");

  try {
    const payload = { norad_id: noradId, limit: 25, days_ahead: 7 };
    if (pcMin != null && !Number.isNaN(pcMin)) {
      payload.pc_min = pcMin;
    }
    const data = await apiPost("/api/v1/cdm/fetch", payload);
    cdmAlerts = data.records;
    els.alertTableBody.innerHTML = "";

    if (cdmAlerts.length === 0) {
      setAlertStatus("該当する CDM アラートはありません。");
      return;
    }

    for (const [i, rec] of cdmAlerts.entries()) {
      const tr = document.createElement("tr");
      const otherName =
        rec.sat1_id === noradId ? rec.sat2_name || rec.sat2_id : rec.sat1_name || rec.sat1_id;
      tr.innerHTML = `
        <td>${formatTime(rec.tca)}</td>
        <td>${formatPc(rec.pc)}</td>
        <td>${rec.min_range_km?.toFixed(2) ?? "—"}</td>
        <td>${otherName}</td>
        <td>${rec.has_rtn_covariance ? "RTN σ" : "要詳細"}</td>
        <td>${rec.emergency_reportable ? "Y" : "—"}</td>
      `;
      tr.addEventListener("click", () => compareCdmAlert(rec, tr, i));
      els.alertTableBody.appendChild(tr);
    }

    els.alertTable.classList.remove("hidden");
    const cacheNote = data.cached ? "（キャッシュ）" : "";
    const degradedNote = data.degraded ? " / フォールバック" : "";
    setAlertStatus(`${cdmAlerts.length} 件取得${cacheNote}${degradedNote}。行をクリックで CAS 比較。`);
  } catch (err) {
    setAlertStatus(err.message, true);
  } finally {
    els.btnFetchAlerts.disabled = false;
  }
}

async function compareCdmAlert(record, rowEl, index) {
  const satTle = els.alertSatTle.value.trim();
  if (!satTle) {
    setAlertStatus("衛星 TLE を入力してください。", true);
    return;
  }

  document.querySelectorAll("#alert-table-body tr").forEach((el) => {
    el.classList.remove("selected");
  });
  rowEl.classList.add("selected");
  setAlertStatus(`CDM ${record.cdm_id || index + 1} を CAS と比較中...`);

  try {
    const data = await apiPost("/api/v1/cdm/compare-alert", {
      satellite_tle: satTle,
      record,
      duration_days: 7,
      step_minutes: 1,
    });
    renderCdmCompareResult(data.compare, els.alertCompareResult);
    const sigmaNote =
      data.compare.sigma_source === "cdm_covariance" ? " / CDM RTN σ 適用" : "";
    setAlertStatus(
      `比較完了（相手 NORAD ${data.debris_norad_id}${sigmaNote}）。`
    );
  } catch (err) {
    setAlertStatus(err.message, true);
  }
}

async function runManeuver() {
  if (!selectedConjunction) return;

  const deltaV = parseFloat(els.deltaV.value);
  if (Number.isNaN(deltaV) || deltaV < 0.01 || deltaV > 1.0) {
    setStatus("Δv は 0.01〜1.0 m/s の範囲で指定してください。", true);
    return;
  }

  els.btnManeuver.disabled = true;
  els.maneuverResult.textContent = "試算中...";

  try {
    const data = await apiPost("/api/v1/maneuver/preview", {
      satellite_tle: lastSatelliteTle,
      debris_tle: selectedConjunction.debris_tle,
      direction: els.maneuverDirection.value,
      delta_v_ms: deltaV,
      duration_days: 7,
      step_minutes: 1,
    });

    els.maneuverResult.innerHTML = `
      <div><strong>Before</strong></div>
      <div>TCA: ${formatTime(data.before.tca)}</div>
      <div>最接近: ${data.before.miss_distance_km.toFixed(3)} km</div>
      <div>相対速度: ${data.before.relative_velocity_kms.toFixed(3)} km/s</div>
      <div style="margin-top:0.5rem"><strong>After (${data.direction}, Δv=${data.delta_v_applied_ms} m/s)</strong></div>
      <div>TCA: ${formatTime(data.after.tca)}</div>
      <div>最接近: ${data.after.miss_distance_km.toFixed(3)} km</div>
      <div>相対速度: ${data.after.relative_velocity_kms.toFixed(3)} km/s</div>
    `;
  } catch (err) {
    els.maneuverResult.textContent = err.message;
  } finally {
    els.btnManeuver.disabled = false;
  }
}

async function loadDemoTle() {
  try {
    const res = await fetch(`${API_BASE}/samples/demo-satellite.tle`);
    if (!res.ok) throw new Error("デモ TLE が見つかりません。");
    const text = await res.text();
    els.tleInput.value = text.trim();
    els.thresholdKm.value = String(DEMO_THRESHOLD_KM);
    setStatus(`デモ TLE を読み込みました（閾値 ${DEMO_THRESHOLD_KM} km）。接近解析を実行してください。`);
  } catch (err) {
    setStatus(err.message, true);
  }
}

async function loadConstellationDemo() {
  try {
    const res = await fetch(`${API_BASE}/samples/constellation-demo.tle`);
    if (!res.ok) throw new Error("コンステレーションデモ TLE が見つかりません。");
    els.constellationInput.value = (await res.text()).trim();
    els.batchThresholdKm.value = String(DEMO_THRESHOLD_KM);
    setBatchStatus("デモ TLE を読み込みました。一括解析を実行してください。");
  } catch (err) {
    setBatchStatus(err.message, true);
  }
}

async function loadCdmDemo() {
  try {
    const [cdmRes, satRes, debRes] = await Promise.all([
      fetch(`${API_BASE}/samples/example.cdm`),
      fetch(`${API_BASE}/samples/demo-satellite.tle`),
      fetch(`${API_BASE}/samples/demo-debris.tle`),
    ]);
    if (!cdmRes.ok || !satRes.ok || !debRes.ok) {
      throw new Error("デモ CDM / TLE が見つかりません。");
    }
    els.cdmInput.value = (await cdmRes.text()).trim();
    els.cdmSatTle.value = (await satRes.text()).trim();
    els.cdmDebTle.value = (await debRes.text()).trim();
    setCdmStatus("デモ CDM と TLE を読み込みました。比較実行を押してください。");
  } catch (err) {
    setCdmStatus(err.message, true);
  }
}

function initEventListeners() {
  els.tabSingle.addEventListener("click", () => switchMode("single"));
  els.tabConstellation.addEventListener("click", () => switchMode("constellation"));
  els.tabCdm.addEventListener("click", () => switchMode("cdm"));
  els.tabAlerts.addEventListener("click", () => switchMode("alerts"));
  els.tabOps.addEventListener("click", () => switchMode("ops"));

  els.btnOpsRefresh.addEventListener("click", refreshOpsDashboard);
  els.opsFleetSelect.addEventListener("change", () => {
    if (els.opsFleetSelect.value) {
      refreshOpsDashboard();
    } else {
      els.opsSilencesSection?.classList.add("hidden");
      els.opsBreachStatesSection?.classList.add("hidden");
      els.opsBreachStatesAllSection?.classList.add("hidden");
      els.opsBreachHistoryAllSection?.classList.add("hidden");
      els.opsBreachRetentionAllSection?.classList.add("hidden");
      els.opsFleetAlertRulesSection?.classList.add("hidden");
      els.opsBreachHistorySection?.classList.add("hidden");
    }
  });
  if (els.opsBreachStatesBreachingOnly) {
    els.opsBreachStatesBreachingOnly.addEventListener("change", refreshOpsBreachStates);
  }
  if (els.opsBreachStatesAllBreachingOnly) {
    els.opsBreachStatesAllBreachingOnly.addEventListener("change", refreshOpsBreachStatesAll);
  }
  if (els.btnOpsBreachHistoryCsv) {
    els.btnOpsBreachHistoryCsv.addEventListener("click", downloadOpsBreachHistoryCsv);
  }
  if (els.btnOpsBreachHistorySummaryCsv) {
    els.btnOpsBreachHistorySummaryCsv.addEventListener("click", downloadOpsBreachHistorySummaryCsv);
  }
  if (els.btnOpsBreachHistoryAllCsv) {
    els.btnOpsBreachHistoryAllCsv.addEventListener("click", downloadOpsBreachHistoryAllCsv);
  }
  if (els.btnOpsBreachHistoryAllSummaryCsv) {
    els.btnOpsBreachHistoryAllSummaryCsv.addEventListener("click", downloadOpsBreachHistoryAllSummaryCsv);
  }
  if (els.btnOpsBreachHistoryAllFleetSummaryCsv) {
    els.btnOpsBreachHistoryAllFleetSummaryCsv.addEventListener("click", downloadOpsBreachHistoryAllFleetSummaryCsv);
  }
  if (els.opsBreachHistorySource) {
    els.opsBreachHistorySource.addEventListener("change", refreshOpsBreachHistory);
  }
  if (els.opsBreachHistoryBreachingOnly) {
    els.opsBreachHistoryBreachingOnly.addEventListener("change", refreshOpsBreachHistory);
  }
  for (const el of [els.opsBreachHistoryAlertnameOpen, els.opsBreachHistoryAlertnameHighrisk]) {
    el?.addEventListener("change", refreshOpsBreachHistory);
  }
  for (const el of [els.opsBreachHistorySince, els.opsBreachHistoryUntil]) {
    el?.addEventListener("change", refreshOpsBreachHistory);
  }
  if (els.btnOpsBreachHistoryRetentionSave) {
    els.btnOpsBreachHistoryRetentionSave.addEventListener("click", saveOpsBreachHistoryRetention);
  }
  if (els.opsBreachHistoryAllSource) {
    els.opsBreachHistoryAllSource.addEventListener("change", refreshOpsBreachHistoryAll);
  }
  if (els.opsBreachHistoryAllBreachingOnly) {
    els.opsBreachHistoryAllBreachingOnly.addEventListener("change", refreshOpsBreachHistoryAll);
  }
  for (const el of [els.opsBreachHistoryAllAlertnameOpen, els.opsBreachHistoryAllAlertnameHighrisk]) {
    el?.addEventListener("change", refreshOpsBreachHistoryAll);
  }
  for (const el of [els.opsBreachHistoryAllSince, els.opsBreachHistoryAllUntil]) {
    el?.addEventListener("change", refreshOpsBreachHistoryAll);
  }
  if (els.opsBreachHistoryAllFleetName) {
    els.opsBreachHistoryAllFleetName.addEventListener("change", refreshOpsBreachHistoryAll);
    els.opsBreachHistoryAllFleetName.addEventListener("input", refreshOpsBreachHistoryAll);
  }
  if (els.opsBreachHistoryAllFleetSummaryLimit) {
    els.opsBreachHistoryAllFleetSummaryLimit.addEventListener("change", refreshOpsBreachHistoryAll);
  }
  if (els.btnOpsBreachHistoryAllFleetSummaryPrev) {
    els.btnOpsBreachHistoryAllFleetSummaryPrev.addEventListener("click", () => {
      changeFleetSummaryPage(-1);
    });
  }
  if (els.btnOpsBreachHistoryAllFleetSummaryNext) {
    els.btnOpsBreachHistoryAllFleetSummaryNext.addEventListener("click", () => {
      changeFleetSummaryPage(1);
    });
  }
  if (els.btnOpsBreachHistoryAllFleetSummaryGo) {
    els.btnOpsBreachHistoryAllFleetSummaryGo.addEventListener("click", () => {
      goToFleetSummaryOffset(els.opsBreachHistoryAllFleetSummaryOffset?.value);
    });
  }
  if (els.opsBreachRetentionPreviewChangesOnly) {
    els.opsBreachRetentionPreviewChangesOnly.addEventListener("change", () => {
      if (lastOpsBreachRetentionImportPreview) {
        renderOpsBreachRetentionImportPreview(
          lastOpsBreachRetentionImportPreview.preview,
          lastOpsBreachRetentionImportPreview.errors
        );
      }
    });
  }
  if (els.btnOpsFleetAlertRulesDownload) {
    els.btnOpsFleetAlertRulesDownload.addEventListener("click", downloadOpsFleetAlertRules);
  }
  if (els.btnOpsFleetAlertRulesApply) {
    els.btnOpsFleetAlertRulesApply.addEventListener("click", applyOpsFleetAlertRules);
  }
  if (els.btnOpsPrometheusReload) {
    els.btnOpsPrometheusReload.addEventListener("click", triggerOpsPrometheusReload);
  }
  if (els.btnOpsBreachRetentionBulkSave) {
    els.btnOpsBreachRetentionBulkSave.addEventListener("click", saveOpsBreachRetentionBulk);
  }
  if (els.btnOpsBreachRetentionCsv) {
    els.btnOpsBreachRetentionCsv.addEventListener("click", downloadOpsBreachRetentionCsv);
  }
  if (els.btnOpsBreachRetentionImport) {
    els.btnOpsBreachRetentionImport.addEventListener("click", () => {
      retentionImportDryRun = false;
      els.opsBreachRetentionImportFile?.click();
    });
  }
  if (els.btnOpsBreachRetentionDryRun) {
    els.btnOpsBreachRetentionDryRun.addEventListener("click", () => {
      retentionImportDryRun = true;
      retentionImportDryRunCsv = false;
      els.opsBreachRetentionImportFile?.click();
    });
  }
  if (els.btnOpsBreachRetentionDryRunCsv) {
    els.btnOpsBreachRetentionDryRunCsv.addEventListener("click", () => {
      retentionImportDryRun = false;
      retentionImportDryRunCsv = true;
      els.opsBreachRetentionImportFile?.click();
    });
  }
  if (els.opsBreachRetentionImportFile) {
    els.opsBreachRetentionImportFile.addEventListener("change", () => {
      if (retentionImportDryRunCsv) {
        retentionImportDryRunCsv = false;
        downloadOpsBreachRetentionDryRunCsv();
        return;
      }
      importOpsBreachRetentionCsv(retentionImportDryRun);
      retentionImportDryRun = false;
    });
  }
  if (els.opsBreachRetentionSelectAll) {
    els.opsBreachRetentionSelectAll.addEventListener("change", () => {
      const checked = els.opsBreachRetentionSelectAll.checked;
      for (const el of els.opsBreachRetentionAllTableBody?.querySelectorAll(".ops-breach-retention-row-select") ?? []) {
        el.checked = checked;
      }
    });
  }
  els.opsStatusFilter.addEventListener("change", refreshOpsDashboard);
  if (els.btnOpsSilenceCreate) {
    els.btnOpsSilenceCreate.addEventListener("click", createOpsSilence);
  }
  if (els.btnOpsSilencesDeleteAll) {
    els.btnOpsSilencesDeleteAll.addEventListener("click", deleteAllOpsSilences);
  }
  if (els.btnOpsSilencesDeleteSelected) {
    els.btnOpsSilencesDeleteSelected.addEventListener("click", deleteSelectedOpsSilences);
  }
  if (els.opsSilencesSelectAll) {
    els.opsSilencesSelectAll.addEventListener("change", () => {
      const checked = els.opsSilencesSelectAll.checked;
      els.opsSilencesTableBody?.querySelectorAll("input.ops-silence-select").forEach((el) => {
        el.checked = checked;
      });
      updateOpsSilencesDeleteSelectedButton();
    });
  }
  if (els.btnOpsSsoLogin) {
    els.btnOpsSsoLogin.addEventListener("click", () => {
      window.location.href = `${API_BASE}/api/v1/auth/oidc/login`;
    });
  }
  if (els.btnOpsSsoLogout) {
    els.btnOpsSsoLogout.addEventListener("click", async () => {
      try {
        await apiPost("/api/v1/auth/logout", {}, { ops: true });
        opsAuthMe = { authenticated: false };
        await refreshOpsAuthStatus();
        setOpsStatus("ログアウトしました。");
      } catch (err) {
        setOpsStatus(err.message, true);
      }
    });
  }
  if (els.opsApiKeyInput) {
    const savedKey = localStorage.getItem("casApiKey");
    if (savedKey) {
      els.opsApiKeyInput.value = savedKey;
    }
    els.opsApiKeyInput.addEventListener("change", saveOpsApiKeyFromInput);
  }

  els.btnLoadSample.addEventListener("click", () => {
    els.tleInput.value = ISS_SAMPLE;
    els.thresholdKm.value = "5";
    setStatus("ISS サンプルを読み込みました。");
  });
  els.btnLoadDemo.addEventListener("click", loadDemoTle);
  els.useAdvancedPc.addEventListener("change", () => {
    syncAnisotropicCheckbox(els.useAdvancedPc, els.useAnisotropicCov);
  });
  els.batchUseAdvancedPc.addEventListener("change", () => {
    syncAnisotropicCheckbox(els.batchUseAdvancedPc, els.batchUseAnisotropicCov);
  });
  syncAnisotropicCheckbox(els.useAdvancedPc, els.useAnisotropicCov);
  syncAnisotropicCheckbox(els.batchUseAdvancedPc, els.batchUseAnisotropicCov);
  els.btnScan.addEventListener("click", runScan);
  els.btnWebhookTest.addEventListener("click", runWebhookTest);
  els.btnLoadConstellationDemo.addEventListener("click", loadConstellationDemo);
  els.btnBatchScan.addEventListener("click", runBatchScan);
  els.satelliteSelect.addEventListener("change", () => {
    showBatchSatellite(parseInt(els.satelliteSelect.value, 10));
  });
  els.btnLoadCdmDemo.addEventListener("click", loadCdmDemo);
  els.btnCdmCompare.addEventListener("click", runCdmCompare);
  els.btnCdmToScan.addEventListener("click", transferCdmToScan);
  els.btnAlertLoadIss.addEventListener("click", () => {
    els.alertSatTle.value = ISS_SAMPLE;
    setAlertStatus("ISS サンプル TLE を読み込みました。");
  });
  els.btnFetchAlerts.addEventListener("click", fetchCdmAlerts);
  els.btnManeuver.addEventListener("click", runManeuver);
}

async function init() {
  initViewer();
  els.tleInput.value = ISS_SAMPLE;
  initEventListeners();
  const health = await waitForBackend();
  if (health) {
    let msg = "準備完了。デモ TLE 読込 → 接近解析を実行してください。";
    if (health.alert_delivery_configured && health.alert_delivery_format) {
      msg += ` / 通知: ${health.alert_delivery_format}`;
    }
    setStatus(msg);
    if (health.spacetrack_configured) {
      els.autoSpacetrackCdm.disabled = false;
      els.autoSpacetrackCdmWrap.title = "Space-Track cdm_public から RTN 共分散を自動適用";
      els.batchAutoSpacetrackCdm.disabled = false;
      els.batchAutoSpacetrackCdmWrap.title = "Space-Track cdm_public から RTN 共分散を自動適用";
    } else {
      els.autoSpacetrackCdm.disabled = true;
      els.autoSpacetrackCdmWrap.title = "Space-Track 認証（.env）が必要です。";
      els.batchAutoSpacetrackCdm.disabled = true;
      els.batchAutoSpacetrackCdmWrap.title = "Space-Track 認証（.env）が必要です。";
    }
  }
  const tabParam = new URLSearchParams(window.location.search).get("tab");
  if (tabParam === "ops") {
    switchMode("ops");
  }
}

init();
