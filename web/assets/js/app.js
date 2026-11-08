import { loadSession } from "./store.js";
import { parseHash, qs, esc } from "./utils.js";
import { mountShell, setTopbar, closeModal } from "./components.js";
import { renderLogin } from "./login.js";
import { renderDashboard } from "./views/dashboard.js";
import { renderQueue, renderDocuments } from "./views/queue.js";
import { renderReview } from "./views/review.js";
import { renderAnalytics } from "./views/analytics.js";
import { renderAudit } from "./views/audit.js";
import { renderSettings } from "./views/settings.js";

const ROUTES = {
  overview: { nav: "overview", title: "Command centre", crumbs: "Operations / Overview", view: renderDashboard },
  queue: { nav: "queue", title: "Human review", crumbs: "Operations / Review queue", view: renderQueue },
  documents: { nav: "documents", title: "Intake ledger", crumbs: "Operations / Documents", view: renderDocuments },
  analytics: { nav: "analytics", title: "Measurement", crumbs: "Operations / Analytics", view: renderAnalytics },
  audit: { nav: "audit", title: "Attribution", crumbs: "Operations / Audit log", view: renderAudit },
  settings: { nav: "settings", title: "Workspace", crumbs: "Operations / Settings", view: renderSettings },
};

let shellReady = false;
let rendering = false;

function setActiveNav(id) {
  document.querySelectorAll(".nav-item").forEach((a) => {
    a.classList.toggle("active", a.getAttribute("href") === `#/${id}`);
  });
}

function setDocumentTitle(title) {
  document.title = `${title} · Akshara`;
}

async function route() {
  if (!shellReady || rendering) return;
  rendering = true;
  try {
    if (typeof window.__akCleanup === "function") {
      window.__akCleanup();
      window.__akCleanup = null;
    }
    const parsed = parseHash();
    const name = parsed.name || "overview";
    const view = qs("#view");
    if (!view) return;

    if (name === "review" && parsed.id) {
      setActiveNav("queue");
      setTopbar(`Operations<span class="sep">/</span><a href="#/queue">Review queue</a><span class="sep">/</span><strong>${esc(parsed.id.replace("doc_", "").toUpperCase())}</strong>`, "Review workspace");
      setDocumentTitle("Review");
      view.className = "view flush";
      await renderReview(view, parsed);
      return;
    }

    const config = ROUTES[name] || ROUTES.overview;
    setActiveNav(config.nav);
    setTopbar(config.crumbs, config.title);
    setDocumentTitle(config.title);
    view.className = "view";
    await config.view(view, parsed);
  } catch (e) {
    console.error(e);
  } finally {
    rendering = false;
  }
}

async function boot() {
  try {
    await loadSession();
  } catch (e) {
    renderLogin(authenticated);
    return;
  }
  mount();
}

function mount() {
  mountShell("overview");
  shellReady = true;
  route();
}

async function authenticated() {
  try {
    await loadSession();
    mount();
  } catch (e) {
    renderLogin(authenticated);
  }
}

window.addEventListener("hashchange", () => {
  if (shellReady) route();
});

window.addEventListener("akshara:unauthorized", () => {
  if (!shellReady) return;
  shellReady = false;
  closeModal();
  renderLogin(authenticated);
});

window.addEventListener("akshara:logout", () => {
  shellReady = false;
  closeModal();
  renderLogin(authenticated);
});

boot();
