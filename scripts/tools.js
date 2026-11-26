/* ==========================================================================
   Radar — shared calculator engine
   Powers every registry-generated calculator under /tools/.
   All calculations run locally in the browser; no inputs are transmitted.
   ========================================================================== */

"use strict";

const escCalc = window.escapeHtml || function (value) {
  return String(value ?? "").replace(/[&<>"']/g, ch => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;", "'": "&#39;"
  }[ch]));
};

const inrWhole = new Intl.NumberFormat("en-IN", { maximumFractionDigits: 0 });
const inrPrecise = new Intl.NumberFormat("en-IN", { maximumFractionDigits: 2 });

function money(n) {
  if (!isFinite(n)) return "—";
  return "₹" + inrPrecise.format(n);
}

function money0(n) {
  if (!isFinite(n)) return "—";
  return "₹" + inrWhole.format(n);
}

function num(n, places) {
  if (!isFinite(n)) return "—";
  return Number(n).toLocaleString("en-IN", { minimumFractionDigits: places || 2, maximumFractionDigits: places || 2 });
}

function pct(n, places) {
  if (!isFinite(n)) return "—";
  return num(n, places === undefined ? 2 : places) + "%";
}

function item(label, value, note, tone) {
  return { label: label, value: value, note: note || "", tone: tone || "" };
}

function emiOf(principal, annualRate, years) {
  const n = Math.max(1, Math.round(years * 12));
  const r = annualRate / 1200;
  if (r <= 0) return principal / n;
  const factor = Math.pow(1 + r, n);
  return principal * r * factor / (factor - 1);
}

function loanSchedule(principal, annualRate, years) {
  const n = Math.max(1, Math.round(years * 12));
  const r = annualRate / 1200;
  const emi = emiOf(principal, annualRate, years);
  let balance = principal;
  let cumInterest = 0;
  let cumPrincipal = 0;
  const rows = [];
  for (let month = 1; month <= n; month++) {
    const interest = balance * r;
    let component = emi - interest;
    let payment = emi;
    if (component >= balance) {
      component = balance;
      payment = interest + component;
    }
    const opening = balance;
    balance = Math.max(0, balance - component);
    cumInterest += interest;
    cumPrincipal += component;
    rows.push({
      month: month,
      year: Math.ceil(month / 12),
      opening: opening,
      interest: interest,
      principal: component,
      closing: balance,
      payment: payment,
      cumInterest: cumInterest,
      cumPrincipal: cumPrincipal
    });
    if (balance <= 0.0001) break;
  }
  return { rows: rows, emi: emi, rate: r, months: n, totalInterest: cumInterest };
}

function annuityFactor(monthlyRate, months) {
  if (monthlyRate <= 0) return months;
  return (Math.pow(1 + monthlyRate, months) - 1) / monthlyRate;
}

function simulateRemaining(balance, emi, monthlyRate, cap) {
  let months = 0;
  let interest = 0;
  while (balance > 0.0001 && months < cap) {
    const part = balance * monthlyRate;
    let principal = emi - part;
    if (principal >= balance) principal = balance;
    if (principal <= 0) break;
    interest += part;
    balance -= principal;
    months++;
  }
  return { months: months, interest: interest, balance: balance };
}

function safeDivide(a, b, fallback) {
  return Math.abs(b) < 0.0000001 ? fallback : a / b;
}

