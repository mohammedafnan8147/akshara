import { api } from "../api.js";
import { icon } from "../icons.js";
import { esc, pct, avatar, navigate } from "../utils.js";
import { trendChart, setView, loadingView, errorView } from "../components.js";

export async function renderAnalytics(view, route) {
  const days = Math.max(7, Math.min(28, parseInt(route.query.get("days") || "14", 10) || 14));
  view.innerHTML = loadingView("Analytics");
  let data;
  try {
    data = await api.analytics(days);
  } catch (e) {
    view.innerHTML = errorView(e);
    return;
  }
  const { trend, by_type, by_language, by_quality, confidence_bands, error_fields, reviewers, totals } = data;
  const maxBand = Math.max(1, ...confidence_bands.map((b) => b.fields));
  const maxErr = Math.max(1, ...error_fields.map((e) => e.count));
  const qualityOrder = ["good", "fair", "poor", "unknown"];
  const qualityLabels = { good: "Clear", fair: "Fair", poor: "Poor", unknown: "Unknown" };
  const qualityColors = { good: "#2d7255", fair: "#c6a04a", poor: "#b4463f", unknown: "#9aa096" };

  setView(`
    <div class="page-head">
      <div>
        <div class="eyebrow">Measurement</div>
        <h1>Analytics</h1>
        <p class="lede">Where the model is confident, where reviewers intervene, and where the process is losing time.</p>
      </div>
      <div class="page-head-actions">
        <div class="analytics-controls">
          ${[7, 14, 28].map((d) => `<button class="${d === days ? "active" : ""}" data-days="${d}">${d} days</button>`).join("")}
        </div>
        <button class="btn" data-export>${icon("download", "icon-sm")} Export report</button>
      </div>
    </div>

    <div class="analytics-kpis">
      <div class="mini-kpi"><div class="label">Documents</div><div class="value">${totals.documents}</div><div class="foot">${totals.fields} extracted fields</div></div>
      <div class="mini-kpi"><div class="label">Human corrections</div><div class="value">${totals.corrections}</div><div class="foot">${totals.documents ? (totals.corrections / totals.documents).toFixed(2) : "0"} per document</div></div>
      <div class="mini-kpi"><div class="label">Validation failures</div><div class="value" style="color:var(--red)">${totals.invalid}</div><div class="foot">Across all fields</div></div>
      <div class="mini-kpi"><div class="label">SLA compliance</div><div class="value" style="color:${totals.sla_compliance >= 90 ? "var(--green)" : "var(--amber)"}">${totals.sla_compliance}%</div><div class="foot">${totals.overdue} open documents overdue</div></div>
    </div>

    <section class="card">
      <div class="card-head">
        <div><h2 class="card-title">Volume & straight-through</h2><p class="card-sub">The last ${days} days of intake and automated decisions</p></div>
        <div class="legend"><span><i style="background:#c3d6d0"></i>Volume</span><span><i style="background:#23675a"></i>Auto-approved</span><span><i style="background:#c6a04a"></i>STP line</span></div>
      </div>
      <div class="chart-wrap">${trendChart(trend, { height: 270 })}</div>
    </section>

    <div class="analytics-grid">
      <section class="card">
        <div class="card-head"><div><h2 class="card-title">Performance by document type</h2><p class="card-sub">Automation, confidence and correction volume</p></div></div>
        <div class="bar-list">
          ${by_type.map((t) => `<div class="bar-row">
            <span class="name">${esc(t.name)}</span>
            <span class="track"><span class="fill" style="width:${t.auto_rate}%"></span></span>
            <span class="value">${t.count}</span>
            <span class="sub">${t.auto_rate}% STP</span>
          </div>`).join("") || `<p class="muted small">No data.</p>`}
        </div>
        <div style="border-top:1px solid var(--line);padding:12px 24px;display:flex;gap:16px;flex-wrap:wrap">
          ${by_type.slice(0, 3).map((t) => `<span class="tiny muted">${esc(t.name)} · ${t.avg_confidence}% mean confidence · ${t.corrections} corrections</span>`).join("")}
        </div>
      </section>

      <section class="card">
        <div class="card-head"><div><h2 class="card-title">Confidence calibration</h2><p class="card-sub">Corrected fields as a share of each band</p></div></div>
        <div class="calib">
          ${confidence_bands.map((b) => `<div class="calib-row">
            <span class="calib-label">${esc(b.label)}</span>
            <span class="calib-track" title="${b.fields} fields · ${b.corrected} corrected">
              <span class="calib-bar" style="width:${Math.round(100 * (b.fields - b.corrected) / maxBand)}%"></span>
              <span class="calib-bar bad" style="width:${Math.round(100 * b.corrected / maxBand)}%"></span>
            </span>
            <span class="calib-rate">${b.correction_rate}%</span>
          </div>`).join("")}
        </div>
        <div style="padding:0 24px 18px"><p class="tiny muted" style="line-height:1.5">A calibrated model should show correction rates falling as confidence rises. The 90–100% band is the straight-through target.</p></div>
      </section>
    </div>

    <div class="analytics-grid-2">
      <section class="card">
        <div class="card-head"><div><h2 class="card-title">Where reviewers spend time</h2><p class="card-sub">Fields with low confidence or a validation failure</p></div></div>
        <div class="error-list">
          ${error_fields.map((e) => `<div class="error-row">
            <span class="name">${esc(e.label)}</span>
            <span class="track"><span class="fill" style="width:${Math.round(100 * e.count / maxErr)}%"></span></span>
            <span class="count">${e.count}</span>
          </div>`).join("") || `<p class="muted small">No error hotspots yet.</p>`}
        </div>
      </section>
      <section class="card">
        <div class="card-head"><div><h2 class="card-title">Language performance</h2><p class="card-sub">Volume and automation by language</p></div></div>
        <div class="bar-list">
          ${by_language.map((l) => `<div class="bar-row">
            <span class="name">${esc(l.name)}</span>
            <span class="track"><span class="fill" style="width:${l.auto_rate}%"></span></span>
            <span class="value">${l.count}</span>
            <span class="sub">${l.avg_confidence}%</span>
          </div>`).join("")}
        </div>
        <div style="border-top:1px solid var(--line);padding:12px 24px;display:flex;gap:8px;flex-wrap:wrap">
          ${qualityOrder.filter((q) => by_quality.some((x) => x.name === q)).map((q) => {
            const item = by_quality.find((x) => x.name === q);
            return `<span class="pill" style="background:#fff;border-color:var(--line)"><i class="legend-dot" style="background:${qualityColors[q]}"></i>${qualityLabels[q]} · ${item.count}</span>`;
          }).join("")}
        </div>
      </section>
    </div>

    <div class="analytics-grid-2">
      <section class="card">
        <div class="card-head"><div><h2 class="card-title">Reviewer throughput</h2><p class="card-sub">This snapshot · attributed decisions</p></div></div>
        <table class="reviewer-table">
          <thead><tr><th>Reviewer</th><th>Reviewed</th><th>Corrections</th><th>Avg. time</th><th></th></tr></thead>
          <tbody>
            ${reviewers.map((r) => `<tr>
              <td><div class="reviewer-cell">${avatar({ name: r.name, initials: r.initials, color: r.color }, "avatar-sm")}<strong>${esc(r.name)}</strong></div></td>
              <td>${r.reviewed}</td>
              <td>${r.corrections}</td>
              <td>${r.avg_tat ? r.avg_tat + "m" : "—"}</td>
              <td style="text-align:right"><span class="pill pill-green">${r.correction_rate}% corr.</span></td>
            </tr>`).join("") || `<tr><td colspan="5" class="muted small" style="padding:18px 14px">No reviewer activity yet.</td></tr>`}
          </tbody>
        </table>
      </section>
      <section class="card" style="background:linear-gradient(155deg,#f7f2e4,#fffdf8)">
        <div class="card-head"><div><h2 class="card-title">A note on calibration</h2><p class="card-sub">Why confidence is shown per field, not just per page</p></div></div>
        <div style="padding:10px 24px 24px">
          <p class="muted" style="font-size:12px;line-height:1.7">Page-level confidence hides the one field that matters. Akshara aggregates token confidence into field-level scores, then combines them with deterministic validation. Reviewers see exactly where the model is uncertain, and supervisors can audit the original model output after a correction.</p>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:16px">
            <div style="padding:10px;border:1px solid var(--line);border-radius:8px;background:#fff"><div class="eyebrow">Polyglot</div><div style="font-family:var(--font-display);font-size:22px;margin-top:4px">6 scripts</div></div>
            <div style="padding:10px;border:1px solid var(--line);border-radius:8px;background:#fff"><div class="eyebrow">Audited</div><div style="font-family:var(--font-display);font-size:22px;margin-top:4px">${totals.fields} fields</div></div>
          </div>
        </div>
      </section>
    </div>
  `, (root) => {
    root.querySelectorAll("[data-days]").forEach((b) => b.addEventListener("click", () => {
      const d = b.dataset.days;
      navigate(`/analytics?days=${d}`);
    }));
    root.querySelector("[data-export]")?.addEventListener("click", () => {
      const rows = [
        ["Metric", "Value"],
        ["Documents", totals.documents], ["Fields", totals.fields],
        ["Corrections", totals.corrections], ["Invalid fields", totals.invalid],
        ["Open", totals.open], ["Overdue", totals.overdue],
        ["SLA compliance", totals.sla_compliance + "%"],
        ...by_type.map((t) => [`Type: ${t.name}`, `${t.count} docs · ${t.auto_rate}% STP · ${t.avg_confidence}% conf`]),
        ...by_language.map((l) => [`Language: ${l.name}`, `${l.count} docs · ${l.auto_rate}% STP · ${l.avg_confidence}% conf`]),
      ];
      const csv = rows.map((r) => r.map((v) => `"${String(v).replaceAll('"', '""')}"`).join(",")).join("\n");
      const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = `akshara-analytics-${days}d.csv`;
      a.click();
      URL.revokeObjectURL(a.href);
    });
  });
}
