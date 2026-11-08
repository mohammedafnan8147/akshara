import { api } from "../api.js";
import { icon, docIcon } from "../icons.js";
import { state } from "../store.js";
import {
  esc, greeting, todayLong, avatar, statusPill, confBar, dueLabel,
  fmtDate, relative, duration, navigate, pct,
} from "../utils.js";
import {
  sparkline, trendChart, donut, setView, loadingView, errorView, toast,
} from "../components.js";

export async function renderDashboard(view) {
  view.innerHTML = loadingView("Command centre");
  let data;
  try {
    data = await api.dashboard();
  } catch (e) {
    view.innerHTML = errorView(e);
    return;
  }
  const { kpis, counts, trend, queue_health, attention, activity, by_script, workload } = data;
  state.counts = counts;
  const first = state.user.name.split(" ")[0];
  const sparkVol = trend.slice(-8).map((d) => d.volume);
  const sparkConf = trend.slice(-8).map((d) => Math.round((d.avg_confidence || 0) * 100));
  const medConf = kpis.avg_confidence;
  const autoSpark = trend.slice(-8).map((d) => d.auto_approved);
  const stp14 = trend.length
    ? Math.round(100 * trend.reduce((a, b) => a + (b.auto_approved || 0), 0) / Math.max(1, trend.reduce((a, b) => a + (b.volume || 0), 0)))
    : kpis.auto_rate;
  const openTotal = (queue_health.queued || 0) + (queue_health.in_review || 0) + (queue_health.escalated || 0) + (queue_health.needs_rescan || 0);
  const segments = [
    { label: "Needs review", value: queue_health.queued || 0, color: "#c99a42" },
    { label: "In review", value: queue_health.in_review || 0, color: "#4d7f90" },
    { label: "Escalated", value: queue_health.escalated || 0, color: "#b4463f" },
    { label: "Rescan", value: queue_health.needs_rescan || 0, color: "#9a9d94" },
  ];
  const queueTotal = segments.reduce((a, b) => a + b.value, 0);

  const kpi = (label, value, unit, foot, iconName, tone, spark) => `
    <article class="kpi">
      <div class="kpi-top"><span class="kpi-label">${label}</span><span class="kpi-icon ${tone}">${icon(iconName)}</span></div>
      <div class="kpi-value">${value}${unit ? `<span class="unit">${unit}</span>` : ""}</div>
      <div class="kpi-foot"><span>${foot}</span>${spark || ""}</div>
    </article>`;

  const attentionRows = attention.length ? attention.map((d) => {
    const due = dueLabel(d);
    return `<a class="attention-row" href="#/review/${esc(d.id)}">
      <span class="doc-tile">${icon(docIcon[d.doc_type] || "fileText")}</span>
      <div class="attention-main">
        <strong>${esc(d.customer_name || "Unknown customer")}</strong>
        <div class="attention-meta"><span class="mono">${esc(d.ref)}</span><span>·</span><span>${esc(d.doc_type_label)}</span><span>·</span><span>${esc(d.language_name)}</span></div>
        <div class="risk-reasons">${(d.reasons || []).slice(0, 2).map((r, i) => `<span class="risk-reason ${i ? "amber" : ""}">${esc(r)}</span>`).join("")}</div>
      </div>
      <div class="attention-side">
        ${confBar(d.confidence)}
        <span class="due-text ${due.tone}">${esc(due.main)}</span>
      </div>
    </a>`;
  }).join("") : `<div class="empty-state"><p>No documents need attention. The queue is clear.</p></div>`;

  const scriptMax = Math.max(1, ...by_script.map((x) => x.count));
  const scriptRows = by_script.map((s) => `
    <div class="script-row">
      <span class="script-name">${esc(s.script)}</span>
      <span class="script-track"><span class="script-fill" style="width:${Math.round(100 * s.count / scriptMax)}%; background:${s.script === "Arabic" ? "#8a6f3d" : s.script === "Tamil" ? "#4d7f70" : s.script === "Bengali" ? "#b07043" : s.script === "Devanagari" ? "#1f6a5b" : "#9b8a62"}"></span></span>
      <span class="script-count">${s.count}</span>
    </div>`).join("");

  const workloadRows = workload.length ? workload.map((w) => `
    <div class="workload-row">
      ${avatar({ name: w.name, initials: w.initials, color: w.color }, "avatar-sm")}
      <div class="who">${esc(w.name)}${w.overdue ? `<span>· ${w.overdue} overdue</span>` : ""}</div>
      <span class="workload-count">${w.count}</span>
    </div>`).join("") : `<p class="muted small" style="padding:10px 0">No open assignments.</p>`;

  const feedRows = activity.map((a) => `
    <div class="feed-row">
      <span class="feed-dot">${icon(a.action.includes("approved") ? "check" : a.action.includes("escalat") || a.action.includes("reject") ? "flag" : a.action.includes("correct") ? "edit" : a.action.includes("comment") ? "message" : "scan", "icon-sm")}</span>
      <div class="feed-body">
        <p>${esc(a.detail || a.action)} ${a.doc_id ? `· <a href="#/review/${esc(a.doc_id)}">${esc(a.doc_ref || "open")}</a>` : ""}</p>
        <div class="feed-time">${a.user ? esc(a.user.name) + " · " : ""}${relative(a.created_at)}</div>
      </div>
    </div>`).join("");

  setView(`
    <div class="greeting">
      <div>
        <div class="date">${esc(todayLong())}</div>
        <h1>${greeting()}, <em>${esc(first)}</em>.</h1>
        <p>${counts.queue || 0} documents in the human queue · ${counts.overdue || 0} past SLA · ${counts.unassigned || 0} unassigned.</p>
      </div>
      <div class="page-head-actions">
        <button class="btn" data-refresh>${icon("refresh", "icon-sm")} Refresh</button>
        <button class="btn btn-primary" data-intake>${icon("plus", "icon-sm")} Start intake</button>
      </div>
    </div>

    <div class="kpi-grid">
      ${kpi("Open review queue", kpis.open_queue, "", `<strong>${kpis.unassigned}</strong> unassigned · <span class="trend-up">${icon("arrowUpRight", "icon-sm")} live</span>`, "inbox", "", sparkline(sparkVol, "#1f6a5b"))}
      ${kpi("Past SLA", kpis.overdue, "", `<strong>${counts.overdue || 0}</strong> documents · <span class="trend-down">${icon("clock", "icon-sm")} act now</span>`, "clock", "red", sparkline([1, 2, 1, 3, 2, 3, 2, kpis.overdue || 0], "#b4463f"))}
      ${kpi("Straight-through", stp14, "%", `14-day average · <strong>${counts.auto_approved || 0}</strong> in this snapshot`, "sparkles", "gold", sparkline(autoSpark, "#c6a04a"))}
      ${kpi("Mean confidence", medConf, "%", `<strong>${counts.low_confidence || 0}</strong> docs with low-confidence fields`, "shield", "blue", sparkline(sparkConf, "#386a7e"))}
    </div>

    <div class="dash-split">
      <section class="card chart-card">
        <div class="card-head">
          <div><h2 class="card-title">Document flow</h2><p class="card-sub">Volume and straight-through processing, last 14 days</p></div>
          <div class="legend"><span><i style="background:#c3d6d0"></i>Volume</span><span><i style="background:#23675a"></i>Auto-approved</span><span><i style="background:#c6a04a"></i>STP line</span></div>
        </div>
        <div class="chart-wrap">${trendChart(trend)}</div>
      </section>
      <section class="card">
        <div class="card-head"><div><h2 class="card-title">Queue health</h2><p class="card-sub">Open work by state</p></div></div>
        <div class="donut-wrap">
          ${donut(segments, queueTotal, String(queueTotal))}
          <div class="donut-key">
            ${segments.map((s) => `<div class="donut-key-row"><i style="background:${s.color}"></i>${s.label}<strong>${s.value}</strong></div>`).join("")}
            <div class="donut-key-row" style="border-top:1px solid var(--line);padding-top:7px;margin-top:1px"><i style="background:#2d7255"></i>Auto-approved<strong>${queue_health.auto_approved || 0}</strong></div>
          </div>
        </div>
      </section>
    </div>

    <section class="card attention-card">
      <div class="card-head">
        <div><h2 class="card-title">Needs attention</h2><p class="card-sub">Ranked by SLA risk, validation issues and confidence</p></div>
        <a class="btn btn-sm" href="#/queue">Open queue ${icon("arrowRight", "icon-sm")}</a>
      </div>
      <div class="attention-list">${attentionRows}</div>
    </section>

    <div class="dash-split-2">
      <section class="card script-card">
        <div class="card-head"><div><h2 class="card-title">Script coverage</h2><p class="card-sub">Documents by writing system</p></div><span class="pill pill-gold">5 writing systems</span></div>
        <div class="script-bars">${scriptRows}</div>
      </section>
      <section class="card">
        <div class="card-head"><div><h2 class="card-title">Reviewer workload</h2><p class="card-sub">Open items by owner</p></div><a class="link" href="#/queue?view=unassigned" style="font-size:10.5px;color:var(--teal);font-weight:650">Unassigned ${icon("arrowRight", "icon-sm")}</a></div>
        <div class="workload-list">${workloadRows}</div>
      </section>
    </div>

    <div class="dash-split-2">
      <section class="card">
        <div class="card-head"><div><h2 class="card-title">Recent activity</h2><p class="card-sub">Every decision is attributable</p></div><a class="link" href="#/audit" style="font-size:10.5px;color:var(--teal);font-weight:650">Audit log ${icon("arrowRight", "icon-sm")}</a></div>
        <div class="feed">${feedRows || `<p class="muted small" style="padding:12px 0">No recent activity.</p>`}</div>
      </section>
      <section class="card" style="background:linear-gradient(155deg,#14342c,#0f2822);color:#f1eddf;border-color:#14342c">
        <div class="card-head"><div><div class="eyebrow" style="color:#b8a26c">Desk note</div><h2 class="card-title" style="color:#f4f0e4;margin-top:5px">A confidence score is a question, not a verdict.</h2></div></div>
        <div style="padding:10px 24px 22px">
          <p style="color:#b6c4ba;font-size:12px;line-height:1.65;max-width:480px">Every low-confidence field is grounded to its source box on the scan. Reviewers can correct, request a rescan, or escalate — and the model's original output stays in the audit trail.</p>
          <div style="display:flex;gap:16px;margin-top:18px">
            <div><div class="eyebrow" style="color:#8fa096">Fields checked</div><div style="font-family:var(--font-display);font-size:26px;color:#f4f0e4">${data.totals?.fields ?? "—"}</div></div>
            <div><div class="eyebrow" style="color:#8fa096">Corrections</div><div style="font-family:var(--font-display);font-size:26px;color:#f4f0e4">${data.totals?.corrections ?? "—"}</div></div>
          </div>
        </div>
      </section>
    </div>
  `, (root) => {
    root.querySelector("[data-refresh]")?.addEventListener("click", () => renderDashboard(root));
    root.querySelectorAll("[data-intake]").forEach((b) => b.addEventListener("click", async () => {
      const { openIntake } = await import("../intake.js");
      openIntake();
    }));
  });
}