const CALCULATORS = {
  "emi-calculator": function (v) {
    const n = Math.round(v.years * 12);
    const emi = emiOf(v.amount, v.rate, v.years);
    const total = emi * n;
    const interest = total - v.amount;
    return {
      items: [
        item("Monthly EMI", money(emi), "Fixed payment each month", "primary"),
        item("Total interest", money(interest), pct(safeDivide(interest, v.amount, 0) * 100) + " of principal"),
        item("Total payable", money(total), "Principal plus interest"),
        item("Principal share", pct(safeDivide(v.amount, total, 0) * 100), "Rest is the cost of credit")
      ]
    };
  },

  "loan-affordability": function (v) {
    const maxEmi = Math.max(0, v.income * v.foir / 100 - v.existing);
    const n = Math.round(v.years * 12);
    const r = v.rate / 1200;
    const maxLoan = r > 0 ? maxEmi * (Math.pow(1 + r, n) - 1) / (r * Math.pow(1 + r, n)) : maxEmi * n;
    return {
      items: [
        item("Affordable EMI", money(maxEmi), "After existing obligations", "primary"),
        item("Maximum loan", money(maxLoan), "At the selected rate and tenure"),
        item("Comfortable range", money(maxLoan * 0.7) + " – " + money(maxLoan), "70–100% of the cap"),
        item("Debt burden", pct(safeDivide(maxEmi, v.income, 0) * 100), "Share of take-home income")
      ]
    };
  },

  "interest-principal-split": function (v) {
    const plan = loanSchedule(v.amount, v.rate, v.years);
    const at = Math.min(Math.max(1, Math.round(v.month)), plan.rows.length);
    const row = plan.rows[at - 1];
    return {
      items: [
        item("Instalment #" + at, money(row.payment), "Monthly EMI", "primary"),
        item("Interest component", money(row.interest), pct(safeDivide(row.interest, row.payment, 0) * 100) + " of EMI", "warning"),
        item("Principal component", money(row.principal), pct(safeDivide(row.principal, row.payment, 0) * 100) + " of EMI", "positive"),
        item("Balance after payment", money(row.closing), "Opening balance " + money(row.opening))
      ],
      table: {
        title: "Split at a glance",
        headers: ["Component", "Amount", "Share of EMI"],
        rows: [
          ["Interest", money(row.interest), pct(safeDivide(row.interest, row.payment, 0) * 100)],
          ["Principal", money(row.principal), pct(safeDivide(row.principal, row.payment, 0) * 100)],
          ["Total EMI", money(row.payment), "100.00%"]
        ],
        filename: "radar-principal-split.csv"
      }
    };
  },

  "amortization-schedule": function (v) {
    const plan = loanSchedule(v.amount, v.rate, v.years);
    let rows = [];
    let headers = [];
    if (v.view === "monthly") {
      headers = ["Month", "Opening", "Interest", "Principal", "Closing", "Cumulative interest"];
      rows = plan.rows.map(r => [String(r.month), money0(r.opening), money0(r.interest), money0(r.principal), money0(r.closing), money0(r.cumInterest)]);
    } else {
      headers = ["Year", "Opening", "Interest paid", "Principal repaid", "Closing", "Cumulative interest"];
      const byYear = {};
      plan.rows.forEach(r => {
        if (!byYear[r.year]) byYear[r.year] = { opening: r.opening, interest: 0, principal: 0, closing: r.closing, cumInterest: r.cumInterest };
        const y = byYear[r.year];
        y.interest += r.interest;
        y.principal += r.principal;
        y.closing = r.closing;
        y.cumInterest = r.cumInterest;
      });
      rows = Object.keys(byYear).map(year => {
        const y = byYear[year];
        return [year, money0(y.opening), money0(y.interest), money0(y.principal), money0(y.closing), money0(y.cumInterest)];
      });
    }
    return {
      items: [
        item("Monthly EMI", money(plan.emi), "Constant payment", "primary"),
        item("Total interest", money(plan.totalInterest), "Over " + plan.rows.length + " instalments", "warning"),
        item("Total payable", money(v.amount + plan.totalInterest), "Principal plus interest"),
        item("Schedule rows", String(rows.length), v.view === "monthly" ? "Monthly detail" : "Yearly summary")
      ],
      table: {
        title: "Repayment schedule (" + v.view + ")",
        headers: headers,
        rows: rows,
        filename: "radar-amortization-" + v.view + ".csv"
      }
    };
  },

  "prepayment-impact": function (v) {
    const base = loanSchedule(v.amount, v.rate, v.years);
    const at = Math.min(Math.max(1, Math.round(v.month)), base.rows.length);
    const opening = base.rows[at - 1].closing;
    const extra = Math.min(v.prepay, opening);
    const after = simulateRemaining(opening - extra, base.emi, base.rate, base.months * 2);
    const totalMonths = at + after.months;
    const newInterest = base.rows[at - 1].cumInterest + after.interest;
    const savedInterest = Math.max(0, base.totalInterest - newInterest);
    const savedMonths = Math.max(0, base.months - totalMonths);
    return {
      items: [
        item("Interest saved", money(savedInterest), pct(safeDivide(savedInterest, base.totalInterest, 0) * 100) + " of original interest", "positive"),
        item("Tenure reduction", savedMonths + " months", "About " + num(savedMonths / 12, 1) + " years", "primary"),
        item("New payoff", "Month " + totalMonths, "After " + num(totalMonths / 12, 1) + " years"),
        item("Prepayment applied", money(extra), "After instalment #" + at)
      ],
      table: {
        title: "Before vs after prepayment",
        headers: ["Scenario", "Total months", "Total interest", "Final balance"],
        rows: [
          ["Original loan", String(base.months), money(base.totalInterest), money0(0)],
          ["With prepayment", String(totalMonths), money(newInterest), money0(after.balance)]
        ],
        filename: "radar-prepayment-impact.csv"
      }
    };
  },

  "loan-comparison": function (v) {
    const offer = (rate, years, fee) => {
      const n = Math.round(years * 12);
      const emi = emiOf(v.amount, rate, years);
      const interest = emi * n - v.amount;
      return { emi: emi, n: n, interest: interest, allIn: emi * n + fee, fee: fee };
    };
    const a = offer(v.rateA, v.yearsA, v.feeA);
    const b = offer(v.rateB, v.yearsB, v.feeB);
    const winner = a.allIn <= b.allIn ? "A" : "B";
    const saving = Math.abs(a.allIn - b.allIn);
    return {
      items: [
        item("Cheaper offer", "Offer " + winner, "On all-in cost", "primary"),
        item("Cost difference", money(saving), "Include fees, not just rate", "positive"),
        item("Offer A EMI", money(a.emi), pct(v.rateA, 2) + " for " + v.yearsA + " years"),
        item("Offer B EMI", money(b.emi), pct(v.rateB, 2) + " for " + v.yearsB + " years")
      ],
      table: {
        title: "Offer comparison",
        headers: ["Metric", "Offer A", "Offer B"],
        rows: [
          ["Interest rate", pct(v.rateA), pct(v.rateB)],
          ["Tenure", v.yearsA + " years", v.yearsB + " years"],
          ["Monthly EMI", money(a.emi), money(b.emi)],
          ["Total interest", money(a.interest), money(b.interest)],
          ["Fees", money(a.fee), money(b.fee)],
          ["All-in cost", money(a.allIn), money(b.allIn)]
        ],
        filename: "radar-loan-comparison.csv"
      }
    };
  },

  "fd-maturity": function (v) {
    const m = Number(v.comp);
    const periods = Math.max(1, Math.round(v.years * m));
    const factor = Math.pow(1 + v.rate / 100 / m, periods);
    const maturity = v.principal * factor;
    const interest = maturity - v.principal;
    const effective = (factor - 1) * 100;
    const postTax = v.principal + interest * (1 - v.tax / 100);
    return {
      items: [
        item("Maturity value", money(maturity), "Before tax", "primary"),
        item("Interest earned", money(interest), pct(effective) + " effective over the tenure", "positive"),
        item("Post-tax maturity", money(postTax), "At " + pct(v.tax, 0) + " tax rate"),
        item("Compounding", m + " times a year", "Frequency used by the bank")
      ]
    };
  },

  "rd-maturity": function (v) {
    const m = Number(v.comp);
    const months = Math.max(1, Math.round(v.years * 12));
    const monthlyRate = Math.pow(1 + v.rate / 100 / m, m / 12) - 1;
    const maturity = v.monthly * annuityFactor(monthlyRate, months);
    const invested = v.monthly * months;
    const interest = maturity - invested;
    return {
      items: [
        item("Maturity value", money(maturity), "After " + months + " deposits", "primary"),
        item("Amount invested", money(invested), "Total of monthly deposits"),
        item("Interest earned", money(interest), "Compounded at " + pct(v.rate) + " p.a.", "positive"),
        item("Growth multiple", num(safeDivide(maturity, invested, 0), 2) + "×", "Maturity ÷ invested")
      ]
    };
  },

  "sip-returns": function (v) {
    const months = Math.max(1, Math.round(v.years * 12));
    const monthlyRate = Math.pow(1 + v.return / 100, 1 / 12) - 1;
    let balance = 0;
    let invested = 0;
    for (let month = 1; month <= months; month++) {
      const yearIndex = Math.floor((month - 1) / 12);
      const contribution = v.monthly * Math.pow(1 + v.step / 100, yearIndex);
      balance = balance * (1 + monthlyRate) + contribution;
      invested += contribution;
    }
    const gain = balance - invested;
    return {
      items: [
        item("Maturity value", money(balance), "With annual step-up", "primary"),
        item("Amount invested", money(invested), "Total contributions", "warning"),
        item("Wealth gained", money(gain), pct(safeDivide(gain, invested, 0) * 100) + " on invested", "positive"),
        item("Growth multiple", num(safeDivide(balance, invested, 0), 2) + "×", "Assumed return " + pct(v.return) + " p.a.")
      ],
      table: {
        title: "Year-by-year SIP projection",
        headers: ["Year", "Invested till date", "Portfolio value"],
        rows: (() => {
          let bal = 0;
          let inv = 0;
          const out = [];
          for (let year = 1; year <= Math.round(v.years); year++) {
            for (let m = 1; m <= 12; m++) {
              const yearIndex = year - 1;
              bal = bal * (1 + monthlyRate) + v.monthly * Math.pow(1 + v.step / 100, yearIndex);
              inv += v.monthly * Math.pow(1 + v.step / 100, yearIndex);
            }
            out.push([String(year), money0(inv), money0(bal)]);
          }
          return out;
        })(),
        filename: "radar-sip-projection.csv"
      }
    };
  },

  "cagr": function (v) {
    const cagr = Math.pow(v.final / v.initial, 1 / v.years) - 1;
    const real = (1 + cagr) / (1 + v.inflation / 100) - 1;
    return {
      items: [
        item("CAGR", pct(cagr * 100), "Per year over " + v.years + " years", "primary"),
        item("Absolute return", pct((v.final / v.initial - 1) * 100), "Total growth"),
        item("Growth multiple", num(v.final / v.initial, 2) + "×", "Final ÷ initial", "positive"),
        item("Real CAGR", pct(real * 100), "After " + pct(v.inflation) + " inflation", "warning")
      ]
    };
  },

  "compound-interest": function (v) {
    const m = Number(v.comp);
    const yearlyFactor = Math.pow(1 + v.rate / 100 / m, m);
    let balance = v.principal;
    for (let year = 0; year < Math.round(v.years); year++) {
      balance = balance * yearlyFactor + v.contribution;
    }
    const invested = v.principal + v.contribution * v.years;
    const interest = balance - invested;
    return {
      items: [
        item("Future value", money(balance), "After " + v.years + " years", "primary"),
        item("Total invested", money(invested), "Principal plus contributions"),
        item("Interest earned", money(interest), pct(safeDivide(interest, invested, 0) * 100) + " on invested", "positive"),
        item("Interest share", pct(safeDivide(interest, balance, 0) * 100), "Of the final corpus")
      ],
      table: {
        title: "Growth by year",
        headers: ["Year", "Balance"],
        rows: (() => {
          let bal = v.principal;
          const out = [["0", money0(bal)]];
          for (let year = 1; year <= Math.round(v.years); year++) {
            bal = bal * yearlyFactor + v.contribution;
            out.push([String(year), money0(bal)]);
          }
          return out;
        })(),
        filename: "radar-compound-growth.csv"
      }
    };
  },

  "simple-interest": function (v) {
    const interest = v.principal * v.rate / 100 * v.days / 365;
    const maturity = v.principal + interest;
    const postTax = v.principal + interest * (1 - v.tax / 100);
    const yieldPct = interest / v.principal * 365 / v.days * 100;
    return {
      items: [
        item("Simple interest", money(interest), "For " + v.days + " days", "primary"),
        item("Maturity amount", money(maturity), "Principal plus interest"),
        item("Post-tax interest", money(postTax), "At " + pct(v.tax, 0) + " tax rate", "positive"),
        item("Effective annual yield", pct(yieldPct), "No compounding applied")
      ]
    };
  },

  "life-cover": function (v) {
    const i = v.inflation / 100;
    const need = i > 0 ? v.expenses * (Math.pow(1 + i, v.years) - 1) / i : v.expenses * v.years;
    const gap = need + v.debt - v.assets - v.cover;
    const suggested = Math.max(0, gap);
    return {
      items: [
        item("Future family needs", money(need), "Inflation-adjusted expenses", "primary"),
        item("Cover gap", money(gap), "Needs + debt − assets − cover", "warning"),
        item("Suggested term cover", money(suggested), "Round up to a convenient band", "positive"),
        item("Income replacement", num(safeDivide(suggested, v.income, 0), 1) + "×", "Cover ÷ annual income")
      ]
    };
  },

  "term-premium-estimator": function (v) {
    const base = 220 + Math.pow(Math.max(0, v.age - 25), 1.35) * 9;
    const smokerFactor = v.smoker === "yes" ? 1.8 : 1;
    const genderFactor = v.gender === "female" ? 0.85 : 1;
    const termFactor = Math.max(0.8, Math.min(1.2, 0.85 + v.term * 0.005));
    const perLakh = base * smokerFactor * genderFactor * termFactor;
    const annual = v.cover / 100000 * perLakh;
    return {
      items: [
        item("Estimated annual premium", money(annual), "Illustrative tariff", "primary"),
        item("Estimated monthly", money(annual / 12), "If paid monthly"),
        item("Per ₹1 lakh cover", money(perLakh), "Annual rate band"),
        item("Quote range", money(annual * 0.85) + " – " + money(annual * 1.2), "Insurers price differently", "warning")
      ]
    };
  },

  "health-cover-gap": function (v) {
    const bases = { metro: 500000, tier2: 300000, tier3: 200000 };
    const factors = { none: 1, one: 1.4, multiple: 1.8 };
    const recommended = (bases[v.tier] || bases.metro) * v.members * (factors[v.condition] || 1);
    const existing = v.existing + v.employer;
    const gap = Math.max(0, recommended - existing);
    return {
      items: [
        item("Recommended cover", money(recommended), "For " + v.members + " members", "primary"),
        item("Existing cover", money(existing), "Personal plus employer"),
        item("Cover gap", money(gap), gap > 0 ? "Buy a portable family floater" : "Adequate for this estimate", gap > 0 ? "warning" : "positive"),
        item("Premium range", money(gap * 0.006) + " – " + money(gap * 0.012), "Very rough annual estimate")
      ]
    };
  },

  "emergency-fund": function (v) {
    const extra = v.stability === "contract" ? 3 : (v.stability === "business" ? 6 : 0);
    const months = Math.min(18, 6 + v.dependents + extra);
    const target = v.expenses * months;
    const gap = Math.max(0, target - v.corpus);
    const coverage = safeDivide(v.corpus, v.expenses, 0);
    return {
      items: [
        item("Target corpus", money(target), months + " months of expenses", "primary"),
        item("Current coverage", num(coverage, 1) + " months", "Based on current corpus"),
        item("Gap", money(gap), gap > 0 ? "Still to build" : "Fully funded", gap > 0 ? "warning" : "positive"),
        item("Monthly saving needed", money(gap / v.monthsToBuild), "Over " + v.monthsToBuild + " months")
      ]
    };
  },

  "retirement-corpus": function (v) {
    const toRetire = Math.max(1, v.retire - v.age);
    const inRetirement = Math.max(1, v.life - v.retire);
    const firstExpense = v.monthly * 12 * Math.pow(1 + v.inflation / 100, toRetire);
    const realRate = (1 + v.return / 100) / (1 + v.inflation / 100) - 1;
    const need = Math.abs(realRate) < 0.000001 ? firstExpense * inRetirement : firstExpense * (1 - Math.pow(1 + realRate, -inRetirement)) / realRate;
    const existingFv = v.corpus * Math.pow(1 + v.return / 100, toRetire);
    const shortfall = Math.max(0, need - existingFv);
    const months = toRetire * 12;
    const monthlyRate = Math.pow(1 + v.return / 100, 1 / 12) - 1;
    const sip = shortfall / annuityFactor(monthlyRate, months);
    return {
      items: [
        item("Corpus needed", money(need), "At retirement age " + v.retire, "primary"),
        item("First-year expense", money(firstExpense), "Inflated to retirement"),
        item("Monthly SIP required", money(sip), "For " + toRetire + " years", "positive"),
        item("Existing corpus FV", money(existingFv), "Grown at " + pct(v.return) + " p.a.")
      ]
    };
  },

  "goal-savings": function (v) {
    const years = Math.max(0.5, v.years);
    const growth = Math.pow(1 + v.return / 100, years);
    const currentFv = v.current * growth;
    const shortfall = Math.max(0, v.target - currentFv);
    const months = Math.max(1, Math.round(years * 12));
    const monthlyRate = Math.pow(1 + v.return / 100, 1 / 12) - 1;
    const sip = shortfall / annuityFactor(monthlyRate, months);
    const lumpsum = shortfall / growth;
    return {
      items: [
        item("Monthly SIP needed", money(sip), "To reach " + money(v.target), "primary"),
        item("Lumpsum needed today", money(lumpsum), "If invested now", "positive"),
        item("Current savings FV", money(currentFv), "At " + pct(v.return) + " p.a."),
        item("Shortfall without returns", money(Math.max(0, v.target - v.current)), "Simple gap")
      ]
    };
  },

  "budget-split": function (v) {
    const needs = v.income * 0.5;
    const wants = v.income * 0.3;
    const savings = v.income * 0.2;
    const flex = v.income - v.fixed - v.goal - wants;
    const fixedGap = v.fixed - needs;
    return {
      items: [
        item("Needs (50%)", money(needs), "Includes fixed obligations", "primary"),
        item("Wants (30%)", money(wants), "Lifestyle and discretionary"),
        item("Savings (20%)", money(savings), "Investments and buffers", "positive"),
        item(flex >= 0 ? "Flexible balance" : "Budget shortfall", money(Math.abs(flex)), flex >= 0 ? "Left after fixed, goal and wants" : "Trim fixed costs or wants", flex >= 0 ? "positive" : "warning")
      ],
      table: {
        title: "Your 50/30/20 plan",
        headers: ["Bucket", "Amount", "Share"],
        rows: [
          ["Needs", money(needs), "50.00%"],
          ["Wants", money(wants), "30.00%"],
          ["Savings", money(savings), "20.00%"],
          ["Fixed obligations", money(v.fixed), pct(safeDivide(v.fixed, v.income, 0) * 100)],
          ["Savings goal", money(v.goal), pct(safeDivide(v.goal, v.income, 0) * 100)],
          ["Fixed vs needs", money(fixedGap), fixedGap > 0 ? "Above the 50% guide" : "Within the 50% guide"]
        ],
        filename: "radar-budget-plan.csv"
      }
    };
  },

  "inflation-adjuster": function (v) {
    const factor = Math.pow(1 + v.inflation / 100, v.years);
    const adjusted = v.direction === "future" ? v.amount * factor : v.amount / factor;
    return {
      items: [
        item("Adjusted value", money(adjusted), v.direction === "future" ? "Future rupees" : "Today's rupees", "primary"),
        item("Inflation multiple", num(factor, 3) + "×", "Over " + v.years + " years"),
        item("Price-level change", pct((factor - 1) * 100), "Cumulative effect"),
        item("Original amount", money(v.amount), "Before adjustment")
      ]
    };
  },

  "net-worth": function (v) {
    const assets = v.cash + v.bank + v.funds + v.property + v.gold;
    const liquid = v.cash + v.bank + v.funds;
    const liabilities = v.homeLoan + v.otherLoan + v.card;
    const net = assets - liabilities;
    return {
      items: [
        item("Net worth", money(net), "Assets minus liabilities", net >= 0 ? "primary" : "warning"),
        item("Total assets", money(assets), "Including property", "positive"),
        item("Total liabilities", money(liabilities), "All loans and dues", "warning"),
        item("Financial asset share", pct(safeDivide(liquid, assets, 0) * 100), "Cash, deposits and markets")
      ],
      table: {
        title: "Balance sheet snapshot",
        headers: ["Category", "Amount"],
        rows: [
          ["Cash", money(v.cash)], ["Bank deposits", money(v.bank)],
          ["Funds and shares", money(v.funds)], ["Property", money(v.property)],
          ["Gold and other", money(v.gold)], ["Home loan", money(v.homeLoan)],
          ["Other loans", money(v.otherLoan)], ["Credit-card dues", money(v.card)]
        ],
        filename: "radar-net-worth.csv"
      }
    };
  }
};

