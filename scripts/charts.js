/* ==========================================================================
   Radar — Charts
   Lightweight SVG sparklines and a canvas trend chart. No dependencies.
   Charts are sized to their container so they are never clipped by a card.
   ========================================================================== */

"use strict";

function themeColor(name, fallback) {
  const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return value || fallback;
}

function escapeAttr(value) {
  return String(value).replace(/[&<>"']/g, c => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  })[c]);
}

function formatValue(value) {
  const abs = Math.abs(value);
  const digits = abs >= 1000 ? 0 : abs >= 10 ? 1 : 2;
  return new Intl.NumberFormat("en-IN", { maximumFractionDigits: digits }).format(value);
}

/** Render a minimal SVG sparkline that fits inside its fixed-height box. */
function renderSparklines() {
  document.querySelectorAll(".sparkline").forEach(el => {
    let pts;
    try {
      pts = JSON.parse(el.dataset.points || "[]");
    } catch (error) {
      return;
    }
    if (!Array.isArray(pts)) return;

    const nums = pts
      .filter(v => v !== null && v !== undefined && v !== "")
      .map(Number)
      .filter(Number.isFinite);
    if (nums.length < 2) return;

    const width = 120;
    const height = 30;
    const min = Math.min(...nums);
    const max = Math.max(...nums);
    const range = max - min || 1;
    const color = themeColor("--brand", "#0e7c70");
    const label = el.dataset.label || "Trend sparkline";

    const coords = nums.map((v, i) => {
      const x = (i / (nums.length - 1)) * width;
      const y = height - 2 - ((v - min) / range) * (height - 4);
      return `${x},${y}`;
    }).join(" ");

    el.innerHTML = `
      <svg viewBox="0 0 ${width} ${height}" preserveAspectRatio="none" role="img" aria-label="${escapeAttr(label)}">
        <polyline points="${coords}" fill="none" stroke="${color}" stroke-width="2.4"
          stroke-linecap="round" stroke-linejoin="round" vector-effect="non-scaling-stroke" />
      </svg>`;
  });
}

let trendChart = null;

/** Draw the historical trend chart into its own full-width section. */
function renderTrendChart() {
  const canvas = document.getElementById("trend-chart");
  if (!canvas) return;

  const data = window.__TREND_CHART_DATA__ || window.chartData;
  if (!data || !Array.isArray(data.values) || data.values.length < 2) return;

  const wrap = canvas.parentElement;
  let tooltip = wrap.querySelector(".chart-tooltip");
  if (!tooltip) {
    tooltip = document.createElement("div");
    tooltip.className = "chart-tooltip";
    tooltip.hidden = true;
    wrap.appendChild(tooltip);
  }

  const rect = canvas.getBoundingClientRect();
  const w = Math.max(280, Math.round(rect.width || wrap.clientWidth));
  const h = Math.max(220, Math.round(rect.height || 300));
  const dpr = Math.max(1, Math.min(window.devicePixelRatio || 1, 2));
  canvas.width = Math.round(w * dpr);
  canvas.height = Math.round(h * dpr);

  const ctx = canvas.getContext("2d");
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

  const values = data.values.map(Number);
  const labels = Array.isArray(data.labels) ? data.labels : values.map((_, i) => String(i));
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const pad = { left: 54, right: 18, top: 18, bottom: 42 };

  trendChart = {
    canvas, ctx, tooltip, data, values, labels, w, h, pad, min, max, range, hover: null,
    xAt: i => pad.left + (i / (values.length - 1)) * (w - pad.left - pad.right),
    yAt: v => (h - pad.bottom) - ((v - min) / range) * (h - pad.top - pad.bottom)
  };

  drawTrendChart(trendChart);
  bindTrendInteractions(trendChart);
}

function drawTrendChart(s) {
  const { ctx, w, h, pad, values, labels } = s;
  const brand = themeColor("--brand", "#0e7c70");
  const line = themeColor("--line", "#dfe7ec");
  const muted = themeColor("--muted", "#6b7d8b");
  const axis = themeColor("--ink", "#0c1c2e");

  ctx.clearRect(0, 0, w, h);

  // Horizontal guides with readable value labels.
  ctx.font = "12px Inter, sans-serif";
  ctx.lineWidth = 1;
  ctx.strokeStyle = line;
  ctx.fillStyle = muted;
  ctx.textAlign = "right";
  for (let i = 0; i <= 3; i++) {
    const y = pad.top + (i * (h - pad.top - pad.bottom)) / 3;
    ctx.beginPath();
    ctx.moveTo(pad.left, y);
    ctx.lineTo(w - pad.right, y);
    ctx.stroke();
    ctx.fillText(formatValue(s.max - (i * (s.max - s.min)) / 3), pad.left - 8, y + 4);
  }

  // Baseline.
  ctx.strokeStyle = axis;
  ctx.globalAlpha = 0.25;
  ctx.beginPath();
  ctx.moveTo(pad.left, pad.top);
  ctx.lineTo(pad.left, h - pad.bottom);
  ctx.lineTo(w - pad.right, h - pad.bottom);
  ctx.stroke();
  ctx.globalAlpha = 1;

  // Filled area under the series.
  const gradient = ctx.createLinearGradient(0, pad.top, 0, h - pad.bottom);
  gradient.addColorStop(0, "rgba(14, 124, 112, 0.22)");
  gradient.addColorStop(1, "rgba(14, 124, 112, 0.01)");
  ctx.beginPath();
  values.forEach((v, i) => i === 0 ? ctx.moveTo(s.xAt(i), s.yAt(v)) : ctx.lineTo(s.xAt(i), s.yAt(v)));
  ctx.lineTo(s.xAt(values.length - 1), h - pad.bottom);
  ctx.lineTo(s.xAt(0), h - pad.bottom);
  ctx.closePath();
  ctx.fillStyle = gradient;
  ctx.fill();

  // Series line.
  ctx.beginPath();
  values.forEach((v, i) => i === 0 ? ctx.moveTo(s.xAt(i), s.yAt(v)) : ctx.lineTo(s.xAt(i), s.yAt(v)));
  ctx.strokeStyle = brand;
  ctx.lineWidth = 3;
  ctx.lineJoin = "round";
  ctx.stroke();

  // Point markers.
  values.forEach((v, i) => {
    ctx.beginPath();
    ctx.arc(s.xAt(i), s.yAt(v), s.hover === i ? 5 : 3.5, 0, Math.PI * 2);
    ctx.fillStyle = "#fff";
    ctx.fill();
    ctx.lineWidth = s.hover === i ? 3 : 2;
    ctx.strokeStyle = brand;
    ctx.stroke();
  });

  // X-axis labels, spaced to fit the available width and always showing the latest point.
  const slots = Math.max(2, Math.floor((w - pad.left - pad.right) / 72));
  const step = Math.max(1, Math.ceil(values.length / slots));
  const last = values.length - 1;
  ctx.textAlign = "center";
  ctx.fillStyle = muted;
  labels.forEach((label, i) => {
    if ((last - i) % step !== 0) return;
    const x = Math.min(Math.max(s.xAt(i), pad.left), w - pad.right);
    ctx.fillText(label, x, h - pad.bottom + 22);
  });

  // Hover / keyboard crosshair.
  if (s.hover !== null && s.hover >= 0 && s.hover < values.length) {
    const x = s.xAt(s.hover);
    const y = s.yAt(values[s.hover]);
    ctx.strokeStyle = brand;
    ctx.globalAlpha = 0.4;
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(x, pad.top);
    ctx.lineTo(x, h - pad.bottom);
    ctx.stroke();
    ctx.globalAlpha = 1;
  }
  ctx.textAlign = "left";
}

function showTrendPoint(index) {
  const s = trendChart;
  if (!s || !s.values.length) return;
  const i = Math.max(0, Math.min(s.values.length - 1, index));
  s.hover = i;
  drawTrendChart(s);

  const unit = s.data.unit ? ` ${s.data.unit}` : "";
  s.tooltip.textContent = `${s.labels[i]} · ${formatValue(s.values[i])}${unit}`;
  s.tooltip.hidden = false;
  s.tooltip.style.left = `${s.canvas.offsetLeft + s.xAt(i)}px`;
  s.tooltip.style.top = `${Math.max(4, s.canvas.offsetTop + s.yAt(s.values[i]) - 42)}px`;
}

function clearTrendPoint() {
  if (!trendChart) return;
  trendChart.hover = null;
  trendChart.tooltip.hidden = true;
  drawTrendChart(trendChart);
}

function bindTrendInteractions(state) {
  const { canvas, tooltip, values } = state;
  if (canvas.dataset.bound) return;
  canvas.dataset.bound = "1";
  canvas.tabIndex = 0;

  canvas.addEventListener("pointermove", event => {
    const s = trendChart;
    if (!s) return;
    const rect = canvas.getBoundingClientRect();
    const x = (event.clientX - rect.left) * (s.w / rect.width);
    const ratio = (x - s.pad.left) / (s.w - s.pad.left - s.pad.right);
    showTrendPoint(Math.round(ratio * (s.values.length - 1)));
  });
  canvas.addEventListener("pointerleave", clearTrendPoint);
  tooltip.addEventListener("pointerleave", clearTrendPoint);

  canvas.addEventListener("focus", () => showTrendPoint(values.length - 1));
  canvas.addEventListener("blur", clearTrendPoint);
  canvas.addEventListener("keydown", event => {
    const current = trendChart && trendChart.hover !== null ? trendChart.hover : values.length - 1;
    if (event.key === "ArrowLeft") showTrendPoint(current - 1);
    else if (event.key === "ArrowRight") showTrendPoint(current + 1);
    else if (event.key === "Home") showTrendPoint(0);
    else if (event.key === "End") showTrendPoint(values.length - 1);
    else if (event.key === "Escape") clearTrendPoint();
    else return;
    event.preventDefault();
  });

  if (typeof ResizeObserver !== "undefined") {
    new ResizeObserver(() => renderTrendChart()).observe(canvas.parentElement);
  } else {
    window.addEventListener("resize", renderTrendChart);
  }
}

document.addEventListener("DOMContentLoaded", () => {
  renderSparklines();
  renderTrendChart();
});
