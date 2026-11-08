import { api } from "../api.js";
import { icon, docIcon } from "../icons.js";
import { state } from "../store.js";
import {
  esc, statusPill, priorityPill, confBar, languageChips, dueLabel,
  avatar, fmtDate, relative, qualityLabel, navigate, debounce, qs,
} from "../utils.js";
import { setView, loadingView, errorView, toast } from "../components.js";

const QUEUE_TABS = [
  { id: "all", label: "All open", count: (c) => c.queue || 0 },
  { id: "unassigned", label: "Unassigned", count: (c) => c.unassigned || 0 },
  { id: "low", label: "Low confidence", count: (c) => c.low_confidence || 0 },
  { id: "invalid", label: "Validation", count: (c, items) => items.filter((d) => d.invalid_count > 0).length },
  { id: "overdue", label: "Overdue", count: (c) => c.overdue || 0 },
  { id: "escalated", label: "Escalated", count: (c) => c.escalated || 0 },
];

const DOC_TABS = [
  { id: "all", label: "All", count: (c) => c.all || 0 },
  { id: "queued", label: "Needs review", count: (c) => c.queued || 0 },
  { id: "in_review", label: "In review", count: (c) => c.in_review || 0 },
  { id: "auto_approved", label: "Auto-approved", count: (c) => c.auto_approved || 0 },
  { id: "approved", label: "Approved", count: (c) => c.approved || 0 },
  { id: "rejected", label: "Rejected", count: (c) => c.rejected || 0 },
  { id: "needs_rescan", label: "Rescan", count: (c) => c.needs_rescan || 0 },
];

export async function renderQueue(view, route) {
  return renderDesk(view, route, "queue");
}

export async function renderDocuments(view, route) {
  return renderDesk(view, route, "documents");
}

