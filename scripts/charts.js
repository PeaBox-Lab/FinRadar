/* ==========================================================================
   Radar — Charts
   Lightweight SVG sparklines and a canvas trend chart. No dependencies.
   ========================================================================== */

"use strict";

function themeColor(name, fallback) {
  const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return value || fallback;
}

/** Render a minimal SVG sparkline from the data-points attribute. */
function renderSparklines() {
  const sparklines = document.querySelectorAll(".sparkline");
  sparklines.forEach(el => {
    const pts = JSON.parse(el.dataset.points || "[]");
    if (pts.length < 2) return;

    const width = 120;
    const height = 30;
    const min = Math.min(...pts);
    const max = Math.max(...pts);
    const range = max - min || 1;
    const color = themeColor("--brand", "#0e7c70");

    const coords = pts.map((v, i) => {
      const x = (i / (pts.length - 1)) * width;
      const y = height - ((v - min) / range) * height;
      return `${x},${y}`;
    }).join(" ");

    el.innerHTML = `
      <svg viewBox="0 0 ${width} ${height}" preserveAspectRatio="none" role="img" aria-label="Trend sparkline">
        <polyline points="${coords}" fill="none" stroke="${color}" stroke-width="2.4"
          stroke-linecap="round" stroke-linejoin="round" vector-effect="non-scaling-stroke" />
      </svg>`;
  });
}

/** Draw the historical trend chart on detail pages. */
function renderTrendChart() {
  const canvas = document.getElementById("trend-chart");
  if (!canvas) return;

  const data = window.__TREND_CHART_DATA__ || window.chartData;
  if (!data || !data.values || data.values.length < 2) return;

  const ctx = canvas.getContext("2d");
  const padding = 44;
  const w = canvas.width = canvas.parentElement.clientWidth;
  const h = canvas.height = 300;

  const brand = themeColor("--brand", "#0e7c70");
  const line = themeColor("--line", "#dfe7ec");
  const muted = themeColor("--muted", "#6b7d8b");
  const axis = themeColor("--ink", "#0c1c2e");

  const labels = data.labels;
  const values = data.values;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const xAt = i => padding + (i / (values.length - 1)) * (w - 2 * padding);
  const yAt = v => (h - padding) - ((v - min) / range) * (h - 2 * padding);

  ctx.clearRect(0, 0, w, h);

  // Horizontal guides
  ctx.strokeStyle = line;
  ctx.lineWidth = 1;
  for (let i = 0; i <= 3; i++) {
    const y = padding + (i * (h - 2 * padding)) / 3;
    ctx.beginPath();
    ctx.moveTo(padding, y);
    ctx.lineTo(w - padding, y);
    ctx.stroke();
  }

  // Baseline
  ctx.strokeStyle = axis;
  ctx.globalAlpha = 0.25;
  ctx.beginPath();
  ctx.moveTo(padding, padding);
  ctx.lineTo(padding, h - padding);
  ctx.lineTo(w - padding, h - padding);
  ctx.stroke();
  ctx.globalAlpha = 1;

  // Filled area under the series
  const gradient = ctx.createLinearGradient(0, padding, 0, h - padding);
  gradient.addColorStop(0, "rgba(14, 124, 112, 0.22)");
  gradient.addColorStop(1, "rgba(14, 124, 112, 0.01)");
  ctx.beginPath();
  values.forEach((v, i) => i === 0 ? ctx.moveTo(xAt(i), yAt(v)) : ctx.lineTo(xAt(i), yAt(v)));
  ctx.lineTo(xAt(values.length - 1), h - padding);
  ctx.lineTo(xAt(0), h - padding);
  ctx.closePath();
  ctx.fillStyle = gradient;
  ctx.fill();

  // Series line
  ctx.beginPath();
  values.forEach((v, i) => i === 0 ? ctx.moveTo(xAt(i), yAt(v)) : ctx.lineTo(xAt(i), yAt(v)));
  ctx.strokeStyle = brand;
  ctx.lineWidth = 3;
  ctx.lineJoin = "round";
  ctx.stroke();

  // Point markers
  values.forEach((v, i) => {
    ctx.beginPath();
    ctx.arc(xAt(i), yAt(v), 3.5, 0, Math.PI * 2);
    ctx.fillStyle = "#fff";
    ctx.fill();
    ctx.lineWidth = 2;
    ctx.strokeStyle = brand;
    ctx.stroke();
  });

  // Labels
  ctx.fillStyle = muted;
  ctx.font = '12px Inter, sans-serif';
  ctx.fillText(`${max.toFixed(2)} ${data.unit}`, 6, padding + 4);
  ctx.fillText(`${min.toFixed(2)} ${data.unit}`, 6, h - padding + 4);

  labels.forEach((label, i) => {
    if (labels.length > 10 && i % 2 !== 0 && i !== labels.length - 1) return;
    ctx.fillText(label, xAt(i) - ctx.measureText(label).width / 2, h - padding + 22);
  });
}

document.addEventListener("DOMContentLoaded", () => {
  renderSparklines();
  renderTrendChart();
});