let lastCalcTable = null;

function renderCalcResult(output) {
  const host = document.getElementById("calc-result");
  if (!host) return;
  if (!output || !output.items) {
    host.innerHTML = '<div class="calc-result-error">This calculator is not available. Please refresh the page.</div>';
    return;
  }
  const cards = output.items.map(x =>
    '<div class="calc-result-card ' + escCalc(x.tone) + '">' +
    '<span>' + escCalc(x.label) + '</span>' +
    '<strong>' + escCalc(x.value) + '</strong>' +
    (x.note ? '<small>' + escCalc(x.note) + '</small>' : '') +
    '</div>'
  ).join("");

  let tableHtml = "";
  lastCalcTable = output.table || null;
  if (lastCalcTable && lastCalcTable.rows && lastCalcTable.rows.length) {
    const head = lastCalcTable.headers.map(h => "<th>" + escCalc(h) + "</th>").join("");
    const body = lastCalcTable.rows.map(row =>
      "<tr>" + row.map(cell => "<td>" + escCalc(cell) + "</td>").join("") + "</tr>"
    ).join("");
    tableHtml =
      '<div class="calc-table-block">' +
      '<div class="calc-table-head"><h3>' + escCalc(lastCalcTable.title) + '</h3>' +
      '<button type="button" id="calc-download" class="btn btn-quiet small">Download CSV</button></div>' +
      '<div class="calc-table-wrap"><table class="data-table calc-table"><thead><tr>' + head + '</tr></thead><tbody>' + body + '</tbody></table></div>' +
      '</div>';
  }

  host.innerHTML = '<div class="calc-result-grid">' + cards + '</div>' + tableHtml;
  const download = document.getElementById("calc-download");
  if (download) download.addEventListener("click", downloadCalcCsv);
}

