import { icon } from "./icons.js";
import { esc, avatar, statusPill, qs, qsa, navigate, initials } from "./utils.js";
import { state, roleLabel } from "./store.js";

/* -------------------------------------------------------------------------- toast */
export function toast(message, type = "success", timeout = 4200) {
  const root = qs("#toast-root");
  if (!root) return;
  const el = document.createElement("div");
  el.className = `toast ${type}`;
  const ic = type === "error" ? "alertCircle" : type === "info" ? "info" : "checkCircle";
  el.innerHTML = `${icon(ic)}<div>${esc(message)}</div>`;
  root.appendChild(el);
  setTimeout(() => {
    el.classList.add("out");
    setTimeout(() => el.remove(), 220);
  }, timeout);
}

/* -------------------------------------------------------------------------- modal */
let openOverlay = null;

export function closeModal() {
  if (openOverlay) {
    openOverlay.remove();
    openOverlay = null;
    document.body.style.overflow = "";
  }
}

export function modal({ title, subtitle = "", iconName = "info", body = "", footer = "", size = "", onMount = null, closeOnBackdrop = true }) {
  closeModal();
  const overlay = document.createElement("div");
  overlay.className = "modal-backdrop";
  overlay.innerHTML = `
    <div class="modal ${size}" role="dialog" aria-modal="true" aria-label="${esc(title)}">
      <div class="modal-head">
        <div class="m-icon">${icon(iconName)}</div>
        <div><h3>${esc(title)}</h3>${subtitle ? `<p>${esc(subtitle)}</p>` : ""}</div>
        <button class="icon-btn modal-close" data-close aria-label="Close">${icon("x")}</button>
      </div>
      <div class="modal-body">${body}</div>
      ${footer ? `<div class="modal-foot">${footer}</div>` : ""}
    </div>`;
  document.body.appendChild(overlay);
  document.body.style.overflow = "hidden";
  openOverlay = overlay;
  overlay.addEventListener("click", (e) => {
    if (e.target === overlay && closeOnBackdrop) closeModal();
    if (e.target.closest("[data-close]")) closeModal();
  });
  const onKey = (e) => {
    if (e.key === "Escape") { closeModal(); document.removeEventListener("keydown", onKey); }
  };
  document.addEventListener("keydown", onKey);
  if (onMount) onMount(overlay);
  setTimeout(() => {
    const focus = overlay.querySelector("[autofocus], input, textarea, select, button");
    if (focus) focus.focus();
  }, 50);
  return overlay;
}

export function confirmModal({ title, message, confirmLabel = "Confirm", tone = "primary", iconName = "alert", onConfirm }) {
  const footer = `
    <button class="btn" data-close>Cancel</button>
    <button class="btn ${tone === "danger" ? "btn-danger" : "btn-primary"}" data-confirm>${esc(confirmLabel)}</button>`;
  const overlay = modal({ title, body: `<p class="muted" style="font-size:12.5px;line-height:1.6">${esc(message)}</p>`, footer, iconName });
  overlay.querySelector("[data-confirm]").addEventListener("click", async () => {
    const btn = overlay.querySelector("[data-confirm]");
    btn.disabled = true;
    try { await onConfirm(); closeModal(); } catch (e) { btn.disabled = false; toast(e.message, "error"); }
  });
}

/* -------------------------------------------------------------------------- shell */
const NAV = [
  { id: "overview", label: "Overview", icon: "grid", href: "#/overview" },
  { id: "queue", label: "Review queue", icon: "inbox", href: "#/queue", badge: "queue" },
  { id: "documents", label: "Documents", icon: "files", href: "#/documents" },
  { id: "analytics", label: "Analytics", icon: "chart", href: "#/analytics" },
  { id: "audit", label: "Audit log", icon: "history", href: "#/audit" },
  { id: "settings", label: "Settings", icon: "sliders", href: "#/settings" },
];

