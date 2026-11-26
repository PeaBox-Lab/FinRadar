/* ==========================================================================
   Radar — client script
   Renders live KPIs, benchmarks, tools and peer rankings from the
   data/latest_kpis.json file that the daily pipeline produces.
   ========================================================================== */

"use strict";

// Pages live both at the site root and in subfolders (category/, kpi/, ...).
// The generator emits the correct relative prefix on <body data-base>.
const SITE_BASE = document.body.dataset.base || "";
const LIVE_DATA_URL = `${SITE_BASE}data/latest_kpis.json`;
const SNAPSHOT_URL = `${SITE_BASE}data/snapshots/indicators.json`;
const BADGE_TEXT = "Static Snapshot • Updated Monthly (Not Live)";

function monthLabel(stamp) {
  if (!stamp) return "Unknown";
  const date = new Date(`${String(stamp).slice(0, 7)}-01T00:00:00Z`);
  return Number.isNaN(date.getTime())
    ? String(stamp)
    : date.toLocaleString("en-GB", { month: "long", year: "numeric", timeZone: "UTC" });
}

function snapshotBadge(data) {
  return `<span class="snapshot-badge">${BADGE_TEXT}<span class="snapshot-updated">Last Updated: ${monthLabel(data?.last_updated_month)}</span></span>`;
}

async function loadKPIs() {
  try {
    const res = await fetch(LIVE_DATA_URL);
    if (!res.ok) throw new Error("not ok: " + res.status);
    return await res.json();
  } catch (err) {
    console.warn("Radar: live data unavailable, using snapshot.");
    const res = await fetch(SNAPSHOT_URL);
    if (!res.ok) throw new Error("snapshot not ok: " + res.status);
    return res.json();
  }
}

function humanizeNumber(n) {
  if (n === null || n === undefined || !isFinite(n)) return "—";
  return n >= 1000 ? n.toLocaleString("en-IN", { maximumFractionDigits: 1 }) : String(n.toFixed(2));
}

/* ---------------- KPI grid ---------------- */

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, ch => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;", "'": "&#39;"
  }[ch]));
}

function verdictClass(verdict) {
  const v = (verdict || "").toLowerCase();
  if (v === "strong" || v === "on target" || v === "good") return "good";
  if (v === "moderate" || v === "near target") return "moderate";
  return "weak";
}

function renderKPI(k, data) {
  const el = document.createElement("article");
  el.className = "card kpi-card";
  const sourceType = k.source_type || (k.source_live === false ? "curated_snapshot" : "live_api");
  const isLive = sourceType === "live_api";

  let statusBadge = `<span class="live-badge">Live API</span>`;
  if (sourceType === "curated_snapshot") {
    el.classList.add("snapshot-kpi");
    statusBadge = snapshotBadge(data);
  } else if (sourceType === "unavailable") {
    el.classList.add("unavailable-kpi");
    statusBadge = `<span class="snapshot-badge unavailable">Official series unavailable — no value published</span>`;
  }

  const parts = [];
  parts.push(`<div class="kpi-top">
    <span class="kpi-sector">${escapeHtml(k.sector || "General")}</span>
    ${statusBadge}
  </div>`);
  parts.push(`<h3 class="kpi-name">${escapeHtml(k.name || "")}</h3>`);
  if (k.value != null) {
    parts.push(`<div class="kpi-value">${humanizeNumber(k.value)}<span class="kpi-unit">${escapeHtml(k.unit || "")}</span></div>`);
  } else {
    parts.push(`<div class="kpi-value">—</div>`);
  }
  if (k.verdict) {
    parts.push(`<span class="verdict-badge ${verdictClass(k.verdict)}">${escapeHtml(k.verdict.toUpperCase())}</span>`);
  }
  if (k.insight_text) parts.push(`<p class="kpi-sub clamp-2">${escapeHtml(k.insight_text)}</p>`);
  else if (k.subtitle) parts.push(`<div class="kpi-sub">${escapeHtml(k.subtitle)}</div>`);
  if (k.benchmark) parts.push(`<p class="kpi-meta">${escapeHtml(k.benchmark)}</p>`);
  else if (k.source_resource_id) parts.push(`<p class="kpi-meta">${escapeHtml(k.source_resource_id)}</p>`);
  if (k.kpi_id) {
    parts.push(`<a class="kpi-link" href="kpi/${encodeURIComponent(k.kpi_id)}.html">View detail →</a>`);
  }
  el.innerHTML = parts.join("");
  return el;
}

