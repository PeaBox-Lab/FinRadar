/* ==========================================================================
   FinRadar — Extended Client Script
   Adds support for the multi-page architecture: Sparklines, Charts, and Search.
   ========================================================================== */

"use strict";

/**
 * Simple Sparkline Renderer
 * Renders a minimal SVG path from a data-points attribute.
 */
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

    const coords = pts.map((v, i) => {
      const x = (i / (pts.length - 1)) * width;
      const y = height - ((v - min) / range) * height;
      return `${x},${y}`;
    }).join(" ");

    el.innerHTML = `
      <svg width="${width}" height="${height}" style="overflow:visible">
        <polyline points="${coords}" fill="none" stroke="var(--accent)" stroke-width="2" stroke-linejoin="round" />
      </svg>
    `;
  });
}

/**
 * Historical Trend Chart
 * Uses a simple Canvas-based line chart for detail pages.
 */
function renderTrendChart() {
  const canvas = document.getElementById("trend-chart");
  if (!canvas) return;

  const data = window.__TREND_CHART_DATA__;
  if (!data) return;

  const ctx = canvas.getContext("2d");
  const padding = 40;
  const w = canvas.width = canvas.parentElement.clientWidth;
  const h = canvas.height = 300;

  const labels = data.labels;
  const values = data.values;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;

  ctx.clearRect(0, 0, w, h);
  
  // Draw axes
  ctx.strokeStyle = "#444";
  ctx.beginPath();
  ctx.moveTo(padding, padding);
  ctx.lineTo(padding, h - padding);
  ctx.lineTo(w - padding, h - padding);
  ctx.stroke();

  // Draw line
  ctx.strokeStyle = "var(--accent)";
  ctx.lineWidth = 3;
  ctx.beginPath();
  
  values.forEach((v, i) => {
    const x = padding + (i / (values.length - 1)) * (w - 2 * padding);
    const y = (h - padding) - ((v - min) / range) * (h - 2 * padding);
    if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
  });
  ctx.stroke();

  // Labels
  ctx.fillStyle = "#aaa";
  ctx.font = "12px Inter";
  ctx.fillText(max.toFixed(2) + " " + data.unit, 5, padding);
  ctx.fillText(min.toFixed(2) + " " + data.unit, 5, h - padding);
  
  labels.forEach((l, i) => {
    const x = padding + (i / (labels.length - 1)) * (w - 2 * padding);
    ctx.fillText(l, x - 10, h - padding + 20);
  });
}

// Integration into DOMContentLoaded
const originalDOMContentLoaded = document.addEventListener;
// We wrap the logic to ensure it runs on every page
document.addEventListener("DOMContentLoaded", () => {
  renderSparklines();
  renderTrendChart();
});