export function shellMarkup(active) {
  const counts = state.counts || {};
  const user = state.user;
  const queueCount = counts.queue ?? 0;
  const nav = NAV.map((item) => {
    const badge = item.badge === "queue" && queueCount ? `<span class="nav-badge">${queueCount}</span>` : "";
    return `<a class="nav-item ${active === item.id ? "active" : ""}" href="${item.href}">${icon(item.icon)}<span>${item.label}</span>${badge}</a>`;
  }).join("");

  return `
  <div class="shell">
    <aside class="sidebar" id="sidebar">
      <button class="icon-btn sidebar-close" data-sidebar-close aria-label="Close menu">${icon("x")}</button>
      <a class="sidebar-brand" href="#/overview">
        <span class="brand-mark sm">अ</span>
        <span><span class="brand-word">Akshara</span><span class="brand-tag">document intelligence</span></span>
      </a>
      <div class="workspace">
        <span class="ws-icon">M</span>
        <span class="ws-meta"><strong>Meridian Bank</strong><span>Operations · Mumbai</span></span>
        ${icon("chevronDown")}
      </div>
      <div class="nav-label">Workspace</div>
      <nav class="nav">${nav}</nav>
      <div class="sidebar-spacer"></div>
      <div class="sidebar-card">
        <div class="eyebrow">Human in the loop</div>
        <strong>${queueCount} documents waiting</strong>
        <p>Calibrated confidence, field-level review, and a complete audit trail.</p>
        <a class="mini-link" href="#/queue">Open the queue ${icon("arrowRight", "icon-sm")}</a>
      </div>
      <div class="sidebar-user">
        ${avatar(user)}
        <div class="who"><strong>${esc(user.name)}</strong><span>${esc(roleLabel())} · ${esc(user.email)}</span></div>
        <button class="icon-btn" data-logout aria-label="Sign out" title="Sign out">${icon("logout")}</button>
      </div>
    </aside>
    <div class="main">
      <header class="topbar">
        <button class="icon-btn menu-toggle" data-sidebar-open aria-label="Open menu">${icon("menu")}</button>
        <div class="topbar-context">
          <div class="crumbs" id="crumbs"><span>Operations</span><span class="sep">/</span><strong>Overview</strong></div>
          <div class="topbar-title" id="topbar-title">Command centre</div>
        </div>
        <form class="topbar-search" id="global-search" role="search">
          ${icon("search")}
          <input type="search" name="q" placeholder="Search reference, customer or language" aria-label="Search documents">
        </form>
        <div class="topbar-actions">
          <div class="notif-wrap">
            <button class="icon-btn bordered" data-notifications aria-label="Attention needed">
              ${icon("bell")}
              ${(counts.overdue || 0) + (counts.low_confidence || 0) > 0 ? '<span class="notif-dot"></span>' : ""}
            </button>
          </div>
          <button class="btn btn-gold" data-intake>${icon("plus", "icon-sm")}<span>New intake</span></button>
        </div>
      </header>
      <main class="view" id="view"></main>
    </div>
  </div>
  <div class="sidebar-scrim" id="sidebar-scrim" hidden></div>`;
}

export function mountShell(active) {
  const app = qs("#app");
  app.innerHTML = shellMarkup(active);
  const sidebar = qs("#sidebar");
  const scrim = qs("#sidebar-scrim");
  const close = () => {
    sidebar.classList.remove("open");
    scrim.hidden = true;
  };
  qs("[data-sidebar-open]")?.addEventListener("click", () => {
    sidebar.classList.add("open");
    scrim.hidden = false;
  });
  qs("[data-sidebar-close]")?.addEventListener("click", close);
  scrim.addEventListener("click", close);
  qs("[data-logout]")?.addEventListener("click", async () => {
    const { api } = await import("./api.js");
    try { await api.logout(); } catch {}
    location.hash = "/overview";
    window.dispatchEvent(new CustomEvent("akshara:logout"));
  });
  qs("[data-notifications]")?.addEventListener("click", showNotifications);
  qs("#global-search")?.addEventListener("submit", (e) => {
    e.preventDefault();
    const q = new FormData(e.currentTarget).get("q")?.toString().trim();
    navigate(`/queue${q ? `?q=${encodeURIComponent(q)}` : ""}`);
  });
  qs("[data-intake]")?.addEventListener("click", async () => {
    const mod = await import("./intake.js");
    mod.openIntake();
  });
  return { sidebar, close };
}

export function setTopbar(crumbs, title) {
  const c = qs("#crumbs");
  const t = qs("#topbar-title");
  if (c) c.innerHTML = crumbs;
  if (t) t.textContent = title;
}

