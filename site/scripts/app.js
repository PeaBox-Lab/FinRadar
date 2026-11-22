/* ==========================================================================
   FinRadar — client script
   Renders live KPIs, benchmarks, tools and peer rankings from the
   data/latest_kpis.json file that the daily pipeline produces.
   ========================================================================== */

"use strict";

async function loadKPIs() {
  try {
    const res = await fetch("data/latest_kpis.json");
    if (!res.ok) throw new Error("not ok: " + res.status);
    return await res.json();
  } catch (err) {
    console.warn("FinRadar: live data unavailable, using snapshot.");
    const res = await fetch("data/snapshots/indicators.json");
    return res.json();
  }
}

function humanizeNumber(n) {
  if (n === null || n === undefined || !isFinite(n)) return "—";
  return n >= 1000 ? n.toLocaleString("en-IN", { maximumFractionDigits: 1 }) : String(n.toFixed(2));
}

/* ---------------- KPI grid ---------------- */

function renderKPI(k) {
  const el = document.createElement("div");
  el.className = "kpi-card";
  if (k.value === null || k.value === undefined) el.classList.add("demo");

  const parts = [];
  if (k.value !== null && k.value !== undefined) {
    parts.push(`<div class="kpi-value">${humanizeNumber(k.value)}<span class="kpi-unit"> ${k.unit || ""}</span></div>`);
  } else {
    parts.push(`<div class="kpi-value">—</div>`);
  }
  if (k.subtitle) parts.push(`<div class="kpi-sub">${k.subtitle}</div>`);
  parts.push(`<div class="kpi-meta">${k.source || ""}</div>`);
  if (k.benchmark) parts.push(`<div class="kpi-meta">${k.benchmark}</div>`);
  const isDemo = el.classList.contains("demo");
  parts.push(`<span class="kpi-badge ${isDemo ? "demo" : "live"}">${isDemo ? "demo" : "live"}</span>`);
  el.innerHTML = parts.join("");
  return el;
}

function renderKPIs(data) {
  const grid = document.getElementById("kpi-grid");
  if (!grid || !data.kpis) return;
  data.kpis.forEach(k => grid.appendChild(renderKPI(k)));
}

/* ---------------- Hero stats ---------------- */

function renderHeroStats(data) {
  const container = document.getElementById("hero-stats");
  if (!container || !data) return;
  const items = [];
  if (data.india && data.india.gdp_per_capita_usd != null) {
    items.push(`<span class="stat-pill">₹ <strong>${humanizeNumber(data.india.gdp_per_capita_usd)}</strong> avg economic output per person</span>`);
  }
  if (data.benchmarks && data.benchmarks.india_macro_cycle_score != null) {
    items.push(`<span class="stat-pill">📈 <strong>${data.benchmarks.india_macro_cycle_score}/100</strong> macro cycle score — expansion vs slowdown</span>`);
  }
  if (data.kpis) {
    const strongCount = data.kpis.filter(k => k.verdict === "strong" || k.verdict === "on target").length;
    const total = data.kpis.length;
    if (total) items.push(`<span class="stat-pill">✅ <strong>${strongCount}/${total}</strong> KPIs strong or on target</span>`);
  }
  if (data.peers && data.peers[0] && data.peers[0].rank) {
    items.push(`<span class="stat-pill">🥇 <strong>${data.peers[0].name}: #${data.peers[0].rank}</strong> of ${data.peers.length}</span>`);
  }
  container.innerHTML = items.join("");
}

/* ---------------- Benchmarks ---------------- */

function renderBenchmarks(data) {
  if (data.benchmarks && data.benchmarks.india_macro_cycle_score != null) {
    const v = document.getElementById("bench-macro-cycle-value");
    if (v) v.textContent = `${data.benchmarks.india_macro_cycle_score} / 100`;
  }
  const t = document.getElementById("macro-cycle-readout");
  if (t && data.benchmarks && data.benchmarks.india_macro_cycle_score != null) {
    t.textContent = `${data.benchmarks.india_macro_cycle_score} / 100`;
  }
  if (data.benchmarks && data.benchmarks.global_resilience) {
    const g = data.benchmarks.global_resilience;
    const v = document.getElementById("bench-resilience-value");
    if (v) {
      v.textContent = `# ${g.india_rank_by_real_gdp_growth != null ? g.india_rank_by_real_gdp_growth : "n/a"} of ${g.of}`;
      v.title = (g.peers || []).map(p => `${p.name}: growth ${p.real_gdp_growth != null ? p.real_gdp_growth.toFixed(1) + "%" : "n/a"}`).join(" • ");
    }
  }
}

/* ---------------- KPI Library (sector-grouped) ---------------- */