function renderKPIs(data) {
  const grid = document.getElementById("kpi-grid");
  if (!grid || !data.kpis) return;
  data.kpis.forEach(k => grid.appendChild(renderKPI(k, data)));
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
    const score = data.benchmarks.india_macro_cycle_score;
    const v = document.getElementById("bench-macro-cycle-value");
    if (v) v.textContent = `${score} / 100`;
    const hero = document.getElementById("hero-signal-value");
    if (hero) hero.textContent = score;
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

  const subindices = data?.subindices;
  const publishedWeights = data?.subindex_weights || {};
  const categories = Object.entries(subindices || {})
    .filter(([, value]) => typeof value === "number")
    .map(([name, subindex]) => ({ name, subindex, weight: publishedWeights[name] }));
  if (!categories.length) {
    heading.innerHTML = '<p class="muted">Official CPI sub-indices are unavailable for this build, so the calculator is disabled. No placeholder figures are used.</p>';
    document.getElementById("personal-inflation-btn")?.setAttribute("disabled", "disabled");
    return;
  }
  const n = categories.length;
  // Use published CPI group weights where available; otherwise start from an
  // equal, user-editable split (not presented as an official statistic).
  const baseWeight = Math.floor(100 / n);
  const defaultWeights = categories.map((c, i) =>
    typeof c.weight === "number" ? c.weight : baseWeight + (i < (100 - baseWeight * n) ? 1 : 0));
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
      `<br><small class="muted">Sub-indices: ${escapeHtml(data?.subindex_metadata?.source || "Official CPI release")}${data?.subindex_metadata?.month ? ` (${escapeHtml(data.subindex_metadata.month)}, base ${escapeHtml(data.subindex_metadata.base || "—")})` : ""}. Starting weights are published CPI group weights; change them to match your own spending.</small>`;
  });

  const resetBtn = document.getElementById("personal-inflation-reset");
  if (resetBtn) resetBtn.addEventListener("click", () => {
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

  const cityIndices = data?.city_indices;
  const names = Object.keys(cityIndices || {}).filter(k => typeof cityIndices[k] === "number");
  if (!names.length) {
    result.innerHTML = '<p class="muted">Official city index data is unavailable for this build, so the calculator is disabled. No placeholder figures are used.</p>';
    document.getElementById("salary-parity-btn")?.setAttribute("disabled", "disabled");
    return;
  }

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
      ` <br><small class="muted">City figures: ${escapeHtml(data?.city_indices_metadata?.source || "official city index")}${data?.city_indices_metadata?.month ? ` (${escapeHtml(data.city_indices_metadata.month)}, base ${escapeHtml(data.city_indices_metadata.base || "—")})` : ""}. Published proxy for industrial-worker households, not a general cost-of-living index.</small>`;
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
  let data;
  try {
    data = await loadKPIs();
  } catch (err) {
    console.error("Radar: no KPI data could be loaded.", err);
    return;
  }
  window.__RADAR_DATA__ = data;
  renderKPIs(data);
  renderHeroStats(data);
  renderBenchmarks(data);
  renderPeers(data);
  initPersonalInflationTool(data);
  initSalaryParityTool(data);
  renderFooter(data);
  renderKpiLibrary(data);
});


/* ---------------- Data Lab table filters ---------------- */
function initDataLabFilters() {
  document.querySelectorAll('[data-filter-input]').forEach(input => {
    const target = document.getElementById(input.dataset.filterTarget);
    if (!target) return;
    input.addEventListener('input', () => {
      const term = input.value.trim().toLowerCase();
      target.querySelectorAll('tr').forEach(row => {
        row.hidden = term ? !row.textContent.toLowerCase().includes(term) : false;
      });
    });
  });
}
document.addEventListener('DOMContentLoaded', initDataLabFilters);

/* ---------------- Nav ---------------- */
function initNav() {
  const toggle = document.querySelector('.nav-toggle');
  const nav = document.getElementById('site-nav');
  if (toggle && nav) {
    toggle.addEventListener('click', () => {
      const open = nav.classList.toggle('open');
      toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
  }
  document.querySelectorAll('.nav-drop-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      const drop = btn.closest('.nav-drop');
      const isOpen = drop.classList.contains('open');
      document.querySelectorAll('.nav-drop.open').forEach(d => { if (d !== drop) { d.classList.remove('open'); d.querySelector('.nav-drop-btn')?.setAttribute('aria-expanded','false'); } });
      drop.classList.toggle('open', !isOpen);
      btn.setAttribute('aria-expanded', !isOpen ? 'true' : 'false');
    });
  });
  document.addEventListener('click', (e) => {
    if (!e.target.closest('.nav-drop')) {
      document.querySelectorAll('.nav-drop.open').forEach(d => { d.classList.remove('open'); d.querySelector('.nav-drop-btn')?.setAttribute('aria-expanded','false'); });
    }
  });

  // Highlight the section the reader is in.
  const page = (location.pathname.split('/').pop() || 'index.html').toLowerCase();
  document.querySelectorAll('.nav-primary a').forEach(a => {
    const target = (a.getAttribute('href') || '').split('/').pop().toLowerCase();
    if (target === page || (page === 'index.html' && target === 'index.html')) {
      a.setAttribute('aria-current', 'page');
    }
  });
}
document.addEventListener('DOMContentLoaded', initNav);
