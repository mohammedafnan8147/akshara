import { api } from "./api.js";
import { icon, docIcon } from "./icons.js";
import { state, loadSession } from "./store.js";
import { toast, modal, closeModal, refreshSidebarCounts } from "./components.js";
import { esc, navigate, qualityLabel, confBar } from "./utils.js";

let cache = null;

const DOC_FILTERS = [
  { id: "all", label: "All specimens" },
  { id: "bank", label: "Banking" },
  { id: "claim", label: "Insurance" },
  { id: "service", label: "Service" },
  { id: "loan", label: "Lending" },
  { id: "invoice", label: "Business" },
  { id: "kyc", label: "KYC" },
];

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

export async function openIntake() {
  const ocrMeta = state.meta.ocr || {};
  const ocrReady = Boolean(ocrMeta.available);
  const pdfReady = Boolean(state.meta.pdf?.available);
  let items = cache;
  if (!items) {
    try {
      items = (await api.samples()).items;
      cache = items;
    } catch (e) {
      toast(e.message, "error");
      return;
    }
  }
  let tab = "library";
  let filter = "all";
  let selectedFile = null;

  const filtered = () => filter === "all" ? items : items.filter((s) => s.kind === filter);

  const card = (s) => `<button class="specimen-card" data-sample="${esc(s.id)}">
    <span class="specimen-thumb"><img src="/samples/${esc(s.thumb)}" alt="" loading="lazy"><span class="specimen-type">${icon(docIcon[s.kind] || "fileText", "icon-sm")} ${esc(s.doc_type_label)}</span></span>
    <span class="specimen-body">
      <span class="specimen-ref">${esc(s.ref)} · ${esc(s.language_name)} · ${esc(s.script)}</span>
      <strong>${esc(s.customer_name)}</strong>
      <span class="specimen-foot">${confBar(s.confidence)}<span class="pill ${s.quality === "poor" ? "pill-red" : s.quality === "fair" ? "pill-amber" : "pill-green"}">${esc(qualityLabel(s.quality))}</span></span>
    </span>
  </button>`;

  const body = `
    <div class="intake-tabs">
      <button class="${tab === "library" ? "active" : ""}" data-intake-tab="library">${icon("layers", "icon-sm")} Specimen library</button>
      <button class="${tab === "upload" ? "active" : ""}" data-intake-tab="upload">${icon("upload", "icon-sm")} Upload a scan</button>
    </div>
    <div id="intake-library">
      <p class="modal-note" style="margin:2px 0 12px">Every specimen is a rendered scan with an OCR-style error map. Pick one to watch the pipeline and land in human review.</p>
      <div class="intake-filters">
        ${DOC_FILTERS.map((f) => `<button class="filter-tab ${filter === f.id ? "active" : ""}" data-intake-filter="${f.id}">${f.label}<span class="n">${f.id === "all" ? items.length : items.filter((s) => s.kind === f.id).length}</span></button>`).join("")}
      </div>
      <div class="specimen-grid" id="specimen-grid">${filtered().map(card).join("")}</div>
    </div>
    <div id="intake-upload" hidden>
      <p class="modal-note" style="margin:2px 0 12px">${ocrReady
        ? `Local OCR is active — <strong>${esc(ocrMeta.version || "Tesseract")}</strong>, languages: ${esc((ocrMeta.languages || []).join(", ") || "eng")}. Upload a PNG/JPEG${pdfReady ? " or a multi-page PDF" : ""} and Akshara will read it on this machine${pdfReady ? "; PDFs are rasterised locally, up to 6 pages" : ""}. Imperfect fields are routed to review with source boxes.`
        : "No local OCR engine is installed. Uploads become a manual-indexing task — the same review experience, with fields blank and ready to key."}</p>
      <label class="dropzone" id="dropzone">
        <input type="file" accept="image/png,image/jpeg,application/pdf,.pdf" id="file-input" hidden>
        <span class="drop-icon">${icon("upload", "icon-lg")}</span>
        <strong>Drop a scanned form here</strong>
        <span>or click to choose a PNG / JPEG${pdfReady ? " / PDF" : ""} · max 15 MB</span>
        <span class="drop-file" id="drop-file"></span>
      </label>
      <div class="intake-upload-row">
        <div>
          <label class="field-label-top" for="upload-type">Document type</label>
          <select class="select" id="upload-type">
            ${(state.meta.doc_types || []).map((t) => `<option value="${esc(t.id)}">${esc(t.label)}</option>`).join("")}
          </select>
        </div>
        <button class="btn btn-primary" id="upload-submit" disabled>${icon("scan", "icon-sm")} ${ocrReady ? "Run local OCR" : "Start manual indexing"}</button>
      </div>
    </div>`;

  const overlay = modal({
    title: "New intake",
    subtitle: "Bring a document into the review desk",
    iconName: "upload",
    size: "modal-lg",
    body,
    footer: `<button class="btn" data-close>Cancel</button><span class="modal-note" style="margin-left:auto">All scanned data stays local.</span>`,
    onMount: (ov) => bind(ov),
  });

  function bind(ov) {
    const library = ov.querySelector("#intake-library");
    const upload = ov.querySelector("#intake-upload");
    ov.querySelectorAll("[data-intake-tab]").forEach((btn) => btn.addEventListener("click", () => {
      tab = btn.dataset.intakeTab;
      ov.querySelectorAll("[data-intake-tab]").forEach((b) => b.classList.toggle("active", b === btn));
      library.hidden = tab !== "library";
      upload.hidden = tab !== "upload";
    }));
    ov.querySelectorAll("[data-intake-filter]").forEach((btn) => btn.addEventListener("click", () => {
      filter = btn.dataset.intakeFilter;
      ov.querySelectorAll("[data-intake-filter]").forEach((b) => b.classList.toggle("active", b === btn));
      const grid = ov.querySelector("#specimen-grid");
      grid.innerHTML = filtered().map(card).join("");
      bindCards(grid);
    }));
    bindCards(ov.querySelector("#specimen-grid"));

    const fileInput = ov.querySelector("#file-input");
    const drop = ov.querySelector("#dropzone");
    const fileLabel = ov.querySelector("#drop-file");
    const submit = ov.querySelector("#upload-submit");
    const type = ov.querySelector("#upload-type");

    const setFile = (file) => {
      if (!file) return;
      const isImage = file.type.match(/image\/(png|jpeg)/) || /\.(png|jpe?g)$/i.test(file.name);
      const isPdf = file.type === "application/pdf" || /\.pdf$/i.test(file.name);
      if (isPdf && (!pdfReady || !ocrReady)) { toast("PDF uploads need both local PDF rendering and OCR; upload an image instead.", "error"); return; }
      if (!isImage && !isPdf) { toast("Upload a PNG, JPEG or PDF scan.", "error"); return; }
      if (file.size > 15 * 1024 * 1024) { toast("That file is larger than 15 MB.", "error"); return; }
      selectedFile = file;
      fileLabel.textContent = `${file.name} · ${(file.size / 1024 / 1024).toFixed(1)} MB${isPdf ? " · PDF" : ""}`;
      submit.disabled = false;
    };
    fileInput.addEventListener("change", () => setFile(fileInput.files[0]));
    ["dragenter", "dragover"].forEach((ev) => drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.add("drag"); }));
    ["dragleave", "drop"].forEach((ev) => drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.remove("drag"); }));
    drop.addEventListener("drop", (e) => setFile(e.dataTransfer.files[0]));

    submit.addEventListener("click", async () => {
      if (!selectedFile) return;
      const file = selectedFile;
      closeModal();
      const steps = ocrReady
        ? ["Secure upload", "Tesseract OCR", "Label extraction", "Confidence check", "Route to review"]
        : ["Secure upload", "Image checks", "Document classification", "Manual indexing route"];
      const pipe = pipeline(ocrReady ? "Reading the scan locally" : "Preparing a manual index", steps);
      try {
        const [res] = await Promise.all([
          api.intakeUpload(file, type.value, "en"),
          sleep(ocrReady ? 2200 : 1000),
        ]);
        pipe.done();
        await afterIntake(res);
      } catch (e) {
        pipe.fail(e.message);
      }
    });
  }

  function bindCards(grid) {
    grid.querySelectorAll("[data-sample]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const sample = items.find((s) => s.id === btn.dataset.sample);
        closeModal();
        const pipe = pipeline(`Reading ${sample.customer_name}`, [
          "Secure intake", "Deskew & denoise", "Script detection", "Field extraction", "Confidence calibration", "Policy routing",
        ]);
        try {
          const [res] = await Promise.all([
            api.intakeDemo(sample.id),
            sleep(2100),
          ]);
          pipe.done();
          await afterIntake(res, sample);
        } catch (e) {
          pipe.fail(e.message);
        }
      });
    });
  }

  function pipeline(title, steps) {
    const body = `<div class="pipeline">
      <div class="pipeline-head">
        <span class="pipeline-spinner"></span>
        <div><strong>${esc(title)}</strong><p>Running the extraction and calibration pipeline…</p></div>
      </div>
      <div class="pipeline-steps">
        ${steps.map((s, i) => `<div class="pipeline-step" data-step="${i}">
          <span class="step-dot">${i}</span><span>${esc(s)}</span><span class="step-status">Waiting</span>
        </div>`).join("")}
      </div>
      <div class="pipeline-track"><span id="pipeline-fill"></span></div>
      <p class="modal-note" id="pipeline-note">This runs locally against the bundled specimen adapter.</p>
    </div>`;
    const ov = modal({ title: "Processing scan", subtitle: "Extraction → calibration → routing", iconName: "scan", body, closeOnBackdrop: false });
    ov.querySelector(".modal-close").style.display = "none";
    let current = 0;
    const timer = setInterval(() => {
      const row = ov.querySelector(`[data-step="${current}"]`);
      if (row) {
        row.classList.add("done");
        row.querySelector(".step-dot").innerHTML = "✓";
        row.querySelector(".step-status").textContent = "Done";
        current = Math.min(steps.length, current + 1);
        const fill = ov.querySelector("#pipeline-fill");
        if (fill) fill.style.width = `${Math.round(100 * current / steps.length)}%`;
        const next = ov.querySelector(`[data-step="${current}"]`);
        if (next) { next.classList.add("active"); next.querySelector(".step-status").textContent = "Running"; }
      }
    }, 300);
    return {
      done: () => {
        clearInterval(timer);
        ov.querySelectorAll(".pipeline-step").forEach((r) => { r.classList.add("done"); r.querySelector(".step-dot").innerHTML = "✓"; r.querySelector(".step-status").textContent = "Done"; });
        const fill = ov.querySelector("#pipeline-fill");
        if (fill) fill.style.width = "100%";
      },
      fail: (msg) => {
        clearInterval(timer);
        const note = ov.querySelector("#pipeline-note");
        if (note) { note.style.color = "var(--red)"; note.textContent = msg; }
        ov.querySelector(".pipeline-spinner")?.classList.add("stopped");
        const close = ov.querySelector(".modal-close");
        if (close) close.style.display = "";
      },
    };
  }

  async function afterIntake(res, sample = null) {
    try {
      await loadSession();
      refreshSidebarCounts();
    } catch {}
    closeModal();
    if (sample) {
      toast(`${sample.ref} processed · ${res.status === "auto_approved" ? "straight through" : "routed to review"}.`, "success");
    } else if (res.ocr) {
      const pages = res.pages > 1 ? ` · ${res.pages} pages` : "";
      toast(`Local OCR read ${res.ocr.extracted}/${res.ocr.total} fields${pages} · ${Math.round((res.ocr.mean_confidence || 0) * 100)}% mean confidence. Review required.`, "success", 6000);
    } else {
      toast(res.ocr_error ? `OCR unavailable: ${res.ocr_error} Manual index created.` : "Manual indexing task created.", "info", 6000);
    }
    navigate(`/review/${res.id}`);
  }
}
