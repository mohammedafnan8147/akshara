import { api } from "../api.js";
import { icon } from "../icons.js";
import { state, loadSession } from "../store.js";
import {
  esc, avatar, statusPill, priorityPill, confBar, confTone, languageChips,
  qualityLabel, fmtDateTime, relative, amountFmt, duration, navigate,
} from "../utils.js";
import {
  modal, closeModal, toast, loadingView, errorView, refreshSidebarCounts,
} from "../components.js";

export async function renderReview(view, route) {
  view.className = "view flush";
  view.innerHTML = loadingView("Opening document");
  let doc;
  try {
    doc = await api.document(route.id);
  } catch (e) {
    view.className = "view";
    view.innerHTML = errorView(e);
    return;
  }

  let tab = "fields";
  let overlayMode = "issues";
  let heat = false;
  let zoom = 1;
  let activeId = null;
  let editing = null;
  let currentPage = (doc.fields.find((f) => f.value)?.page) || 1;

  const low = (f) => f.confidence < 0.8;
  const invalid = (f) => f.validation_status === "invalid";
  const isRtl = (text) => /[\u0590-\u08ff]/.test(text || "");

  const groups = () => {
    const out = [];
    for (const f of doc.fields) {
      const section = f.section || "Document details";
      if (!out.length || out[out.length - 1].name !== section) out.push({ name: section, fields: [] });
      out[out.length - 1].fields.push(f);
    }
    return out;
  };

  const activeField = () => doc.fields.find((f) => f.id === activeId);
  const pageData = () => (doc.page_images || []).find((p) => p.no === currentPage)
    || (doc.page_images || [])[0]
    || { no: 1, url: doc.image_url, width: doc.width, height: doc.height };

  const progressRing = (p) => {
    const r = 13, c = 2 * Math.PI * r;
    const off = c * (1 - Math.max(0, Math.min(1, p / 100)));
    return `<svg class="progress-ring" viewBox="0 0 32 32" aria-hidden="true">
      <circle cx="16" cy="16" r="${r}" fill="none" stroke="#ece7dc" stroke-width="3"/>
      <circle cx="16" cy="16" r="${r}" fill="none" stroke="#1f6a5b" stroke-width="3" stroke-linecap="round"
        stroke-dasharray="${c}" stroke-dashoffset="${off}" transform="rotate(-90 16 16)"/>
    </svg>`;
  };

  const overlayBoxes = () => {
    if (overlayMode === "off") return "";
    const page = pageData();
    const pw = page.width || doc.width || 1240;
    const ph = page.height || doc.height || 1754;
    return doc.fields.filter((f) => (f.page || 1) === currentPage && f.bbox && (f.bbox[2] > 0 || f.bbox[3] > 0)).map((f) => {
      const [x, y, w, h] = f.bbox;
      const left = (x / pw) * 100;
      const top = (y / ph) * 100;
      const width = (w / pw) * 100;
      const height = (h / ph) * 100;
      const isActive = f.id === activeId;
      const tone = confTone(f.confidence);
      const visible = overlayMode === "all" || (overlayMode === "issues" && (low(f) || invalid(f))) || isActive;
      if (!visible) return "";
      let cls = "";
      if (isActive) cls = "active";
      else if (invalid(f)) cls = "invalid";
      else if (low(f)) cls = "low";
      else if (f.verified) cls = "verified";
      if (heat) cls += " heat";
      const heatStyle = heat
        ? `background:rgba(${tone === "green" ? "45,114,85" : tone === "amber" ? "171,117,33" : "180,70,63"},.12);border-color:rgba(${tone === "green" ? "45,114,85" : tone === "amber" ? "171,117,33" : "180,70,63"},.55);`
        : "";
      return `<button class="overlay-box ${cls}" style="left:${left}%;top:${top}%;width:${width}%;height:${height}%;${heatStyle}"
        data-overlay-field="${esc(f.id)}" aria-label="${esc(f.label)}">
        ${isActive ? `<span class="tag">${esc(f.label)} · ${Math.round(f.confidence * 100)}%</span>` : ""}
      </button>`;
    }).join("");
  };

  const fieldRow = (f) => {
    const active = f.id === activeId;
    const bad = invalid(f);
    const isEditing = editing === f.id;
    const value = f.value || "";
    const old = f.corrected && f.original_value && f.original_value !== f.value;
    const rtl = f.dir === "rtl" || isRtl(value);
    const side = doc.actions.edit && !isEditing
      ? `<button class="icon-btn" data-edit="${esc(f.id)}" title="Edit field">${icon("edit")}</button>
         <button class="icon-btn" data-locate="${esc(f.id)}" title="Find on scan">${icon("scan")}</button>`
      : "";
    const input = isEditing
      ? `<div class="field-edit">
          <textarea class="field-input" rows="${value.length > 55 ? 2 : 1}" data-edit-input="${esc(f.id)}" ${rtl ? 'dir="rtl"' : ""}>${esc(value)}</textarea>
          <div class="field-edit-actions">
            <button class="btn btn-sm btn-primary" data-save="${esc(f.id)}">${icon("check", "icon-sm")} Save</button>
            <button class="btn btn-sm" data-cancel="${esc(f.id)}">Cancel</button>
            <span class="hint">Enter to save · Esc to cancel</span>
          </div>
        </div>`
      : `<div class="field-value ${value ? "" : "placeholder"} ${rtl ? "rtl" : ""}" ${rtl ? 'dir="rtl"' : ""}>
          ${old ? `<span class="old" title="Model output">${esc(f.original_value)}</span>` : ""}${esc(value || "Not detected")}
        </div>`;
    return `<div class="field-row ${active ? "active" : ""} ${bad ? "invalid" : ""}" data-field-row="${esc(f.id)}">
      <div class="field-main">
        <div class="field-label-row">
          <span class="field-label" title="${esc(f.label_sub || f.label)}">${esc(f.label)}${f.required ? "" : " · optional"}</span>
          <span class="field-conf ${f.confidence < 0.7 ? "bad" : low(f) ? "low" : ""}">${Math.round(f.confidence * 100)}%</span>
          ${doc.pages > 1 ? `<span class="field-page">p.${f.page || 1}</span>` : ""}
          ${f.verified ? `<span title="Verified by a human">${icon("checkCircle", "verified-mark")}</span>` : ""}
          ${f.corrected ? `<span class="pill pill-blue" style="font-size:8px;padding:1px 4px">Corrected</span>` : ""}
        </div>
        ${input}
        ${f.validation_message ? `<div class="field-message ${f.validation_status}">${icon(f.validation_status === "invalid" ? "alertCircle" : "alert", "icon-sm")}<span>${esc(f.validation_message)}</span></div>` : ""}
      </div>
      <div class="field-side">${side}</div>
    </div>`;
  };

  const fieldsHtml = () => {
    const banner = !doc.assignee && doc.actions.claim
      ? `<div class="claim-banner">${icon("user")}<div><strong>This document is unassigned.</strong><span>Claim it to start reviewing. Every decision is attributed to you.</span></div><button class="btn btn-sm btn-primary" data-claim>Claim document</button></div>`
      : doc.assignee && doc.assignee.id !== state.user.id && ["queued", "in_review", "escalated"].includes(doc.status)
        ? `<div class="locked-banner">${icon("lock")} Assigned to <strong>${esc(doc.assignee.name)}</strong>. Supervisors can review; reviewers should coordinate before editing.</div>`
        : doc.status === "needs_rescan"
          ? `<div class="locked-banner">${icon("refresh")} A fresh scan has been requested. This document is paused.</div>`
          : ["approved", "rejected", "auto_approved"].includes(doc.status)
            ? `<div class="locked-banner">${icon("lock")} Closed ${doc.reviewed_at ? relative(doc.reviewed_at) : ""}. The extraction and every human edit are preserved in the audit trail.</div>`
            : "";
    return `${banner}
      <div class="fields-scroll">
        ${groups().map((g) => `<div class="field-group">
          <div class="field-group-head"><h3>${esc(g.name)}</h3><span class="line"></span><span class="n">${g.fields.length}</span></div>
          ${g.fields.map(fieldRow).join("")}
        </div>`).join("")}
      </div>`;
  };

  const activityHtml = () => `<div class="timeline">
    ${doc.events.map((e) => {
      const strong = ["document.approved", "document.rejected", "document.escalated", "document.auto_approved"].includes(e.action);
      return `<div class="timeline-item ${strong ? "strong" : ""}">
        <span class="timeline-dot"></span>
        <div class="t-head"><strong>${esc(e.detail || e.action)}</strong><span>${fmtDateTime(e.created_at)}</span></div>
        <p>${e.user ? `${esc(e.user.name)} · ` : "Akshara · "}${relative(e.created_at)}</p>
      </div>`;
    }).join("") || `<p class="muted small">No activity yet.</p>`}
  </div>`;

  const ocrHtml = () => {
    if (!doc.ocr_text) {
      return `<div class="empty-state" style="padding-top:54px">
        ${icon("scan", "icon-lg")}
        <h3 style="font-family:var(--font-display);font-size:20px;margin-top:10px">Specimen extraction</h3>
        <p style="max-width:320px;margin:6px auto 0;font-size:11.5px;line-height:1.6">This document came from the bundled specimen adapter. Its field boxes and confidence scores are exact by construction; raw OCR text is not part of the fixture.</p>
      </div>`;
    }
    const m = doc.ocr_meta || {};
    return `<div class="ocr-pane">
      <div class="ocr-meta">
        <div class="ocr-stat"><span>Engine</span><strong>${esc(m.engine || doc.engine || "Tesseract")}</strong></div>
        <div class="ocr-stat"><span>Words</span><strong>${esc(m.words ?? "—")}</strong></div>
        <div class="ocr-stat"><span>OCR confidence</span><strong>${m.mean_confidence != null ? Math.round(m.mean_confidence * 100) + "%" : "—"}</strong></div>
        <div class="ocr-stat"><span>Fields read</span><strong>${esc(m.extracted ?? "—")} / ${esc(m.total ?? "—")}</strong></div>
      </div>
      <div class="ocr-note">${icon("info", "icon-sm")}<span>Raw local OCR output. Language: ${esc(m.language || "—")}${m.requested_language && m.requested_language !== m.language ? ` (requested ${esc(m.requested_language)})` : ""} · ${esc(m.pages ?? 1)} page${(m.pages ?? 1) === 1 ? "" : "s"} · page segmentation ${esc(m.psm ?? "—")}. Low-confidence values are routed to review, never auto-approved.</span></div>
      <pre class="ocr-text">${esc(doc.ocr_text)}</pre>
    </div>`;
  };

  const commentsHtml = () => `<div class="comments-wrap">
    ${doc.comments.map((c) => `<div class="comment">
      ${avatar(c.user)}
      <div class="comment-body">
        <div class="comment-head"><strong>${esc(c.user?.name || "System")}</strong><span>${relative(c.created_at)}</span></div>
        <p>${esc(c.body)}</p>
      </div>
    </div>`).join("") || `<p class="muted small">No comments yet. Leave context for the next reviewer.</p>`}
    <form class="comment-form" id="comment-form">
      <input class="input" id="comment-input" placeholder="Add a review note…" maxlength="900" aria-label="Review note">
      <button class="btn btn-primary" type="submit">${icon("message", "icon-sm")} Add</button>
    </form>
  </div>`;

  const footer = () => {
    if (["approved", "rejected"].includes(doc.status)) {
      return `<div class="review-footer">
        <span class="footer-note">Closed ${doc.reviewed_at ? relative(doc.reviewed_at) : ""} by ${esc(doc.reviewer?.name || "a reviewer")}. Corrections remain in the audit trail.</span>
        <div class="spacer"></div>
        ${doc.actions.reopen ? `<button class="btn" data-reopen>${icon("refresh", "icon-sm")} Reopen document</button>` : ""}
        <a class="btn btn-primary" href="#/queue">Back to queue</a>
      </div>`;
    }
    if (doc.status === "auto_approved") {
      return `<div class="review-footer"><span class="footer-note">Straight-through processing. No human decision was required.</span><div class="spacer"></div><a class="btn" href="#/queue">Back to queue</a></div>`;
    }
    if (doc.status === "needs_rescan") {
      return `<div class="review-footer"><span class="footer-note">Waiting for a fresh scan. The document will return to the queue when received.</span><div class="spacer"></div><a class="btn" href="#/queue">Back to queue</a></div>`;
    }
    const claim = doc.actions.claim ? `<button class="btn btn-primary" data-claim>${icon("user", "icon-sm")} Claim to review</button>` : "";
    const verify = doc.actions.verify_high_confidence
      ? `<button class="btn btn-sm" data-verify>${icon("checkCircle", "icon-sm")} Verify ≥90%</button>` : "";
    const approveLabel = doc.is_high_value && state.user.role === "reviewer" ? "Supervisor approval" : "Approve & next";
    const approve = doc.actions.approve
      ? `<button class="btn btn-primary" data-approve>${icon("check", "icon-sm")} ${approveLabel}</button>`
      : !doc.actions.claim && doc.actions.supervisor
        ? `<button class="btn" data-approve title="Claim or assign the document first">${icon("lock", "icon-sm")} Approve</button>`
        : "";
    return `<div class="review-footer">
      ${verify}
      ${claim}
      <div class="spacer"></div>
      ${doc.actions.rescan ? `<button class="btn" data-rescan>${icon("refresh", "icon-sm")} Rescan</button>` : ""}
      ${doc.actions.escalate ? `<button class="btn" data-escalate>${icon("flag", "icon-sm")} Escalate</button>` : ""}
      ${doc.actions.reject ? `<button class="btn btn-danger" data-reject>${icon("x", "icon-sm")} Reject</button>` : ""}
      ${approve}
    </div>`;
  };

  const topActions = () => {
    const items = [];
    if (doc.actions.claim) items.push(`<button class="btn btn-sm btn-primary" data-claim>${icon("user", "icon-sm")} Claim</button>`);
    if (doc.actions.release) items.push(`<button class="btn btn-sm" data-release>${icon("arrowLeft", "icon-sm")} Return to queue</button>`);
    if (doc.actions.reopen) items.push(`<button class="btn btn-sm" data-reopen>${icon("refresh", "icon-sm")} Reopen</button>`);
    return items.join("");
  };

  const paint = () => {
    view.className = "view flush";
    view.innerHTML = `
      <div class="review-view">
        <div class="review-topline">
          <a class="back" href="#/queue">${icon("arrowLeft", "icon-sm")} Queue</a>
          <span class="doc-id">${esc(doc.ref)}</span>
          ${statusPill(doc.status)}
          ${priorityPill(doc.priority)}
          ${doc.is_high_value ? `<span class="pill pill-gold">${icon("flag", "icon-sm")} High value</span>` : ""}
          <span class="spacer"></span>
          ${doc.assignee ? `<span class="assignee-cell">${avatar(doc.assignee, "avatar-sm")}<span>${esc(doc.assignee.name)}</span></span>` : `<span class="assignee-cell"><span class="unassigned">Unassigned</span></span>`}
          ${topActions()}
        </div>
        <div class="review-grid">
          <section class="doc-pane">
            <div class="doc-toolbar">
              <div class="group">
                <button class="icon-btn" data-zoom-out title="Zoom out">${icon("zoomOut")}</button>
                <span class="zoom-label" id="zoom-label">${Math.round(zoom * 100)}%</span>
                <button class="icon-btn" data-zoom-in title="Zoom in">${icon("zoomIn")}</button>
                <button class="icon-btn" data-fit title="Fit width">${icon("maximize")}</button>
              </div>
              <div class="group">
                <button class="icon-btn ${overlayMode === "issues" ? "active" : ""}" data-overlay-btn="issues" title="Show issues only">${icon("alert")}</button>
                <button class="icon-btn ${overlayMode === "all" ? "active" : ""}" data-overlay-btn="all" title="Show all field boxes">${icon("layers")}</button>
                <button class="icon-btn ${overlayMode === "off" ? "active" : ""}" data-overlay-btn="off" title="Hide overlays">${icon("eye")}</button>
              </div>
              <div class="group">
                <button class="icon-btn ${heat ? "active" : ""}" data-heat title="Confidence heatmap">${icon("scan")}</button>
              </div>
              <span class="spacer"></span>
              <div class="group">
                <button class="icon-btn" data-page-prev title="Previous page" ${currentPage <= 1 ? "disabled" : ""}>${icon("chevronLeft")}</button>
                <span class="page-label" id="page-label">${currentPage} / ${doc.pages || 1}</span>
                <button class="icon-btn" data-page-next title="Next page" ${currentPage >= (doc.pages || 1) ? "disabled" : ""}>${icon("chevronRight")}</button>
              </div>
            </div>
            <div class="doc-viewer">
              <div class="paper-wrap" id="paper" style="width:${Math.round(640 * zoom)}px">
                <img id="paper-img" src="${esc(pageData().url)}" width="${pageData().width}" height="${pageData().height}" alt="Scanned ${esc(doc.doc_type_label)} for ${esc(doc.customer_name || "customer")}" draggable="false">
                <div class="overlay-layer" id="overlay-layer">${overlayBoxes()}</div>
                <span class="paper-note">Source scan · demo</span>
              </div>
            </div>
            <div class="doc-caption">
              <span>${esc(doc.language_name)} · ${esc(doc.script)} · ${esc(qualityLabel(doc.quality))}${doc.pages > 1 ? ` · ${doc.pages} pages` : ""}</span>
              <span class="legend">
                <span><i class="legend-dot" style="background:#ab7521"></i>Low confidence</span>
                <span><i class="legend-dot" style="background:#b4463f"></i>Validation</span>
                <span><i class="legend-dot" style="background:#1f6a5b"></i>Selected</span>
              </span>
            </div>
          </section>

          <aside class="review-pane">
            <div class="review-summary">
              <div class="top-row">
                <span class="doc-icon-lg">${icon(docIcon(doc.doc_type))}</span>
                <div style="min-width:0;flex:1">
                  <div class="eyebrow">${esc(doc.doc_type_label)} · ${esc(doc.ref)}</div>
                  <h2 ${isRtl(doc.customer_name) ? 'dir="rtl"' : ""}>${esc(doc.customer_name || "Unknown customer")}</h2>
                  <div class="sub">${esc(doc.language_name)} · ${esc(doc.script)} · ${esc(qualityLabel(doc.quality))}${doc.amount ? ` · ${amountFmt(doc.amount)}` : ""}</div>
                </div>
                ${confBar(doc.confidence)}
              </div>
              <div class="badges">${languageChips(doc)}${doc.ocr_text ? `<span class="pill pill-blue">${icon("scan", "icon-sm")} Local OCR</span>` : ""}${doc.is_high_value ? `<span class="pill pill-gold">High value</span>` : ""}${doc.validation.invalid ? `<span class="pill pill-red">${doc.validation.invalid} blocking</span>` : `<span class="pill pill-green">${icon("check", "icon-sm")} Valid</span>`}${doc.low_count ? `<span class="pill pill-amber">${doc.low_count} low confidence</span>` : ""}</div>
              <div class="review-metrics">
                <div class="review-metric"><div><div class="metric-label">Confidence</div><div class="metric-value">${Math.round(doc.confidence * 100)}<span style="font-size:11px;color:var(--faint)">%</span></div></div></div>
                <div class="review-metric"><div><div class="metric-label">Fields</div><div class="metric-value">${doc.field_count}</div></div></div>
                <div class="review-metric"><div><div class="metric-label">Corrected</div><div class="metric-value">${doc.corrected_count}</div></div></div>
                <div class="review-progress">${progressRing(doc.progress.percent)}<span>${doc.progress.verified}/${doc.progress.total} verified</span></div>
              </div>
              ${doc.notes ? `<div class="field-message" style="color:var(--muted);margin-top:10px">${icon("info", "icon-sm")}<span>${esc(doc.notes)}</span></div>` : ""}
            </div>

            <div class="review-tabs">
              <button class="review-tab ${tab === "fields" ? "active" : ""}" data-tab="fields">Fields <span class="count">${doc.field_count}</span></button>
              <button class="review-tab ${tab === "ocr" ? "active" : ""}" data-tab="ocr">OCR <span class="count">${doc.ocr_meta?.words || "—"}</span></button>
              <button class="review-tab ${tab === "activity" ? "active" : ""}" data-tab="activity">Activity <span class="count">${doc.events.length}</span></button>
              <button class="review-tab ${tab === "comments" ? "active" : ""}" data-tab="comments">Notes <span class="count">${doc.comments.length}</span></button>
            </div>
            <div class="review-body" id="review-body">
              ${tab === "fields" ? fieldsHtml() : tab === "ocr" ? ocrHtml() : tab === "activity" ? activityHtml() : commentsHtml()}
            </div>
            ${footer()}
          </aside>
        </div>
      </div>`;
    bind();
  };

  const docIcon = (type) => ({
    bank: "bank", claim: "heart", service: "headset",
    loan: "landmark", invoice: "receipt", kyc: "shield",
  }[type] || "fileText");

  const sync = async () => {
    try {
      await loadSession();
      refreshSidebarCounts();
    } catch {}
  };

  const goNext = async () => {
    try {
      const data = await api.documents({ view: "queue", limit: 50 });
      state.counts = data.counts;
      const next = data.items.find((d) => d.id !== doc.id);
      if (next) navigate(`/review/${next.id}`);
      else navigate("/queue");
    } catch {
      navigate("/queue");
    }
  };

  const callAction = async (action, body = {}, label = "Done") => {
    try {
      const res = await api.action(doc.id, action, body);
      doc = res.document;
      toast(label, "success");
      await sync();
      paint();
      return true;
    } catch (e) {
      if (e.code === "validation_blocked" && e.details?.length) {
        showBlocked(e.details, e.message);
      } else if (e.code === "supervisor_required") {
        showSupervisorRequired(e.message);
      } else {
        toast(e.message, "error");
      }
      return false;
    }
  };

  const showBlocked = (issues, message) => {
    const body = `<p class="muted" style="font-size:12px;line-height:1.6">${esc(message || "Resolve these issues before approval.")}</p>
      <div class="issue-list">${issues.map((i) => `<div class="issue">${icon("alertCircle")}<div>${esc(i.message || i)}</div></div>`).join("")}</div>
      ${state.user.role === "supervisor" || state.user.role === "admin" ? `<p class="modal-note" style="margin-top:12px">As a supervisor you can override with a written reason. The override is recorded in the audit trail.</p>` : `<p class="modal-note" style="margin-top:12px">Ask a supervisor to review or override these blockers.</p>`}`;
    const footer = `<button class="btn" data-close>Close</button>
      ${state.user.role === "supervisor" || state.user.role === "admin" ? `<button class="btn btn-danger" data-override>Override & approve</button>` : `<button class="btn" data-escalate-modal>Escalate</button>`}`;
    const ov = modal({ title: "Blocking validation issues", subtitle: "The document cannot be approved as-is", iconName: "alert", body, footer });
    ov.querySelector("[data-override]")?.addEventListener("click", () => { closeModal(); showOverride(issues); });
    ov.querySelector("[data-escalate-modal]")?.addEventListener("click", () => { closeModal(); showReason("escalate"); });
  };

  const showOverride = (issues) => {
    const body = `<p class="muted" style="font-size:12px;line-height:1.6">You are approving despite ${issues.length} blocking issue${issues.length === 1 ? "" : "s"}. Record why this is acceptable — it becomes part of the permanent audit record.</p>
      <div class="issue-list">${issues.map((i) => `<div class="issue">${icon("alertCircle")}<div>${esc(i.message || i)}</div></div>`).join("")}</div>
      <label class="field-label-top" for="override-reason" style="margin-top:14px">Override reason</label>
      <textarea class="textarea" id="override-reason" placeholder="e.g. Verified against the original branch record; rescan requested separately."></textarea>`;
    const footer = `<button class="btn" data-close>Cancel</button><button class="btn btn-danger" data-confirm disabled>Approve with override</button>`;
    const ov = modal({ title: "Supervisor override", subtitle: "This bypass is logged", iconName: "lock", body, footer });
    const input = ov.querySelector("#override-reason");
    const confirm = ov.querySelector("[data-confirm]");
    input.addEventListener("input", () => { confirm.disabled = input.value.trim().length < 8; });
    confirm.addEventListener("click", async () => {
      confirm.disabled = true;
      const ok = await callAction("approve", { override_reason: input.value.trim() }, "Approved with supervisor override.");
      if (ok) { closeModal(); await goNext(); }
      else confirm.disabled = false;
    });
  };

  const showSupervisorRequired = (message) => {
    const body = `<p class="muted" style="font-size:12.5px;line-height:1.7">${esc(message || "This document requires a supervisor decision.")}</p>
      <div class="issue" style="margin-top:12px;border-color:#e7d7b2;background:var(--amber-soft);color:var(--amber)">${icon("shield")}<div>High-value approvals require an <strong>operations supervisor</strong>. You can escalate this document with a note, or sign in as Arjun Mehta to approve it.</div></div>`;
    const footer = `<button class="btn" data-close>Close</button><button class="btn btn-primary" data-escalate-modal>${icon("flag", "icon-sm")} Escalate to supervisor</button>`;
    const ov = modal({ title: "Supervisor approval required", subtitle: "Four-eyes policy", iconName: "shield", body, footer });
    ov.querySelector("[data-escalate-modal]").addEventListener("click", () => { closeModal(); showReason("escalate"); });
  };

  const showReason = (kind) => {
    const config = {
      reject: { title: "Reject this document", sub: "The rejection reason is shared with the submitter.", icon: "x", placeholder: "e.g. Duplicate submission; original already settled.", label: "Reject document", tone: "danger" },
      rescan: { title: "Request a fresh scan", sub: "The document returns to intake when the new scan arrives.", icon: "refresh", placeholder: "e.g. Page is cropped and the account number is unreadable.", label: "Request rescan", tone: "primary" },
      escalate: { title: "Escalate to a supervisor", sub: "The document is marked urgent and routed for a senior decision.", icon: "flag", placeholder: "e.g. High-value claim above ₹4,00,000; policy exception requested.", label: "Escalate", tone: "primary" },
    }[kind];
    const body = `<p class="muted" style="font-size:12px;line-height:1.6">${esc(config.sub)}</p>
      <label class="field-label-top" for="reason" style="margin-top:14px">Reason</label>
      <textarea class="textarea" id="reason" placeholder="${esc(config.placeholder)}"></textarea>`;
    const footer = `<button class="btn" data-close>Cancel</button><button class="btn ${config.tone === "danger" ? "btn-danger" : "btn-primary"}" data-confirm disabled>${esc(config.label)}</button>`;
    const ov = modal({ title: config.title, iconName: config.icon, body, footer });
    const input = ov.querySelector("#reason");
    const confirm = ov.querySelector("[data-confirm]");
    input.addEventListener("input", () => { confirm.disabled = input.value.trim().length < 4; });
    confirm.addEventListener("click", async () => {
      confirm.disabled = true;
      const bodyKey = kind === "reject" ? "reason" : "reason";
      const ok = await callAction(kind, { [bodyKey]: input.value.trim() }, kind === "reject" ? "Document rejected." : kind === "rescan" ? "Rescan requested." : "Escalated to supervisor.");
      if (ok) closeModal();
      else confirm.disabled = false;
    });
  };

  const approve = async () => {
    if (!doc.actions.approve) {
      toast(doc.actions.claim ? "Claim the document before approving." : "This document is not open for approval.", "info");
      return;
    }
    if (doc.is_high_value && state.user.role === "reviewer" && (state.settings.require_supervisor_high_value ?? true)) {
      showSupervisorRequired("This document exceeds the high-value threshold.");
      return;
    }
    if (doc.blocking_issues?.length) {
      showBlocked(doc.blocking_issues, "Resolve or override these blocking issues before approval.");
      return;
    }
    const ok = await callAction("approve", {}, "Document approved.");
    if (ok) {
      await sync();
      await goNext();
    }
  };

  const selectField = (id, scroll = true) => {
    activeId = id;
    const target = activeField();
    if (target && doc.pages > 1 && (target.page || 1) !== currentPage) {
      currentPage = target.page || 1;
      paint();
      setTimeout(() => selectField(id, scroll), 0);
      return;
    }
    refreshOverlay();
    const rows = view.querySelectorAll("[data-field-row]");
    rows.forEach((r) => r.classList.toggle("active", r.dataset.fieldRow === id));
    view.querySelectorAll("[data-overlay-field]").forEach((b) => {
      b.classList.toggle("active", b.dataset.overlayField === id);
    });
    const box = view.querySelector(`[data-overlay-field="${CSS.escape(id)}"]`);
    if (box && scroll) box.scrollIntoView({ block: "center", inline: "center", behavior: "smooth" });
  };

  const refreshOverlay = () => {
    const layer = view.querySelector("#overlay-layer");
    if (layer) layer.innerHTML = overlayBoxes();
    bindOverlay();
  };

  const bindOverlay = () => {
    view.querySelectorAll("[data-overlay-field]").forEach((b) => {
      b.addEventListener("click", () => {
        const input = view.querySelector(`[data-edit="${CSS.escape(b.dataset.overlayField)}"]`);
        selectField(b.dataset.overlayField, false);
        const row = view.querySelector(`[data-field-row="${CSS.escape(b.dataset.overlayField)}"]`);
        row?.scrollIntoView({ block: "center", behavior: "smooth" });
      });
    });
  };

  const bindFields = () => {
    view.querySelectorAll("[data-field-row]").forEach((row) => {
      row.addEventListener("click", (e) => {
        if (e.target.closest("button, textarea, input")) return;
        selectField(row.dataset.fieldRow, false);
      });
    });
    view.querySelectorAll("[data-edit]").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        editing = btn.dataset.edit;
        activeId = editing;
        paint();
        const input = view.querySelector("[data-edit-input]");
        input?.focus();
        input?.setSelectionRange(input.value.length, input.value.length);
      });
    });
    view.querySelectorAll("[data-locate]").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        selectField(btn.dataset.locate, true);
      });
    });
    view.querySelectorAll("[data-save]").forEach((btn) => {
      btn.addEventListener("click", () => saveField(btn.dataset.save));
    });
    view.querySelectorAll("[data-cancel]").forEach((btn) => {
      btn.addEventListener("click", () => { editing = null; paint(); });
    });
    view.querySelectorAll("[data-edit-input]").forEach((input) => {
      input.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); saveField(input.dataset.editInput); }
        if (e.key === "Escape") { e.preventDefault(); editing = null; paint(); }
      });
    });
  };

  const saveField = async (id) => {
    const input = view.querySelector(`[data-edit-input="${CSS.escape(id)}"]`);
    if (!input) return;
    const value = input.value.trim();
    try {
      const res = await api.updateField(id, value);
      doc = res.document;
      editing = null;
      toast("Field saved and verified.", "success");
      await sync();
      paint();
    } catch (e) {
      toast(e.message, "error");
    }
  };

  const bindTabs = () => {
    view.querySelectorAll("[data-tab]").forEach((btn) => {
      btn.addEventListener("click", () => {
        tab = btn.dataset.tab;
        paint();
      });
    });
    if (tab === "comments") {
      view.querySelector("#comment-form")?.addEventListener("submit", async (e) => {
        e.preventDefault();
        const input = view.querySelector("#comment-input");
        if (!input.value.trim()) return;
        try {
          const res = await api.action(doc.id, "comments", { body: input.value.trim() });
          doc = res.document;
          toast("Note added.", "success");
          paint();
        } catch (ex) { toast(ex.message, "error"); }
      });
    }
  };

  let keyHandler = null;

  const bind = () => {
    bindOverlay();
    bindFields();
    bindTabs();

    view.querySelectorAll("[data-claim]").forEach((b) => b.addEventListener("click", async () => {
      const ok = await callAction("claim", {}, "Document claimed. You can now review it.");
      if (ok) activeId = null;
    }));
    view.querySelector("[data-release]")?.addEventListener("click", async () => {
      await callAction("release", {}, "Returned to the shared queue.");
    });
    view.querySelector("[data-verify]")?.addEventListener("click", async () => {
      await callAction("verify-high-confidence", {}, "High-confidence fields verified.");
    });
    view.querySelector("[data-approve]")?.addEventListener("click", approve);
    view.querySelector("[data-rescan]")?.addEventListener("click", () => showReason("rescan"));
    view.querySelector("[data-reject]")?.addEventListener("click", () => showReason("reject"));
    view.querySelector("[data-escalate]")?.addEventListener("click", () => showReason("escalate"));
    view.querySelectorAll("[data-reopen]").forEach((btn) => btn.addEventListener("click", () => {
      modal({
        title: "Reopen this document?",
        subtitle: "A new review pass will be created",
        iconName: "refresh",
        body: `<p class="muted" style="font-size:12.5px;line-height:1.65">The previous decision stays in the activity trail. The document returns to the shared queue as unassigned.</p>`,
        footer: `<button class="btn" data-close>Cancel</button><button class="btn btn-primary" data-confirm>Reopen</button>`,
      }).querySelector("[data-confirm]").addEventListener("click", async () => {
        closeModal();
        await callAction("reopen", {}, "Document reopened for review.");
      });
    }));

    // zoom & overlays
    view.querySelector("[data-zoom-in]")?.addEventListener("click", () => {
      zoom = Math.min(1.8, zoom + 0.15);
      applyZoom();
    });
    view.querySelector("[data-zoom-out]")?.addEventListener("click", () => {
      zoom = Math.max(0.55, zoom - 0.15);
      applyZoom();
    });
    view.querySelector("[data-fit]")?.addEventListener("click", () => {
      const paper = view.querySelector("#paper");
      if (!paper) return;
      paper.style.width = "100%";
      const label = view.querySelector("#zoom-label");
      if (label) label.textContent = "Fit";
    });
    view.querySelectorAll("[data-overlay-btn]").forEach((b) => b.addEventListener("click", () => {
      overlayMode = b.dataset.overlayBtn;
      view.querySelectorAll("[data-overlay-btn]").forEach((x) => x.classList.toggle("active", x === b));
      refreshOverlay();
    }));
    view.querySelector("[data-heat]")?.addEventListener("click", () => {
      heat = !heat;
      view.querySelector("[data-heat]")?.classList.toggle("active", heat);
      if (heat) overlayMode = "all";
      view.querySelectorAll("[data-overlay-btn]").forEach((x) => x.classList.toggle("active", x.dataset.overlayBtn === overlayMode));
      refreshOverlay();
    });

    view.querySelector("[data-page-prev]")?.addEventListener("click", () => {
      if (currentPage > 1) { currentPage -= 1; activeId = null; editing = null; paint(); }
    });
    view.querySelector("[data-page-next]")?.addEventListener("click", () => {
      if (currentPage < (doc.pages || 1)) { currentPage += 1; activeId = null; editing = null; paint(); }
    });

    // keyboard
    if (keyHandler) document.removeEventListener("keydown", keyHandler);
    window.__akCleanup = () => {
      if (keyHandler) document.removeEventListener("keydown", keyHandler);
      keyHandler = null;
    };
    keyHandler = (e) => {
      if (e.target.matches("input, textarea, select")) return;
      if (document.querySelector(".modal-backdrop")) return;
      if (e.key === "Escape" && activeId) { activeId = null; paint(); }
      if (e.key === "?") { showShortcuts(); }
      if (e.key === "a" || e.key === "A") { e.preventDefault(); approve(); }
      if (e.key === "r" || e.key === "R") { e.preventDefault(); if (doc.actions.rescan) showReason("rescan"); }
      if (e.key === "j" || e.key === "J" || e.key === "k" || e.key === "K") {
        e.preventDefault();
        const fields = doc.fields;
        if (!fields.length) return;
        let idx = fields.findIndex((f) => f.id === activeId);
        if (idx < 0) idx = e.key.toLowerCase() === "j" ? -1 : 0;
        idx = e.key.toLowerCase() === "j" ? Math.min(fields.length - 1, idx + 1) : Math.max(0, idx - 1);
        editing = null;
        selectField(fields[idx].id, true);
        view.querySelector(`[data-field-row="${CSS.escape(fields[idx].id)}"]`)?.scrollIntoView({ block: "center", behavior: "smooth" });
      }
    };
    document.addEventListener("keydown", keyHandler);
  };

  const applyZoom = () => {
    const paper = view.querySelector("#paper");
    if (paper) paper.style.width = `${Math.round(640 * zoom)}px`;
    const label = view.querySelector("#zoom-label");
    if (label) label.textContent = `${Math.round(zoom * 100)}%`;
  };

  const showShortcuts = () => {
    modal({
      title: "Keyboard shortcuts",
      subtitle: "For reviewers who live on the keyboard",
      iconName: "keyboard",
      body: `<div class="issue-list" style="gap:8px">
        ${[["J / K", "Next / previous field"], ["Enter", "Save the field being edited"], ["Esc", "Cancel editing or close"], ["A", "Approve when ready"], ["R", "Request a rescan"], ["?", "Open this list"]].map(([k, v]) => `<div class="issue" style="border-color:var(--line);background:var(--surface);color:var(--ink-soft)"><kbd style="font-family:var(--font-mono);font-size:10px;background:#fff;border:1px solid var(--line-2);border-radius:4px;padding:1px 5px">${k}</kbd><div>${v}</div></div>`).join("")}
      </div>`,
      footer: `<button class="btn btn-primary" data-close>Got it</button>`,
    });
  };

  paint();
}