function downloadCalcCsv() {
  if (!lastCalcTable) return;
  const escapeCell = value => '"' + String(value).replace(/"/g, '""') + '"';
  const lines = [lastCalcTable.headers, ...lastCalcTable.rows].map(row => row.map(escapeCell).join(","));
  const blob = new Blob([lines.join("\r\n")], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = lastCalcTable.filename || "radar-calculator.csv";
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

function initRegistryCalculator() {
  const configEl = document.getElementById("calc-config");
  if (!configEl) return;
  let tool;
  try {
    tool = JSON.parse(configEl.textContent);
  } catch (err) {
    renderCalcResult(null);
    return;
  }

  const form = document.getElementById("calc-form");
  if (!form) return;

  form.innerHTML = tool.fields.map(f => {
    const label = escCalc(f.label) + (f.unit ? ' <span class="field-unit">' + escCalc(f.unit) + '</span>' : '');
    let control;
    if (f.kind === "select") {
      const options = (f.options || []).map(o =>
        '<option value="' + escCalc(o[0]) + '"' + (String(o[0]) === String(f.default) ? " selected" : "") + '>' + escCalc(o[1]) + '</option>'
      ).join("");
      control = '<select id="calc-' + escCalc(f.key) + '">' + options + '</select>';
    } else {
      const min = f.min === null || f.min === undefined ? "" : ' min="' + f.min + '"';
      const max = f.max === null || f.max === undefined ? "" : ' max="' + f.max + '"';
      const step = f.step === null || f.step === undefined ? ' step="any"' : ' step="' + f.step + '"';
      control = '<input type="number" id="calc-' + escCalc(f.key) + '" value="' + f.default + '"' + min + max + step + ' />';
    }
    const help = f.help ? '<small>' + escCalc(f.help) + '</small>' : '';
    return '<label class="field calc-field"><span>' + label + '</span>' + control + help + '</label>';
  }).join("");

  function readValues() {
    const values = {};
    tool.fields.forEach(f => {
      const el = document.getElementById("calc-" + f.key);
      if (!el) return;
      values[f.key] = f.kind === "select" ? el.value : Number(el.value);
    });
    return values;
  }

  function run() {
    const fn = CALCULATORS[tool.id];
    if (!fn) {
      renderCalcResult(null);
      return;
    }
    try {
      renderCalcResult(fn(readValues()));
    } catch (err) {
      console.error("Radar calculator error:", err);
      renderCalcResult(null);
    }
  }

  function reset() {
    tool.fields.forEach(f => {
      const el = document.getElementById("calc-" + f.key);
      if (el) el.value = f.default;
    });
    run();
  }

  document.getElementById("calc-run").addEventListener("click", run);
  document.getElementById("calc-reset").addEventListener("click", reset);
  form.addEventListener("submit", e => { e.preventDefault(); run(); });
  form.addEventListener("input", () => { if (lastCalcTable) run(); });
  run();
}

document.addEventListener("DOMContentLoaded", initRegistryCalculator);