function renderKpiLibrary(data) {
  const container = document.getElementById("kpi-library");
  if (!container || !data.kpis) return;

  // Group KPIs by sector.
  const bySector = {};
  data.kpis.forEach(k => {
    const sector = k.sector || "General";
    if (!bySector[sector]) bySector[sector] = [];
    bySector[sector].push(k);
  });

  const sortedSectors = Object.keys(bySector).sort();
  const sections = sortedSectors.map(sector => {
    const kpis = bySector[sector];
    const rows = kpis.map(k => {
      const val = k.value != null ? `${humanizeNumber(k.value)}${k.unit ? " " + k.unit : ""}` : "—";
      const verdict = k.verdict ? `<span class="verdict-badge ${k.verdict === "strong" || k.verdict === "on target" ? "good" : k.verdict === "moderate" || k.verdict === "near target" ? "moderate" : "weak"}">${k.verdict.toUpperCase()}</span>` : "";
      return `<tr>
        <td><strong>${k.name}</strong></td>
        <td class="num">${val}</td>
        <td>${verdict}</td>
        <td>${k.insight_text || ""}</td>
        <td><span class="muted small">${k.formula || ""}</span></td>
      </tr>`;
    }).join("");

    return `
      <div class="sector-block">
        <h3 class="sector-title">${sector} <span class="sector-count">${kpis.length} KPIs</span></h3>
        <table class="kpi-library-table">
          <thead><tr><th>KPI</th><th>Value</th><th>Verdict</th><th>What it means</th><th>Formula</th></tr></thead>
          <tbody>${rows}</tbody>
        </table>
      </div>`;
  });

  container.innerHTML = sections.join("");
}