export function refreshSidebarCounts() {
  const badge = qs(".nav-item[href='#/queue'] .nav-badge");
  const count = state.counts?.queue ?? 0;
  if (badge) {
    badge.textContent = count;
    badge.style.display = count ? "" : "none";
  }
}

export function setView(html, bind) {
  const view = qs("#view");
  if (!view) return;
  view.className = "view";
  view.innerHTML = html;
  view.scrollTop = 0;
  if (bind) bind(view);
}

export function loadingView(title = "Loading") {
  return `<div class="page-head"><div><div class="eyebrow">Akshara</div><h1>${esc(title)}</h1></div></div>
    <div class="card card-pad"><div class="skeleton" style="height:20px;width:40%"></div>
    <div class="skeleton" style="height:12px;width:70%;margin-top:14px"></div>
    <div class="skeleton" style="height:12px;width:55%;margin-top:9px"></div></div>`;
}

export function emptyState(title, text, iconName = "inbox", action = "") {
  return `<div class="table-empty">
    <div class="empty-mark">${icon(iconName, "icon-lg")}</div>
    <h3>${esc(title)}</h3>
    <p>${esc(text)}</p>
    ${action ? `<div style="margin-top:14px">${action}</div>` : ""}
  </div>`;
}

export function errorView(err) {
  return `<div class="card card-pad" style="max-width:640px;margin:40px auto;text-align:center">
    <div class="empty-mark" style="margin:0 auto 12px">${icon("alertCircle", "icon-lg")}</div>
    <h2 style="font-family:var(--font-display);font-size:24px">Could not load this view</h2>
    <p class="muted" style="margin-top:6px">${esc(err?.message || "Unexpected error")}</p>
    <button class="btn btn-primary" style="margin-top:16px" onclick="location.reload()">Reload</button>
  </div>`;
}

/* -------------------------------------------------------------------------- notifications */
export async function showNotifications() {
  const counts = state.counts || {};
  const footer = `<button class="btn" data-close>Close</button><a class="btn btn-primary" href="#/queue?view=attention" data-close>Open attention queue ${icon("arrowRight", "icon-sm")}</a>`;
  const body = `
    <p class="muted" style="font-size:12px;line-height:1.6">Items that need a human decision now.</p>
    <div class="issue-list" style="margin-top:12px">
      <div class="issue" style="border-color:#ecdcb9;background:var(--amber-soft);color:var(--amber)">${icon("clock")}<div><strong>${counts.overdue || 0}</strong> open documents have breached their SLA.</div></div>
      <div class="issue" style="border-color:#e6dcc1;background:#fbf6e8;color:var(--gold-ink)">${icon("scan")}<div><strong>${counts.low_confidence || 0}</strong> documents contain fields below 80% confidence.</div></div>
      <div class="issue" style="border-color:#d7e2ea;background:var(--blue-soft);color:var(--blue)">${icon("inbox")}<div><strong>${counts.unassigned || 0}</strong> documents are waiting to be claimed.</div></div>
    </div>`;
  modal({ title: "Attention needed", subtitle: "The queue, ranked by risk", iconName: "bell", body, footer });
}

