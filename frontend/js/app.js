/** Main UI: TLE input, conjunction scan, maneuver preview. */

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
  tleInput: document.getElementById("tle-input"),
  btnLoadSample: document.getElementById("btn-load-sample"),
  btnLoadDemo: document.getElementById("btn-load-demo"),
  thresholdKm: document.getElementById("threshold-km"),
  btnScan: document.getElementById("btn-scan"),
  statusMsg: document.getElementById("status-msg"),
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

function setStatus(msg, isError = false) {
  els.statusMsg.textContent = msg;
  els.statusMsg.classList.toggle("error", isError);
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
  return iso.replace("T", " ").replace("Z", " UTC");
}

function renderConjunctions(data) {
  els.scanMeta.textContent = `${data.conjunctions.length} 件検出 / カタログ ${data.debris_catalog_count} 件 / ${data.computation_time_ms} ms`;
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
    const data = await apiPost("/api/v1/conjunctions", {
      tle,
      duration_days: 7,
      threshold_km: threshold,
      step_minutes: 1,
    });
    renderConjunctions(data);
    setStatus(`解析完了（${data.computation_time_ms} ms）`);
  } catch (err) {
    setStatus(err.message, true);
  } finally {
    els.btnScan.disabled = false;
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

function init() {
  initViewer();
  els.tleInput.value = ISS_SAMPLE;
  els.btnLoadSample.addEventListener("click", () => {
    els.tleInput.value = ISS_SAMPLE;
    els.thresholdKm.value = "5";
    setStatus("ISS サンプルを読み込みました。");
  });
  els.btnLoadDemo.addEventListener("click", loadDemoTle);
  els.btnScan.addEventListener("click", runScan);
  els.btnManeuver.addEventListener("click", runManeuver);
}

init();