function renderPeers(data) {
  const table = document.getElementById("peers-table");
  if (!table || !data.peers) return;

  table.innerHTML = `
    <thead><tr>
      <th>Rank</th>
      <th>Country</th>
      <th class="th-num">Real GDP Growth</th>
      <th class="th-num">Current Account % of GDP</th>
      <th class="th-num">FDI Inflows % of GDP</th>
    </tr></thead>
    <tfoot><tr>
      <td colspan="5" class="muted"><small>Rank by real GDP growth (World Bank, NY.GDP.MKTP.KD.ZG). India is the 🇮🇳 row.</small></td>
    </tr></tfoot>`;

  const rows = [
    { iso: "IN", name: "India 🇮🇳", real_gdp_growth: data.india?.gdp_growth_pct,
      current_account: data.india?.current_account, fdi_inflows: data.india?.fdi_inflows },
    ...data.peers,
  ].sort((a, b) => {
    const ag = a.real_gdp_growth ?? -Infinity;
    const bg = b.real_gdp_growth ?? -Infinity;
    if (ag !== bg) return bg - ag;
    if (a.iso === "IN") return -1;
    if (b.iso === "IN") return 1;
    return 0;
  });

  rows.forEach((p, idx) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td><span class="rank-badge">#${idx + 1}</span></td>
      <td><strong>${p.name}</strong></td>
      <td class="num">${p.real_gdp_growth != null ? p.real_gdp_growth.toFixed(1) + "%" : "n/a"}</td>
      <td class="num">${p.current_account != null ? p.current_account.toFixed(1) + "%" : "n/a"}</td>
      <td class="num">${p.fdi_inflows != null ? p.fdi_inflows.toFixed(2) + "%" : "n/a"}</td>`;
    table.appendChild(tr);
  });
}

/* ---------------- Tools: Personal Inflation Calculator ---------------- */

function initPersonalInflationTool(data) {
  const table = document.getElementById("personal-inflation-rows");
  const heading = document.getElementById("personal-inflation-result");
  if (!table || !heading) return;

  const subindices = data?.subindices || {
    food: 36, "fuel & light": 7, clothing: 5, education: 3,
    healthcare: 3, housing: 25, "other stuff": 17
  };
  const categories = Object.entries(subindices).map(([name, subindex]) => ({ name, subindex }));
  const n = categories.length;
  // Distribute the total weight 100 evenly (remainder to the first rows).
  const baseWeight = Math.floor(100 / n);
  const defaultWeights = categories.map((c, i) => baseWeight + (i < (100 - baseWeight * n) ? 1 : 0));
  const defaultWeightAt = (i) => defaultWeights[i];

  table.innerHTML = categories.map((c, i) => `
    <tr>
      <td>${c.name}</td>
      <td class="num"><input type="number" id="w-${i}" min="0" max="100" value="${defaultWeightAt(i)}" aria-label="Weight % for ${c.name}"></td>
      <td class="num"><span class="muted" id="s-${i}">${c.subindex}</span></td>
      <td class="num"><input type="number" id="e-${i}" step="0.25" min="0" value="0" aria-label="Extra % for ${c.name}"></td>
      <td class="num"><strong class="adj" id="a-${i}"></strong></td>
    </tr>`).join("");

  const updateAdjusted = () => {
    categories.forEach((c, i) => {
      const extra = parseFloat(document.getElementById(`e-${i}`).value) || 0;
      const adjusted = (parseFloat(document.getElementById(`s-${i}`).textContent) || c.subindex) + extra;
      document.getElementById(`a-${i}`).textContent = adjusted.toFixed(1);
    });
  };

  // Track input changes so the adjusted column updates live.
  table.addEventListener("input", updateAdjusted);
  updateAdjusted();

  document.getElementById("personal-inflation-btn").addEventListener("click", () => {
    let totalWeight = 0, weighted = 0;
    categories.forEach((c, i) => {
      const w = parseFloat(document.getElementById(`w-${i}`).value) || 0;
      const adjusted = parseFloat(document.getElementById(`a-${i}`).textContent) || c.subindex;
      totalWeight += w;
      weighted += (w / 100) * adjusted;
    });
    if (totalWeight === 0) {
      heading.textContent = "Give the weights a total above 0.";
      return;
    }
    const result = weighted / (totalWeight / 100);
    const headline = data?.india?.real_inflation_rate;
    const deltaNote = result > headline + 0.25 ? "You're outpacing the headline — your spending mix is worse than the average person's."
      : result < headline - 0.25 ? "You're running slightly under the headline — your spending feels cheaper than the average person's."
      : "Your personal rate is close to the official headline inflation.";
    heading.innerHTML = `Your personal inflation rate comes to <strong>${result.toFixed(1)}%</strong> — how much your own spending mix is really inflating at.` +
      (headline != null ? ` The official headline is ${headline.toFixed(2)}%. ` + deltaNote : "") +
      `<br><small class="muted">Adjusted sub-indices are illustrative until live MoSPI data is wired in.</small>`;
  });

  document.getElementById("personal-inflation-reset").addEventListener("click", () => {
    categories.forEach((c, i) => {
      document.getElementById(`w-${i}`).value = defaultWeightAt(i);
      document.getElementById(`e-${i}`).value = 0;
      document.getElementById(`a-${i}`).textContent = c.subindex.toFixed(1);
    });
  });
}

/* ---------------- Tools: Salary parity ---------------- */

function initSalaryParityTool(data) {
  const salaryInput = document.getElementById("salary-parity-salary");
  const fromSel = document.getElementById("salary-parity-from");
  const toSel = document.getElementById("salary-parity-to");
  const result = document.getElementById("salary-parity-result");
  if (!salaryInput || !fromSel || !toSel || !result) return;

  const cityIndices = data?.city_indices || { Pune: 120, Mumbai: 130, Delhi: 118, Jaipur: 90, Bengaluru: 115, Hyderabad: 105 };
  const names = Object.keys(cityIndices).filter(k => typeof cityIndices[k] === "number");

  [fromSel, toSel].forEach(sel => {
    sel.innerHTML = names.map(k => `<option>${k}</option>`).join("");
  });
  fromSel.value = "Mumbai";
  toSel.value = "Jaipur";
  salaryInput.value = 200000;

  document.getElementById("salary-parity-btn").addEventListener("click", () => {
    const base = parseFloat(salaryInput.value);
    const from = cityIndices[fromSel.value];
    const to = cityIndices[toSel.value];
    if (!base || !from || !to) {
      result.innerHTML = "Enter a salary and pick two cities above.";
      return;
    }
    const parity = Math.round(base * (to / from) * 10) / 10;
    const direction = from > to ? "Your money buys more there, so the equivalent salary is smaller."
      : "Your money buys less there, so the equivalent salary is bigger.";
    result.innerHTML = `<strong>₹${parity.toLocaleString("en-IN")}</strong> — the salary in <strong>${toSel.value}</strong> that matches your <strong>₹${base.toLocaleString("en-IN")}</strong> in <strong>${fromSel.value}</strong> for purchasing power.` +
      ` <br>${direction}` +
      ` <br><small class="muted">City indices are illustrative until live MoSPI data is wired in.</small>`;
  });
}

/* ---------------- Footer ---------------- */

function renderFooter(data) {
  const el = document.getElementById("last-refresh");
  const footerEl = document.getElementById("footer-refresh");
  const stamp = data?.generated_at;
  const pretty = stamp ? new Date(stamp).toLocaleString("en-IN") : "—";
  if (el) el.textContent = pretty;
  if (footerEl) footerEl.textContent = pretty;
  const wbGdp = document.getElementById("wb-gdp-cap");
  if (wbGdp) wbGdp.textContent = humanizeNumber(data?.india?.gdp_per_capita_usd);
}

/* ---------------- Boot ---------------- */

document.addEventListener("DOMContentLoaded", async () => {
  const data = await loadKPIs();
  window.__FINRADAR_DATA__ = data;
  renderKPIs(data);
  renderHeroStats(data);
  renderBenchmarks(data);
  renderPeers(data);
  initPersonalInflationTool(data);
  initSalaryParityTool(data);
  renderFooter(data);
  renderKpiLibrary(data);
});