async function renderDesk(view, route, mode) {
  const isQueue = mode === "queue";
  view.innerHTML = loadingView(isQueue ? "Review queue" : "Documents");
  let data;
  try {
    data = await api.documents({ view: isQueue ? "queue" : "all", limit: 500 });
  } catch (e) {
    view.innerHTML = errorView(e);
    return;
  }
  state.counts = data.counts;

  const filters = {
    tab: isQueue ? "all" : "all",
    q: route.query.get("q") || "",
    type: "",
    script: "",
    sort: route.query.get("view") === "attention" ? "risk" : "risk",
  };
  if (route.query.get("view") === "attention") filters.tab = "all";

  const queueTabs = QUEUE_TABS;
  const tabs = isQueue ? queueTabs : DOC_TABS;
  const counts = data.counts;

  const tabCount = (t) => typeof t.count === "function" ? t.count(counts, data.items) : 0;

  const rowsFor = () => {
    let items = [...data.items];
    if (isQueue) {
      if (filters.tab === "unassigned") items = items.filter((d) => !d.assignee);
      else if (filters.tab === "low") items = items.filter((d) => d.low_count > 0);
      else if (filters.tab === "invalid") items = items.filter((d) => d.invalid_count > 0);
      else if (filters.tab === "overdue") items = items.filter((d) => d.sla_state === "overdue");
      else if (filters.tab === "escalated") items = items.filter((d) => d.status === "escalated");
    } else if (filters.tab !== "all") {
      items = items.filter((d) => d.status === filters.tab);
    }
    if (filters.q) {
      const q = filters.q.toLowerCase();
      items = items.filter((d) => [d.ref, d.customer_name, d.doc_type_label, d.language_name, d.script, d.assignee?.name]
        .filter(Boolean).some((v) => String(v).toLowerCase().includes(q)));
    }
    if (filters.type) items = items.filter((d) => d.doc_type === filters.type);
    if (filters.script) items = items.filter((d) => d.script === filters.script);
    const sorters = {
      risk: (a, b) => b.risk - a.risk,
      due: (a, b) => (a.due_in_minutes ?? 99999) - (b.due_in_minutes ?? 99999),
      confidence: (a, b) => a.confidence - b.confidence,
      recent: (a, b) => new Date(b.submitted_at) - new Date(a.submitted_at),
    };
    items.sort(sorters[filters.sort] || sorters.risk);
    return items;
  };

  const docs = [...data.items];
  const types = [...new Map(docs.map((d) => [d.doc_type, d.doc_type_label])).entries()];
  const scripts = [...new Set(docs.map((d) => d.script).filter(Boolean))].sort();

  const tabsHtml = tabs.map((t) => `
    <button class="filter-tab ${filters.tab === t.id ? "active" : ""}" data-tab="${t.id}">${t.label}<span class="n">${tabCount(t)}</span></button>`).join("");

  const selectHtml = (name, options, selected, placeholder) => `
    <select class="mini-select" data-filter="${name}">
      <option value="">${placeholder}</option>
      ${options.map(([v, l]) => `<option value="${esc(v)}" ${selected === v ? "selected" : ""}>${esc(l)}</option>`).join("")}
    </select>`;

  const rowHtml = (d) => {
    const due = dueLabel(d);
    return `<tr data-id="${esc(d.id)}">
      <td>
        <div class="doc-cell">
          <span class="doc-tile">${icon(docIcon[d.doc_type] || "fileText")}</span>
          <div style="min-width:0">
            <div class="doc-ref">${esc(d.ref)} · ${esc(qualityLabel(d.quality))}</div>
            <div class="doc-name">${esc(d.customer_name || "Unknown customer")}</div>
            <div class="doc-sub">${esc(d.doc_type_label)} · ${d.field_count} fields${d.pages > 1 ? ` · ${d.pages} pages` : ""}</div>
          </div>
        </div>
      </td>
      <td class="type-cell">${esc(d.doc_type_label)}<span>${esc(d.source && d.source.startsWith("upload") ? "Uploaded scan" : "Branch scan")}</span></td>
      <td>${languageChips(d)}</td>
      <td>${confBar(d.confidence)}</td>
      <td class="status-cell">${statusPill(d.status)}${d.is_high_value ? `<span class="pill pill-gold" style="margin-left:4px">${icon("flag", "icon-sm")} High value</span>` : ""}</td>
      <td><div class="assignee-cell">${d.assignee ? `${avatar(d.assignee, "avatar-sm")}<span>${esc(d.assignee.name)}</span>` : `<span class="unassigned">Unassigned</span>`}</div></td>
      <td class="due-cell ${due.tone}"><strong>${esc(due.main)}</strong><span>${esc(due.sub)}</span></td>
      <td style="text-align:right"><span class="row-chevron">${icon("chevronRight")}</span></td>
    </tr>`;
  };

  const emptyTitle = isQueue ? "The queue is clear" : "No documents here";
  const emptyText = filters.q ? `No results for “${filters.q}”. Try a different reference, customer or script.` : "Nothing matches this filter right now.";

  const headerTitle = isQueue ? "Review queue" : "Documents";
  const headerLede = isQueue
    ? "Work that needs a human decision, ordered by risk. Every edit is grounded to the scan and written to the audit trail."
    : "The complete intake ledger, including straight-through documents, closed reviews and rescan requests.";

  setView(`
    <div class="page-head">
      <div>
        <div class="eyebrow">${isQueue ? "Human review" : "Intake ledger"}</div>
        <h1>${headerTitle}</h1>
        <p class="lede">${headerLede}</p>
      </div>
      <div class="page-head-actions">
        <button class="btn" data-export>${icon("download", "icon-sm")} Export view</button>
        <button class="btn btn-primary" data-intake>${icon("plus", "icon-sm")} New intake</button>
      </div>
    </div>

    <div class="queue-toolbar">
      <div class="filter-tabs" id="queue-tabs">${tabsHtml}</div>
      <div class="queue-tools">
        <div class="search-input">${icon("search")}<input id="queue-search" value="${esc(filters.q)}" placeholder="Search queue" aria-label="Search queue"></div>
        ${selectHtml("type", types, "", "All document types")}
        ${selectHtml("script", scripts.map((s) => [s, s]), "", "All scripts")}
        <select class="mini-select" data-filter="sort">
          <option value="risk">Sort: risk</option>
          <option value="due">Sort: due date</option>
          <option value="confidence">Sort: confidence</option>
          <option value="recent">Sort: newest</option>
        </select>
      </div>
    </div>

    <section class="card table-card">
      <div class="table-scroll">
        <table class="data-table">
          <thead><tr>
            <th>Document</th><th>Type</th><th>Language</th><th>Confidence</th>
            <th>Status</th><th>Assignee</th><th>Due</th><th></th>
          </tr></thead>
          <tbody id="queue-body"></tbody>
        </table>
      </div>
      <div id="queue-empty" hidden>${""}</div>
    </section>
  `, (root) => {
    const tbody = qs("#queue-body", root);
    const empty = qs("#queue-empty", root);

    const paint = () => {
      const items = rowsFor();
      tbody.innerHTML = items.map(rowHtml).join("");
      empty.hidden = items.length > 0;
      if (!items.length) {
        empty.innerHTML = `<div class="table-empty">
          <div class="empty-mark">${icon("inbox", "icon-lg")}</div>
          <h3>${esc(emptyTitle)}</h3>
          <p>${esc(emptyText)}</p>
        </div>`;
      }
      tbody.querySelectorAll("tr[data-id]").forEach((tr) => {
        tr.addEventListener("click", () => navigate(`/review/${tr.dataset.id}`));
      });
    };

    root.querySelectorAll("[data-tab]").forEach((btn) => {
      btn.addEventListener("click", () => {
        filters.tab = btn.dataset.tab;
        root.querySelectorAll("[data-tab]").forEach((b) => b.classList.toggle("active", b === btn));
        paint();
      });
    });
    const search = qs("#queue-search", root);
    search?.addEventListener("input", debounce(() => { filters.q = search.value.trim(); paint(); }, 120));
    root.querySelectorAll("[data-filter]").forEach((sel) => {
      sel.addEventListener("change", () => {
        filters[sel.dataset.filter] = sel.value;
        paint();
      });
    });
    root.querySelector("[data-export]")?.addEventListener("click", () => {
      const items = rowsFor();
      const head = ["Reference", "Customer", "Type", "Language", "Script", "Status", "Confidence", "Assignee", "Due", "Amount"];
      const csv = [head, ...items.map((d) => [
        d.ref, d.customer_name, d.doc_type_label, d.language_name, d.script, d.status,
        Math.round(d.confidence * 100) + "%", d.assignee?.name || "", d.due_at, d.amount ?? "",
      ])].map((row) => row.map((v) => `"${String(v ?? "").replaceAll('"', '""')}"`).join(",")).join("\n");
      const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = `akshara-${isQueue ? "queue" : "documents"}-${new Date().toISOString().slice(0, 10)}.csv`;
      a.click();
      URL.revokeObjectURL(a.href);
      toast(`Exported ${items.length} rows.`, "success");
    });
    root.querySelector("[data-intake]")?.addEventListener("click", async () => {
      const { openIntake } = await import("../intake.js");
      openIntake();
    });
    paint();
  });
}

