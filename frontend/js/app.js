/** Main UI: TLE input, conjunction scan, batch, CDM compare, maneuver preview. */

import {
  initViewer,
  showOrbits,
  getTcaPositionFromOrbits,
} from "./cesium_viewer.js";

const API_BASE = window.location.origin.includes("8000")
  ? ""
  : "http://127.0.0.1:8000";

const ISS_SAMPLE = `ISS (ZARYA)
1 25544U 98067A   25179.51782528  .00016717  00000+0  10270-3 0  9993
2 25544  51.6347  74.8662 0004176 315.5599 138.2340 15.50909589423071`;

const DEMO_THRESHOLD_KM = 50;

const els = {
  tabSingle: document.getElementById("tab-single"),
  tabConstellation: document.getElementById("tab-constellation"),
  tabCdm: document.getElementById("tab-cdm"),
  panelSingle: document.getElementById("panel-single"),
  panelConstellation: document.getElementById("panel-constellation"),
  panelCdm: document.getElementById("panel-cdm"),
  tleInput: document.getElementById("tle-input"),
  btnLoadSample: document.getElementById("btn-load-sample"),
  btnLoadDemo: document.getElementById("btn-load-demo"),
  thresholdKm: document.getElementById("threshold-km"),
  sigmaKm: document.getElementById("sigma-km"),
  btnScan: document.getElementById("btn-scan"),
  statusMsg: document.getElementById("status-msg"),
  constellationInput: document.getElementById("constellation-input"),
  batchThresholdKm: document.getElementById("batch-threshold-km"),
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
  cdmStatusMsg: document.getElementById("cdm-status-msg"),
  cdmResult: document.getElementById("cdm-result"),
  scanMeta: document.getElementById("scan-meta"),
  conjunctionList: document.getElementById("conjunction-list"),
  maneuverSection: document.getElementById("maneuver-section"),
  selectedDebris: document.getElementById("selected-debris"),
  maneuverDirection: document.getElementById("maneuver-direction"),
  deltaV: document.getElementById("delta-v"),
  btnManeuver: document.getElementById("btn-maneuver"),
  maneuverResult: document.getElementById("maneuver-result"),
};

let selectedConjunction = null;
let lastSatelliteTle = "";
let batchResults = [];
let currentMode = "single";

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

async function apiPost(path, body) {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
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

function parseConstellationBlocks(text) {
  const blocks = text.split("---").map((b) => b.trim()).filter(Boolean);
  return blocks.map((block, i) => {
    const firstLine = block.split("\n")[0].trim();
    const name = firstLine.startsWith("1 ") ? `SAT-${i + 1}` : firstLine;
    return { name, tle: block };
  });
}

function switchMode(mode) {
  currentMode = mode;
  for (const tab of [els.tabSingle, els.tabConstellation, els.tabCdm]) {
    tab.classList.toggle("active", tab.dataset.mode === mode);
  }
  els.panelSingle.classList.toggle("hidden", mode !== "single");
  els.panelConstellation.classList.toggle("hidden", mode !== "constellation");
  els.panelCdm.classList.toggle("hidden", mode !== "cdm");
}

function renderConjunctions(data) {
  els.scanMeta.textContent = `${data.conjunctions.length} 件検出 / カタログ ${data.debris_catalog_count} 件 / ${data.computation_time_ms} ms / TLE: ${data.tle_provider || "celestrak"}`;
  els.conjunctionList.innerHTML = "";

  if (data.conjunctions.length === 0) {
    els.conjunctionList.innerHTML =
      "<li>指定閾値以内の接近は検出されませんでした。デモ用に閾値を 50 km などに広げて再試行できます。</li>";
    return;
  }

  for (const c of data.conjunctions) {
    const li = document.createElement("li");
    li.className = `risk-${c.risk_level}`;
    li.innerHTML = `
      <strong>${c.debris_name}</strong> (NORAD ${c.debris_norad_id})<br />
      TCA: ${formatTime(c.tca)}<br />
      距離: ${c.miss_distance_km.toFixed(2)} km /
      Pc: ${formatPc(c.pc)} /
      相対速度: ${c.relative_velocity_kms.toFixed(2)} km/s /
      <span class="risk-${c.risk_level}">${c.risk_level}</span>
    `;
    li.addEventListener("click", () => selectConjunction(c, li));
    els.conjunctionList.appendChild(li);
  }
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
    };
    if (sigmaRaw) {
      payload.sigma_km = parseFloat(sigmaRaw);
    }
    const data = await apiPost("/api/v1/conjunctions", payload);
    renderConjunctions(data);
    setStatus(`解析完了（${data.computation_time_ms} ms）`);
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
    const data = await apiPost("/api/v1/conjunctions/batch", {
      satellites,
      duration_days: 7,
      threshold_km: threshold,
      step_minutes: 1,
    });

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
      (data.parallel
        ? ` / 並列 ${data.worker_count} workers`
        : "");

    els.satelliteSelect.innerHTML = "";
    batchResults.forEach((r, i) => {
      const opt = document.createElement("option");
      opt.value = String(i);
      opt.textContent = `${r.satellite.name} (${r.conjunctions.length} 件)`;
      els.satelliteSelect.appendChild(opt);
    });
    els.satelliteSelectWrap.classList.remove("hidden");

    if (batchResults.length > 0) {
      showBatchSatellite(0);
    }
    setBatchStatus(`一括解析完了（${data.computation_time_ms} ms）`);
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

    els.cdmResult.innerHTML = `
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
          <div>σ: ${data.cas_sigma_km?.toFixed(4) ?? "—"} km (${sigmaLabel})</div>
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
    els.cdmResult.classList.remove("hidden");
    setCdmStatus("比較完了。");
  } catch (err) {
    setCdmStatus(err.message, true);
  } finally {
    els.btnCdmCompare.disabled = false;
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

function init() {
  initViewer();
  els.tleInput.value = ISS_SAMPLE;

  els.tabSingle.addEventListener("click", () => switchMode("single"));
  els.tabConstellation.addEventListener("click", () => switchMode("constellation"));
  els.tabCdm.addEventListener("click", () => switchMode("cdm"));

  els.btnLoadSample.addEventListener("click", () => {
    els.tleInput.value = ISS_SAMPLE;
    els.thresholdKm.value = "5";
    setStatus("ISS サンプルを読み込みました。");
  });
  els.btnLoadDemo.addEventListener("click", loadDemoTle);
  els.btnScan.addEventListener("click", runScan);
  els.btnLoadConstellationDemo.addEventListener("click", loadConstellationDemo);
  els.btnBatchScan.addEventListener("click", runBatchScan);
  els.satelliteSelect.addEventListener("change", () => {
    showBatchSatellite(parseInt(els.satelliteSelect.value, 10));
  });
  els.btnLoadCdmDemo.addEventListener("click", loadCdmDemo);
  els.btnCdmCompare.addEventListener("click", runCdmCompare);
  els.btnManeuver.addEventListener("click", runManeuver);
}

init();
