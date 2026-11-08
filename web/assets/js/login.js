import { api } from "./api.js";
import { loadSession } from "./store.js";
import { icon } from "./icons.js";
import { esc, qs } from "./utils.js";
import { toast } from "./components.js";

const DEMO = [
  { email: "maya@akshara.ai", name: "Maya Rao", role: "Reviewer", color: "#C77655", initials: "MR", note: "Review, correct, approve" },
  { email: "arjun@akshara.ai", name: "Arjun Mehta", role: "Supervisor", color: "#2B6E62", initials: "AM", note: "Override and escalate" },
  { email: "leela@akshara.ai", name: "Leela Nair", role: "Administrator", color: "#8A6F3D", initials: "LN", note: "Policy and workspace" },
];

export function renderLogin(onSuccess) {
  const app = qs("#app");
  app.innerHTML = `
  <div class="login-shell">
    <section class="login-art">
      <div class="login-brand">
        <span class="brand-mark">अ</span>
        <span><span class="brand-word">Akshara</span><span class="brand-tag">document intelligence</span></span>
      </div>

      <div class="login-hero">
        <div class="login-kicker"><span class="dot"></span> Human-in-the-loop document AI</div>
        <h1>Every script.<br>Every form.<br><em>Every decision.</em></h1>
        <p>Banks, insurers and service centres receive the world in a million layouts. Akshara reads regional scripts, mixed languages and imperfect scans — then makes confidence visible, so your team can decide what to trust.</p>
        <div class="script-strip">
          <span class="script-word">नमस्ते <small>Devanagari</small></span>
          <span class="script-word">வணக்கம் <small>Tamil</small></span>
          <span class="script-word">স্বাগতম <small>Bengali</small></span>
          <span class="script-word" dir="rtl">أهلاً <small>Arabic</small></span>
        </div>
        <div class="login-stats">
          <div class="login-stat"><strong>5</strong><span>writing systems</span></div>
          <div class="login-stat"><strong>18</strong><span>specimen scans</span></div>
          <div class="login-stat"><strong>100%</strong><span>decision audit</span></div>
        </div>
      </div>
      <div class="login-foot"><span>Built for regulated operations</span><span>Prototype · fictitious data</span></div>
    </section>

    <section class="login-panel">
      <div class="login-box">
        <div class="eyebrow">Operations workspace</div>
        <h2>Welcome back.</h2>
        <p class="lede">Sign in to the Meridian Bank review desk.</p>

        <form class="login-form" id="login-form" novalidate>
          <div>
            <label class="field-label-top" for="email">Work email</label>
            <div class="input-wrap">${icon("mail")}<input class="input" id="email" name="email" type="email" autocomplete="username" placeholder="you@akshara.ai" required></div>
          </div>
          <div>
            <label class="field-label-top" for="password">Password</label>
            <div class="input-wrap">${icon("lock")}<input class="input" id="password" name="password" type="password" autocomplete="current-password" placeholder="••••••••" required></div>
          </div>
          <div class="login-error" id="login-error"></div>
          <button class="btn btn-primary btn-block btn-lg" type="submit" id="login-submit">Sign in ${icon("arrowRight", "icon-sm")}</button>
        </form>

        <div class="login-divider">Or open a demo desk</div>
        <div class="demo-grid">
          ${DEMO.map((u) => `
            <button class="demo-account" data-demo="${esc(u.email)}">
              <span class="avatar" style="background:${u.color}">${u.initials}</span>
              <span class="who"><strong>${esc(u.name)}</strong><span>${esc(u.role)} · ${esc(u.note)}</span></span>
              ${icon("arrowUpRight")}
            </button>`).join("")}
        </div>
        <p class="login-note">This is a self-contained demonstration. All documents, people and balances are fictitious. The seeded passwords are <strong>review123</strong>, <strong>super123</strong> and <strong>admin123</strong>.</p>
      </div>
    </section>
  </div>`;

  const form = qs("#login-form");
  const err = qs("#login-error");
  const submit = qs("#login-submit");
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    err.classList.remove("show");
    submit.disabled = true;
    submit.innerHTML = "Signing in…";
    try {
      await api.login(qs("#email").value.trim(), qs("#password").value);
      await loadSession();
      await onSuccess();
    } catch (ex) {
      err.textContent = ex.message;
      err.classList.add("show");
      submit.disabled = false;
      submit.innerHTML = `Sign in ${icon("arrowRight", "icon-sm")}`;
    }
  });

  document.querySelectorAll("[data-demo]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      btn.disabled = true;
      try {
        await api.demoLogin(btn.dataset.demo);
        await loadSession();
        await onSuccess();
      } catch (ex) {
        toast(ex.message, "error");
        btn.disabled = false;
      }
    });
  });
}

