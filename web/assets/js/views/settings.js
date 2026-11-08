import { api } from "../api.js";
import { icon } from "../icons.js";
import { state, isSupervisor, isAdmin } from "../store.js";
import { esc } from "../utils.js";
import { setView, loadingView, errorView, toast, modal, closeModal } from "../components.js";

export async function renderSettings(view) {
  view.innerHTML = loadingView("Settings");
  let payload;
  try {
    payload = await api.settings();
  } catch (e) {
    view.innerHTML = errorView(e);
    return;
  }
  state.settings = { ...payload.settings };
  const { settings, meta, providers } = payload;
  const editable = isSupervisor();

  const providerLabel = {
    active: "Active", configured: "Configured", needs_config: "Needs credentials", not_installed: "Not installed",
  };

  const policySlider = (key, label, desc, min, max, step, format) => {
    const val = settings[key];
    return `<div class="setting-row">
      <div class="setting-top"><label for="s-${key}">${esc(label)}</label><span class="value" id="v-${key}">${esc(format(val))}</span></div>
      <p class="setting-desc">${esc(desc)}</p>
      <input type="range" id="s-${key}" min="${min}" max="${max}" step="${step}" value="${val}" data-setting="${key}" ${editable ? "" : "disabled"}>
    </div>`;
  };

  const toggle = (key, label, desc) => `<div class="setting-row">
    <div class="setting-top"><label>${esc(label)}</label><button class="toggle ${settings[key] ? "on" : ""}" data-toggle="${key}" aria-label="${esc(label)}" ${editable ? "" : "disabled"}></button></div>
    <p class="setting-desc">${esc(desc)}</p>
  </div>`;

  setView(`
    <div class="page-head">
      <div>
        <div class="eyebrow">Workspace</div>
        <h1>Settings</h1>
        <p class="lede">Review policy, routing, providers and language coverage. Changes are recorded in the audit log.</p>
      </div>
      <div class="page-head-actions">
        <span class="pill ${editable ? "pill-green" : "pill-slate"}">${editable ? "You can edit policy" : "Read-only"}</span>
        ${editable ? `<button class="btn btn-primary" data-save>${icon("save", "icon-sm")} Save changes</button>` : ""}
      </div>
    </div>

    <div class="settings-grid">
      <section class="card settings-card">
        <div class="eyebrow">Review policy</div>
        <h2 style="margin-top:5px">Confidence & escalation</h2>
        <p class="desc">The thresholds that decide what touches a human and what goes straight through.</p>
        <div style="margin-top:8px">
          ${policySlider("auto_approve_threshold", "Auto-approval threshold", "Documents with every field at or above this confidence, with no blocking validation errors, bypass review.", 0.7, 0.99, 0.01, (v) => Math.round(v * 100) + "%")}
          ${policySlider("review_threshold", "Low-confidence floor", "Fields below this score are surfaced first and highlighted on the scan.", 0.3, 0.95, 0.01, (v) => Math.round(v * 100) + "%")}
          ${policySlider("high_value_threshold", "High-value threshold", "Claims, loans and invoices above this amount require a supervisor decision under four-eyes policy.", 10000, 5000000, 10000, (v) => "₹ " + new Intl.NumberFormat("en-IN").format(v))}
          ${policySlider("sla_hours", "Standard SLA", "Time from intake to a human decision for normal-priority work.", 1, 72, 1, (v) => v + " hours")}
          ${policySlider("urgent_sla_hours", "Urgent SLA", "Used for escalated and high-value documents.", 1, 24, 1, (v) => v + " hours")}
        </div>
      </section>

      <div style="display:grid;gap:14px;align-content:start">
        <section class="card settings-card">
          <div class="eyebrow">Routing</div>
          <h2 style="margin-top:5px">Assignment rules</h2>
          <p class="desc">Keep ownership explicit.</p>
          ${toggle("require_supervisor_high_value", "Supervisor for high-value decisions", "Reviewers cannot approve documents above the high-value threshold; a supervisor must sign off.")}
          ${toggle("auto_assign", "Auto-assign new work", "Round-robin routing across available reviewers. Manual claim stays available.")}
        </section>

        <section class="card settings-card">
          <div class="eyebrow">Extraction providers</div>
          <h2 style="margin-top:5px">Model & OCR</h2>
          <p class="desc">A provider-agnostic pipeline. Swap the adapter without changing the review contract.</p>
          <div class="provider-list">
            ${providers.map((p) => `<div class="provider">
              <span class="p-icon">${icon(p.icon || "cloud")}</span>
              <div class="p-main"><strong>${esc(p.name)}</strong><span>${esc(p.kind)} · ${esc(p.detail)}</span></div>
              <span class="status ${p.status}">${providerLabel[p.status] || p.status}</span>
            </div>`).join("")}
          </div>
        </section>
      </div>
    </div>

    <div class="settings-grid" style="margin-top:14px">
      <section class="card settings-card">
        <div class="eyebrow">Validation</div>
        <h2 style="margin-top:5px">Deterministic checks</h2>
        <p class="desc">Validation is deliberately separate from the model. These are blocking unless marked otherwise.</p>
        <div class="rule-list">
          ${meta.validation_rules.map((r) => `<div class="rule">${icon("checkCircle")}<div><strong>${esc(r.label)} ${r.blocking ? "" : '<span class="pill pill-slate" style="font-size:8px">warning</span>'}</strong><span>${esc(r.detail)}</span></div></div>`).join("")}
        </div>
      </section>
      <section class="card settings-card">
        <div class="eyebrow">Coverage</div>
        <h2 style="margin-top:5px">Languages in the workspace</h2>
        <p class="desc">Script-aware extraction, right-to-left layouts and mixed-language fields.</p>
        <div class="language-grid">
          ${meta.languages.map((l) => `<div class="lang-pill"><strong>${esc(l.name)}</strong><span>${esc(l.script)}</span></div>`).join("")}
        </div>
        <div style="margin-top:18px;padding-top:14px;border-top:1px solid var(--line)">
          <div class="eyebrow">Workspace name</div>
          ${editable
            ? `<input class="input" id="workspace-name" value="${esc(settings.workspace_name || "")}" style="margin-top:8px" maxlength="80">`
            : `<p style="margin-top:6px;font-size:13px">${esc(settings.workspace_name || "—")}</p>`}
        </div>
      </section>
    </div>

    <section class="card settings-card" style="margin-top:14px">
      <div class="eyebrow">Demonstration</div>
      <h2 style="margin-top:5px">Workspace data</h2>
      <p class="desc">This prototype ships with 18 fictitious scans across six document families and six scripts.</p>
      <div style="display:flex;gap:12px;align-items:center;flex-wrap:wrap;margin-top:14px">
        <span class="pill pill-gold">18 specimens</span>
        <span class="pill pill-blue">6 document types</span>
        <span class="pill pill-green">All decisions audited</span>
        <span class="tiny faint">Akshara ${esc(meta.version)} · local SQLite · no cloud calls</span>
      </div>
      ${isAdmin() ? `<div class="danger-row" style="margin-top:16px">
        ${icon("alert")}
        <div class="d-main"><strong>Reset demo workspace</strong><span>Deletes local review progress and restores the seeded specimens.</span></div>
        <button class="btn btn-danger btn-sm" data-reset>Reset data</button>
      </div>` : ""}
      <div class="settings-actions">
        ${editable ? `<button class="btn" data-discard>Discard changes</button><button class="btn btn-primary" data-save>${icon("save", "icon-sm")} Save changes</button>` : `<span class="tiny faint">Ask a supervisor or administrator to change policy.</span>`}
      </div>
    </section>
  `, (root) => {
    const pending = {};

    root.querySelectorAll("[data-setting]").forEach((input) => {
      const key = input.dataset.setting;
      const out = root.querySelector("#v-" + key);
      const fmt = {
        auto_approve_threshold: (v) => Math.round(v * 100) + "%",
        review_threshold: (v) => Math.round(v * 100) + "%",
        high_value_threshold: (v) => "₹ " + new Intl.NumberFormat("en-IN").format(v),
        sla_hours: (v) => v + " hours",
        urgent_sla_hours: (v) => v + " hours",
      }[key] || ((v) => v);
      input.addEventListener("input", () => {
        out.textContent = fmt(Number(input.value));
      });
      input.addEventListener("change", () => { pending[key] = Number(input.value); });
    });

    root.querySelectorAll("[data-toggle]").forEach((btn) => {
      btn.addEventListener("click", () => {
        if (!editable) return;
        btn.classList.toggle("on");
        pending[btn.dataset.toggle] = btn.classList.contains("on");
      });
    });

    root.querySelectorAll("[data-save]").forEach((btn) => btn.addEventListener("click", async () => {
      const nameInput = root.querySelector("#workspace-name");
      if (nameInput) pending.workspace_name = nameInput.value.trim();
      if (!Object.keys(pending).length) {
        toast("No policy changes to save.", "info");
        return;
      }
      try {
        const res = await api.saveSettings(pending);
        state.settings = res.settings;
        toast("Settings saved. Policy applies to new intakes and routing decisions.", "success");
        // Re-render so values reflect the persisted state.
        renderSettings(view);
      } catch (e) {
        toast(e.message, "error");
      }
    }));

    root.querySelector("[data-discard]")?.addEventListener("click", () => renderSettings(view));
    root.querySelector("[data-reset]")?.addEventListener("click", () => {
      const ov = modal({
        title: "Reset the demo workspace?",
        subtitle: "This cannot be undone",
        iconName: "alert",
        body: `<p class="muted" style="font-size:12.5px;line-height:1.65">All corrections, approvals, rejections and comments will be replaced by the seeded demonstration state. The audit trail will be rebuilt.</p>`,
        footer: `<button class="btn" data-close>Cancel</button><button class="btn btn-danger" data-confirm>Reset everything</button>`,
      });
      ov.querySelector("[data-confirm]").addEventListener("click", async () => {
        try {
          await api.resetDemo();
          closeModal();
          toast("Demo workspace restored.", "success");
          setTimeout(() => location.reload(), 600);
        } catch (e) { toast(e.message, "error"); }
      });
    });
  });
}
