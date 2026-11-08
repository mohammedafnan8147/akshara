import { icon, docIcon } from "./icons.js";

export const STATUS_LABEL = {
  queued: "Needs review",
  in_review: "In review",
  escalated: "Escalated",
  needs_rescan: "Rescan requested",
  auto_approved: "Auto-approved",
  approved: "Approved",
  rejected: "Rejected",
};

export const STATUS_TONE = {
  queued: "amber",
  in_review: "blue",
  escalated: "red",
  needs_rescan: "slate",
  auto_approved: "green",
  approved: "green",
  rejected: "red",
};

export const ACTION_LABEL = {
  "document.received": "Document received",
  "document.extracted": "Extraction complete",
  "document.routed": "Routed to review",
  "document.auto_approved": "Auto-approved",
  "document.claimed": "Claimed for review",
  "document.released": "Returned to queue",
  "document.approved": "Approved",
  "document.rejected": "Rejected",
  "document.rescan": "Rescan requested",
  "document.escalated": "Escalated",
  "document.reopened": "Reopened",
  "document.override": "Supervisor override",
  "field.corrected": "Field corrected",
  "field.bulk_verified": "High-confidence fields accepted",
  "comment.added": "Comment added",
  "settings.updated": "Settings updated",
};

export const ACTION_TONE = {
  "document.approved": "green",
  "document.auto_approved": "green",
  "document.rejected": "red",
  "document.escalated": "red",
  "document.rescan": "amber",
  "document.routed": "amber",
  "document.reopened": "blue",
  "field.corrected": "blue",
  "settings.updated": "blue",
};

export function esc(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

export function initials(name) {
  if (!name) return "—";
  return name.trim().split(/\s+/).slice(0, 2).map((p) => p[0]?.toUpperCase() || "").join("") || "—";
}

export function avatar(user, cls = "") {
  if (!user) {
    return `<span class="avatar ${cls}" style="background:#c8c2b3">—</span>`;
  }
  return `<span class="avatar ${cls}" title="${esc(user.name)}" style="background:${esc(user.color || "#2d7255")}">${esc(user.initials || initials(user.name))}</span>`;
}

export function statusPill(status, label = null) {
  const tone = STATUS_TONE[status] || "slate";
  return `<span class="pill pill-${tone}"><span class="dot"></span>${esc(label || STATUS_LABEL[status] || status)}</span>`;
}

export function priorityPill(priority) {
  if (priority === "urgent") return `<span class="pill pill-red">Urgent</span>`;
  if (priority === "high") return `<span class="pill pill-amber">High</span>`;
  return `<span class="pill pill-slate">Normal</span>`;
}

export function confTone(value) {
  if (value >= 0.9) return "green";
  if (value >= 0.75) return "amber";
  return "red";
}

export function confBar(value, opts = {}) {
  const pct = Math.round((value || 0) * 100);
  const tone = confTone(value);
  const showNum = opts.number !== false;
  return `<span class="conf"><span class="conf-track"><span class="conf-fill ${tone === "green" ? "" : tone}" style="width:${pct}%"></span></span>${showNum ? `<span class="conf-num">${pct}%</span>` : ""}</span>`;
}

export function docTile(doc) {
  const name = docIcon[doc.doc_type] || "fileText";
  return `<span class="doc-tile">${icon(name)}</span>`;
}

export function typeLabel(doc) {
  return doc.doc_type_label || doc.title || "Document";
}

export function qualityLabel(q) {
  return { good: "Clear scan", fair: "Fair scan", poor: "Poor scan", unknown: "Unreadable" }[q] || "Scan";
}

export function languageChips(doc) {
  const lang = doc.language_name || "Unknown";
  const script = doc.script || "";
  return `<span class="chip chip-script">${esc(lang)}${script && script !== lang ? ` · ${esc(script)}` : ""}</span>`;
}

export function fmtDate(iso) {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  return new Intl.DateTimeFormat("en-IN", { day: "2-digit", month: "short", year: "numeric" }).format(d);
}

export function fmtDateTime(iso) {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  return new Intl.DateTimeFormat("en-IN", {
    day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit", hour12: false,
  }).format(d);
}

export function fmtTime(iso) {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  return new Intl.DateTimeFormat("en-IN", { hour: "2-digit", minute: "2-digit", hour12: false }).format(d);
}

export function relative(iso) {
  if (!iso) return "—";
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return "—";
  const diff = Math.max(0, Date.now() - then) / 1000;
  if (diff < 45) return "just now";
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  if (diff < 604800) return `${Math.floor(diff / 86400)}d ago`;
  return fmtDate(iso);
}

export function duration(minutes) {
  const m = Math.max(0, Math.round(Math.abs(minutes)));
  if (m >= 1440) {
    const d = Math.floor(m / 1440);
    const h = Math.floor((m % 1440) / 60);
    return `${d}d${h ? ` ${h}h` : ""}`;
  }
  if (m >= 60) {
    const h = Math.floor(m / 60);
    const mm = m % 60;
    return `${h}h${mm ? ` ${mm}m` : ""}`;
  }
  return `${m}m`;
}

export function dueLabel(doc) {
  if (["approved", "rejected", "auto_approved"].includes(doc.status)) return { main: "Closed", sub: "—", tone: "" };
  const mins = doc.due_in_minutes ?? 0;
  if (mins < 0) return { main: duration(mins) + " overdue", sub: "SLA breached", tone: "overdue" };
  if (mins < 120) return { main: "Due in " + duration(mins), sub: "Approaching SLA", tone: "soon" };
  return { main: "Due in " + duration(mins), sub: fmtDate(doc.due_at), tone: "" };
}

export function amountFmt(n) {
  if (n == null || Number.isNaN(Number(n))) return "—";
  return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(Number(n));
}

export function pct(n) {
  return `${Math.round(Number(n) || 0)}%`;
}

export function plural(n, one, many = null) {
  return `${n} ${n === 1 ? one : (many || one + "s")}`;
}

export function debounce(fn, ms = 180) {
  let t;
  return (...args) => {
    clearTimeout(t);
    t = setTimeout(() => fn(...args), ms);
  };
}

export function qs(sel, root = document) {
  return root.querySelector(sel);
}

export function qsa(sel, root = document) {
  return [...root.querySelectorAll(sel)];
}

export function navigate(path) {
  if (location.hash === "#" + path) {
    window.dispatchEvent(new HashChangeEvent("hashchange"));
  } else {
    location.hash = path;
  }
}

export function parseHash() {
  const raw = location.hash.replace(/^#/, "") || "/overview";
  const [path, queryString = ""] = raw.split("?");
  const parts = path.split("/").filter(Boolean);
  return { name: parts[0] || "overview", id: parts[1] || null, query: new URLSearchParams(queryString) };
}

export function greeting() {
  const h = new Date().getHours();
  if (h < 12) return "Good morning";
  if (h < 17) return "Good afternoon";
  return "Good evening";
}

export function todayLong() {
  return new Intl.DateTimeFormat("en-IN", {
    weekday: "long", day: "numeric", month: "long", year: "numeric",
  }).format(new Date());
}
