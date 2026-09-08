"use strict";

// 폴링 주기. 6단계에서 SSE로 대체하고 이 경로는 fallback으로 남긴다.
const POLL_MS = 3000;

// §4 결정: 저장은 UTC, 표시는 Asia/Seoul.
const KST = new Intl.DateTimeFormat("ko-KR", {
  timeZone: "Asia/Seoul",
  dateStyle: "short",
  timeStyle: "medium",
});

const LIFECYCLE_LABEL = { running: "가동", stopped: "정지", offline: "연결 끊김" };
const ZONE_CLASS = { A: "z-ok", B: "z-ok", C: "z-warn", D: "z-crit" };

const el = (id) => document.getElementById(id);
const fmtKst = (iso) => (iso ? KST.format(new Date(iso)) : "-");
const fmtNum = (value) =>
  typeof value === "number" ? value.toFixed(3) : "-";

async function getJson(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${url} → ${res.status}`);
  return res.json();
}

function renderCards(machines) {
  const box = el("cards");
  if (!machines.length) {
    box.innerHTML = '<p class="muted">아직 수신된 데이터가 없습니다.</p>';
    return;
  }
  box.innerHTML = machines
    .map(
      (m) => `
      <article class="card ${ZONE_CLASS[m.zone] || ""}">
        <div class="card-top">
          <span class="mid">${m.machine_id}호기</span>
          <span class="pill ${m.lifecycle}">${
            LIFECYCLE_LABEL[m.lifecycle] || m.lifecycle
          }</span>
        </div>
        <div class="big">${m.zone || "-"}</div>
        <dl>
          <div><dt>진동</dt><dd>${fmtNum(m.vibration_value)} mm/s RMS</dd></div>
          <div><dt>연속 Zone D</dt><dd>${m.zone_d_consecutive_count || 0}회</dd></div>
          <div><dt>최근 수신</dt><dd>${fmtKst(m.updated_at)}</dd></div>
        </dl>
      </article>`
    )
    .join("");
}

function renderEvents(events) {
  const body = el("events").querySelector("tbody");
  body.innerHTML = events
    .map(
      (e) => `
      <tr>
        <td>${fmtKst(e.observed_at)}</td>
        <td>${e.machine_id}</td>
        <td>${e.message_type}</td>
        <td>${e.zone || "-"}</td>
        <td>${fmtNum(e.vibration_value)}</td>
        <td>${e.zone_d_consecutive_count || 0}</td>
      </tr>`
    )
    .join("");
}

// 의존성 없는 인라인 SVG 라인 차트. Chart.js가 필요해지면 이 함수만 교체한다.
function renderChart(points) {
  const box = el("chart");
  if (points.length < 2) {
    box.innerHTML = '<p class="muted">표시할 시계열이 부족합니다.</p>';
    return;
  }
  const width = box.clientWidth || 720;
  const height = 220;
  const pad = 36;

  const times = points.map((p) => new Date(p.observed_at).getTime());
  const values = points.map((p) => p.vibration_value);
  const tMin = Math.min(...times);
  const tMax = Math.max(...times);
  const vMax = Math.max(...values) * 1.1 || 1;

  const sx = (t) => pad + ((width - 2 * pad) * (t - tMin)) / (tMax - tMin || 1);
  const sy = (v) => height - pad - ((height - 2 * pad) * v) / vMax;

  const d = points
    .map((p, i) => `${i ? "L" : "M"}${sx(times[i]).toFixed(1)},${sy(values[i]).toFixed(1)}`)
    .join(" ");

  box.innerHTML = `
    <svg class="chart" viewBox="0 0 ${width} ${height}" preserveAspectRatio="none">
      <line class="axis" x1="${pad}" y1="${height - pad}" x2="${width - pad}" y2="${height - pad}" />
      <line class="axis" x1="${pad}" y1="${pad}" x2="${pad}" y2="${height - pad}" />
      <text class="tick" x="${pad}" y="${pad - 10}">${vMax.toFixed(2)} mm/s RMS</text>
      <path class="line" d="${d}" />
    </svg>`;
}

let machineChoicesLoaded = false;

async function refresh() {
  try {
    const machines = await getJson("/api/machines");
    renderCards(machines);

    const select = el("machine-select");
    if (!machineChoicesLoaded && machines.length) {
      select.innerHTML = machines
        .map((m) => `<option value="${m.machine_id}">${m.machine_id}호기</option>`)
        .join("");
      machineChoicesLoaded = true;
    }

    const typeFilter = el("type-select").value;
    const eventsUrl = new URL("/api/events", location.origin);
    eventsUrl.searchParams.set("limit", "100");
    if (typeFilter) eventsUrl.searchParams.set("type", typeFilter);
    renderEvents(await getJson(eventsUrl));

    const machineId = select.value || (machines[0] && machines[0].machine_id);
    if (machineId) {
      const hours = el("range-select").value;
      const series = await getJson(
        `/api/timeseries?machine_id=${machineId}&hours=${hours}`
      );
      renderChart(series.points);
    }

    el("updated").textContent = `갱신 ${KST.format(new Date())}`;
  } catch (err) {
    el("updated").textContent = `오류: ${err.message}`;
  }
}

for (const id of ["machine-select", "type-select", "range-select"]) {
  el(id).addEventListener("change", refresh);
}
refresh();
setInterval(refresh, POLL_MS);
