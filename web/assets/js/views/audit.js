import { api } from "../api.js";
import { icon } from "../icons.js";
import {
  esc, avatar, relative, fmtDateTime, debounce, ACTION_LABEL as FALLBACK_LABEL,
} from "../utils.js";
import { setView, loadingView, errorView, emptyState, toast } from "../components.js";
import { ACTION_LABEL, ACTION_TONE } from "../utils.js";

const ACTION_ICON = {
  "document.received": "inbox",
  "document.extracted": "scan",
  "document.routed": "inbox",
  "document.auto_approved": "sparkles",
  "document.claimed": "user",
  "document.released": "arrowLeft",
  "document.approved": "checkCircle",
  "document.rejected": "x",
  "document.rescan": "refresh",
  "document.escalated": "flag",
  "document.reopened": "refresh",
  "document.override": "shield",
  "field.corrected": "edit",
  "field.bulk_verified": "check",
  "comment.added": "message",
  "settings.updated": "sliders",
};

export async function renderAudit(view, route) {
  view.innerHTML = loadingView("Audit log");
  let users = [];
  try {
    const u = await api.session();
    const all = await api.audit({ limit: 1 });
    // Users endpoint is small; fetch once for the filter.
    const ures = await fetch("/api/users", { credentials: "same-origin" });
    users = (await ures.json()).items || [];
  } catch (e) {
    // Authentication is managed by the app; render the error if the read failed.
    view.innerHTML = errorView(e);
    return;
  }

  const filters = {
    q: route.query.get("q") || "",
    action: "",
    user: "",
    limit: 80,
    offset: 0,
  };
  let items = [];
  let total = 0;

  const fetchData = async (append = false) => {
    const data = await api.audit({ ...filters, limit: filters.limit, offset: append ? items.length : 0 });
    if (append) items = [...items, ...data.items];
    else items = data.items;
    total = data.total;
    return data;
  };

  const paintRows = () => {
    const list = view.querySelector("#audit-list");
    if (!list) return;
    list.innerHTML = items.map((e) => `<div class="audit-row">
      <span class="audit-icon ${ACTION_TONE[e.action] || ""}">${icon(ACTION_ICON[e.action] || "scan")}</span>
      <div class="audit-main">
        <p><strong>${esc(ACTION_LABEL[e.action] || e.action)}</strong>${e.detail ? ` — ${esc(e.detail)}` : ""}</p>
        <div class="t-sub">
          ${e.user ? `${avatar({ name: e.user.name, initials: e.user.initials, color: e.user.color }, "avatar-sm")}<span>${esc(e.user.name)}</span><span>·</span>` : `<span>Akshara</span><span>·</span>`}
          ${e.doc_id ? `<a href="#/review/${esc(e.doc_id)}">${esc(e.doc_ref)}</a><span>·</span>` : ""}
          <span>${relative(e.created_at)}</span>
        </div>
      </div>
      <span class="audit-time">${fmtDateTime(e.created_at)}</span>
    </div>`).join("");
    view.querySelector("#audit-empty").hidden = items.length > 0;
    const more = view.querySelector("#audit-more");
    if (more) more.hidden = items.length >= total;
    const count = view.querySelector("#audit-count");
    if (count) count.textContent = `${total} event${total === 1 ? "" : "s"}`;
  };

  const load = async (append = false) => {
    try {
      await fetchData(append);
      paintRows();
    } catch (e) {
      toast(e.message, "error");
    }
  };

  const actionOptions = Object.entries(ACTION_LABEL)
    .map(([v, l]) => `<option value="${esc(v)}">${esc(l)}</option>`).join("");

  setView(`
    <div class="page-head">
      <div>
        <div class="eyebrow">Attribution</div>
        <h1>Audit log</h1>
        <p class="lede">Every extraction, correction, override and settings change. This is the record a regulator asks for.</p>
      </div>
      <div class="page-head-actions">
        <span class="pill pill-outline" id="audit-count">—</span>
        <button class="btn" data-refresh>${icon("refresh", "icon-sm")} Refresh</button>
      </div>
    </div>

    <div class="audit-tools">
      <div class="search-input">${icon("search")}<input id="audit-search" value="${esc(filters.q)}" placeholder="Search event, reference or customer" aria-label="Search audit log"></div>
      <select class="mini-select" id="audit-action">
        <option value="">All event types</option>
        ${actionOptions}
      </select>
      <select class="mini-select" id="audit-user">
        <option value="">All people</option>
        ${users.map((u) => `<option value="${esc(u.id)}">${esc(u.name)}</option>`).join("")}
      </select>
      <span style="margin-left:auto" class="tiny faint">Immutable · append-only</span>
    </div>

    <section class="card audit-card">
      <div class="audit-list" id="audit-list"></div>
      <div id="audit-empty" hidden>${emptyState("No events match", "Try a broader filter or clear the search.", "history")}</div>
      <div class="load-more"><button class="btn" id="audit-more" data-more>${icon("chevronDown", "icon-sm")} Load older events</button></div>
    </section>
  `, (root) => {
    paintRows();
    const search = root.querySelector("#audit-search");
    search.addEventListener("input", debounce(() => { filters.q = search.value.trim(); filters.offset = 0; load(false); }, 180));
    root.querySelector("#audit-action").addEventListener("change", (e) => { filters.action = e.target.value; load(false); });
    root.querySelector("#audit-user").addEventListener("change", (e) => { filters.user = e.target.value; load(false); });
    root.querySelector("[data-refresh]").addEventListener("click", () => load(false));
    root.querySelector("[data-more]").addEventListener("click", () => load(true));
  });

  await load(false);
}
