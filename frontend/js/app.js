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
};

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
  const res = await fetch(`${API_BASE}${path}`, {
    headers: ops ? getOpsApiHeaders() : undefined,
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

async function apiPatch(path, body, { ops = false } = {}) {
  const headers = ops
    ? getOpsApiHeaders({ "Content-Type": "application/json" })
    : { "Content-Type": "application/json" };
  const res = await fetch(`${API_BASE}${path}`, {
    method: "PATCH",
    headers,
    body: JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = data.detail;
    const msg = typeof detail === "string" ? detail : `API エラー (${res.status})`;
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

function opsStatusBadge(status) {
  return `<span class="ops-status-badge ops-status-${status}">${status}</span>`;
}

function formatSlaLag(hours) {
  if (hours == null) return "—";
  return `${hours.toFixed(1)}h`;
}

function formatSlaLine(slaItem) {
  if (!slaItem || !slaItem.has_active_schedule) {
    return "Screening lag: <span class=\"ops-sla-na\">N/A（schedule なし）</span>";
  }
  const lag = formatSlaLag(slaItem.screening_lag_hours);
  if (slaItem.screening_sla_ok) {
    return `Screening lag: ${lag} — <span class="ops-sla-ok">OK</span>`;
  }
  return `Screening lag: ${lag} — <span class="ops-sla-overdue">OVERDUE</span>`;
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

async function refreshOpsDashboard() {
  const fleetId = els.opsFleetSelect.value;
  if (!fleetId) {
    setOpsStatus("艦隊を選択してください。", true);
    return;
  }
  try {
    const [summary, sla] = await Promise.all([
      apiGet(`/api/v1/ops/fleets/${fleetId}/summary`, { ops: true }),
      apiGet(`/api/v1/ops/sla?fleet_id=${fleetId}`, { ops: true }),
    ]);
    const slaItem = sla.items && sla.items.length ? sla.items[0] : null;
    els.opsSummary.innerHTML = `
      <strong>${summary.fleet_name}</strong><br/>
      open: ${summary.open_count} /
      ack: ${summary.acknowledged_count} /
      対策計画: ${summary.mitigation_planned_count} /
      closed: ${summary.closed_count}<br/>
      最新 Run: ${summary.latest_run_status ?? "—"} ${formatTime(summary.latest_run_finished_at)}<br/>
      ${formatSlaLine(slaItem)}
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
        <td>${opsStatusBadge(a.status)}</td>
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

      const transitions = {
        open: [
          { label: "Ack", status: "acknowledged" },
          { label: "誤検知", status: "false_positive" },
        ],
        acknowledged: [
          { label: "対策計画", status: "mitigation_planned" },
          { label: "クローズ", status: "closed" },
          { label: "誤検知", status: "false_positive" },
        ],
        mitigation_planned: [
          { label: "クローズ", status: "closed" },
          { label: "誤検知", status: "false_positive" },
        ],
      };
      for (const t of transitions[a.status] || []) {
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
  const escalatedBadge = alert.escalated
    ? '<br/><span class="ops-pc-escalated">ESCALATED</span>'
    : "";
  return (
    `<span class="ops-pc-screening">${screening}</span>` +
    `<br/><span class="ops-pc-refinement">→ ${formatPc(ref.pc_refined)} (${methodLabel})${autoBadge}</span>` +
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
  div.textContent = `Pc refined: ${formatPc(refinement.pc_screening)} → ${formatPc(refinement.pc_refined)} (${methodLabel})`;
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
    loadOpsFleets();
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
    }
  });
  els.opsStatusFilter.addEventListener("change", refreshOpsDashboard);
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
}

init();