/* -------------------------------------------------------------------------- charts */
export function sparkline(values, color = "#1f6a5b", width = 72, height = 22) {
  if (!values || values.length < 2) return "";
  const min = Math.min(...values), max = Math.max(...values);
  const span = max - min || 1;
  const pts = values.map((v, i) => {
    const x = (i / (values.length - 1)) * (width - 2) + 1;
    const y = height - 2 - ((v - min) / span) * (height - 5);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(" ");
  return `<svg class="spark" viewBox="0 0 ${width} ${height}" aria-hidden="true"><polyline points="${pts}" fill="none" stroke="${color}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
}

export function trendChart(data, opts = {}) {
  const W = 760, H = opts.height || 246;
  const pad = { l: 34, r: 14, t: 16, b: 26 };
  const pw = W - pad.l - pad.r, ph = H - pad.t - pad.b;
  const rows = data || [];
  const max = Math.max(8, ...rows.map((d) => d.volume || 0));
  const step = pw / Math.max(1, rows.length);
  const bw = Math.min(24, step * 0.48);
  const y = (v) => pad.t + ph - (v / max) * ph;
  const grid = [0, 0.25, 0.5, 0.75, 1].map((f) => {
    const gy = pad.t + ph - f * ph;
    return `<line class="chart-grid" x1="${pad.l}" y1="${gy}" x2="${W - pad.r}" y2="${gy}"/>
      <text class="chart-axis" x="${pad.l - 6}" y="${gy + 3}" text-anchor="end">${Math.round(max * f)}</text>`;
  }).join("");
  const bars = rows.map((d, i) => {
    const x = pad.l + i * step + (step - bw) / 2;
    const bh = Math.max(1, (d.volume / max) * ph);
    const autoH = Math.max(1, (d.auto_approved / max) * ph);
    return `<g><title>${d.day} · ${d.volume} documents · ${d.auto_approved} straight-through</title>
      <rect class="bar-rect" x="${x}" y="${pad.t + ph - bh}" width="${bw}" height="${bh}" rx="2" fill="#23675a" opacity=".16"/>
      <rect class="bar-rect" x="${x}" y="${pad.t + ph - autoH}" width="${bw}" height="${autoH}" rx="2" fill="#23675a" opacity=".7"/>
    </g>`;
  }).join("");
  const pts = rows.map((d, i) => {
    const x = pad.l + i * step + step / 2;
    const yy = y(d.auto_approved);
    return `${x.toFixed(1)},${yy.toFixed(1)}`;
  }).join(" ");
  const labels = rows.map((d, i) => {
    if (i % Math.max(1, Math.ceil(rows.length / 7)) !== 0 && i !== rows.length - 1) return "";
    const x = pad.l + i * step + step / 2;
    const dt = new Date(d.day + "T00:00:00");
    const label = new Intl.DateTimeFormat("en-IN", { day: "2-digit", month: "short" }).format(dt);
    return `<text class="chart-axis" x="${x}" y="${H - 8}" text-anchor="middle">${label}</text>`;
  }).join("");
  const gid = "g" + Math.random().toString(36).slice(2, 7);
  return `<svg class="chart-svg" viewBox="0 0 ${W} ${H}" role="img" aria-label="Document volume and straight-through trend">
    <defs><linearGradient id="${gid}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#c6a04a" stop-opacity=".22"/><stop offset="1" stop-color="#c6a04a" stop-opacity="0"/></linearGradient></defs>
    ${grid}
    <path d="M${pts.replaceAll(" ", " L")} L${pad.l + (rows.length - 0.5) * step},${pad.t + ph} L${pad.l + step / 2},${pad.t + ph} Z" fill="url(#${gid})" opacity=".9"/>
    ${bars}
    <polyline points="${pts}" class="line-path"/>
    ${rows.map((d, i) => {
      const x = pad.l + i * step + step / 2;
      return `<circle cx="${x}" cy="${y(d.auto_approved)}" r="2.4" fill="#fffdf8" stroke="#c6a04a" stroke-width="1.6"><title>${d.auto_approved} straight-through on ${d.day}</title></circle>`;
    }).join("")}
    ${labels}
  </svg>`;
}

export function donut(segments, total, centerLabel = "") {
  const size = 160, r = 58, c = 2 * Math.PI * r;
  let offset = 0;
  const rings = segments.map((s) => {
    const frac = total ? s.value / total : 0;
    const len = frac * c;
    const el = `<circle cx="80" cy="80" r="${r}" fill="none" stroke="${s.color}" stroke-width="18"
      stroke-dasharray="${len} ${c - len}" stroke-dashoffset="${-offset}" transform="rotate(-90 80 80)" stroke-linecap="butt"><title>${s.label}: ${s.value}</title></circle>`;
    offset += len;
    return el;
  }).join("");
  return `<svg class="donut" viewBox="0 0 160 160" role="img" aria-label="Queue health">
    <circle cx="80" cy="80" r="${r}" fill="none" stroke="#f0ebe0" stroke-width="18"/>
    ${rings}
    <text x="80" y="78" text-anchor="middle" class="donut-center">${esc(centerLabel || total)}</text>
    <text x="80" y="95" text-anchor="middle" class="donut-sub">open items</text>
  </svg>`;
}
