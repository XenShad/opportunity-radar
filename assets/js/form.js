// form.js - the "Add opportunity" dialog, validation, and Export JSON.
//
// app.js calls initForm(...) once, passing in functions so this file never
// reaches into app.js's state directly:
//   getFields()      -> list of field slugs to offer as chips
//   getLocalItems()  -> the items saved in this browser
//   onSave(item)     -> called with a finished item (new or edited)
//   toast(message)   -> show a short message

import { escapeHTML, label, slugify } from "./utils.js";

const TYPES = ["hackathon", "internship", "fellowship", "competition", "conference", "workshop", "webinar", "summer-school"];

let deps;                 // the functions passed to initForm
let editingId = null;     // id of the item being edited, or null when adding
let editingAdded = null;  // its original date_added (kept when editing)
let chosenFields = new Set();

const $ = (id) => document.getElementById(id);

export function initForm(dependencies) {
  deps = dependencies;
  const form = $("addForm");

  form.elements.type.innerHTML = TYPES.map((t) => `<option value="${t}">${label(t)}</option>`).join("");

  // Close buttons (the X and Cancel) in both dialogs
  document.querySelectorAll("dialog [data-close]").forEach((btn) =>
    btn.addEventListener("click", () => btn.closest("dialog").close())
  );
  // Clicking the dark area outside a dialog closes it
  document.querySelectorAll("dialog").forEach((dialog) =>
    dialog.addEventListener("click", (e) => { if (e.target === dialog) dialog.close(); })
  );

  $("formFieldChips").addEventListener("click", (e) => {
    const chip = e.target.closest(".chip");
    if (!chip) return;
    const field = chip.dataset.value;
    chosenFields.has(field) ? chosenFields.delete(field) : chosenFields.add(field);
    chip.setAttribute("aria-pressed", chosenFields.has(field));
  });

  // Ticking "expected" means there's no deadline yet
  form.elements.expected.addEventListener("change", (e) => {
    form.elements.deadline.disabled = e.target.checked;
    if (e.target.checked) form.elements.deadline.value = "";
  });

  form.addEventListener("submit", (e) => {
    e.preventDefault();
    const item = readForm();
    if (!item) return;                   // validation failed; errors are shown
    deps.onSave(item);
    $("addDialog").close();
    deps.toast(editingId ? "Changes saved" : "Saved to My additions");
  });

  $("exportBtn").addEventListener("click", openExport);
  $("copyBtn").addEventListener("click", copyExport);
  $("downloadBtn").addEventListener("click", downloadExport);
}

/** Open the dialog. Pass an item to edit it, or nothing to add a new one. */
export function openForm(item = null) {
  const form = $("addForm");
  form.reset();
  clearErrors();
  editingId = item ? item.id : null;
  editingAdded = item ? item.date_added : null;
  chosenFields = new Set(item ? item.fields : []);
  $("addTitle").textContent = item ? "Edit opportunity" : "Add opportunity";
  $("saveBtn").textContent = item ? "Save changes" : "Save";

  if (item) {
    for (const name of ["title", "organiser", "url", "type", "mode", "location", "region",
                        "start_date", "end_date", "deadline", "stipend_or_prize", "eligibility", "notes"]) {
      form.elements[name].value = item[name] || "";
    }
    form.elements.expected.checked = Boolean(item.expected);
  }
  form.elements.deadline.disabled = form.elements.expected.checked;

  $("formFieldChips").innerHTML = deps.getFields()
    .map((f) => `<button type="button" class="chip" data-value="${escapeHTML(f)}" aria-pressed="${chosenFields.has(f)}">${escapeHTML(label(f))}</button>`)
    .join("");

  $("addDialog").showModal();
  form.elements.title.focus();
}

// ---------------------------------------------------------------------------
// Validation
// ---------------------------------------------------------------------------
function clearErrors() {
  const form = $("addForm");
  form.querySelectorAll("[aria-invalid]").forEach((el) => el.removeAttribute("aria-invalid"));
  form.querySelectorAll(".field-err").forEach((el) => el.remove());
  $("formError").hidden = true;
}

function fieldError(input, message) {
  input.setAttribute("aria-invalid", "true");
  const note = document.createElement("span");
  note.className = "field-err";
  note.textContent = message;
  input.insertAdjacentElement("afterend", note);
}

/** Read and check the form. Returns an item, or null if something is wrong. */
function readForm() {
  clearErrors();
  const f = $("addForm").elements;
  const v = (name) => f[name].value.trim();
  let ok = true;

  if (v("title").length < 3) { fieldError(f.title, "Please enter a title (at least 3 characters)."); ok = false; }

  let url = v("url");
  if (url && !/^https?:\/\//i.test(url)) url = "https://" + url;   // forgive a missing https://
  try {
    if (!url) throw new Error();
    new URL(url);
  } catch {
    fieldError(f.url, "Please enter a valid link, e.g. https://example.org");
    ok = false;
  }

  if (!TYPES.includes(v("type"))) { fieldError(f.type, "Pick a type."); ok = false; }
  if (v("start_date") && v("end_date") && v("end_date") < v("start_date")) {
    fieldError(f.end_date, "End date is before the start date."); ok = false;
  }
  if (v("deadline") && v("end_date") && v("deadline") > v("end_date")) {
    fieldError(f.deadline, "Deadline is after the end date. Is that right?"); ok = false;
  }

  if (!ok) {
    $("formError").textContent = "Please fix the highlighted fields.";
    $("formError").hidden = false;
    $("addForm").querySelector("[aria-invalid]")?.focus();
    return null;
  }

  const mode = v("mode");
  const location = v("location") || (mode === "online" ? "Online" : "");
  const item = {
    id: editingId || `local-${Date.now().toString(36)}`,
    title: v("title"),
    organiser: v("organiser"),
    type: v("type"),
    fields: [...chosenFields],
    mode,
    location,
    region: v("region") || guessRegion(location, mode),
    start_date: v("start_date") || null,
    end_date: v("end_date") || null,
    deadline: f.expected.checked ? null : v("deadline") || null,
    stipend_or_prize: v("stipend_or_prize"),
    eligibility: v("eligibility"),
    url,
    source: "local",
    date_added: editingAdded || new Date().toISOString().slice(0, 10),
    verified: true,                       // your own entry
    notes: v("notes"),
  };
  if (f.expected.checked) item.expected = true;
  return item;
}

export function guessRegion(location, mode) {
  if (/\bindia\b|pune|mumbai|delhi|bengaluru|bangalore|hyderabad|chennai|kolkata|ahmedabad|iit|iisc|iiser/i.test(location)) return "India";
  return mode === "online" ? "Online" : "International";
}

// ---------------------------------------------------------------------------
// Export JSON
// ---------------------------------------------------------------------------
/** Local items reshaped for custom.json (ids become "custom-...", no "source"). */
function exportableItems() {
  return deps.getLocalItems().map((item) => {
    const { source, verified, ...rest } = item;    // custom.json doesn't need these
    return { ...rest, id: `custom-${slugify(item.title)}` };
  });
}

function openExport() {
  const items = exportableItems();
  const text = $("exportText");
  if (items.length === 0) {
    $("exportHint").textContent = "You haven't added anything in this browser yet. Save an opportunity first, then export it here.";
    text.value = "";
    $("copyBtn").disabled = $("downloadBtn").disabled = true;
  } else {
    $("exportHint").innerHTML =
      `${items.length} item${items.length > 1 ? "s" : ""}. Open <code>data/custom.json</code>, put a comma after the last entry in <code>"items": [ … ]</code>, paste this after it, and commit. Once they show up on the site you can delete them here.`;
    // Objects separated by commas, without the outer [ ], ready to paste into the list.
    text.value = items.map((i) => JSON.stringify(i, null, 2)).join(",\n");
    $("copyBtn").disabled = $("downloadBtn").disabled = false;
  }
  $("exportDialog").showModal();
}

async function copyExport() {
  const text = $("exportText");
  try {
    await navigator.clipboard.writeText(text.value);
  } catch {
    text.select();                              // fallback for older browsers
    document.execCommand("copy");
  }
  deps.toast("Copied. Paste it into data/custom.json");
}

function downloadExport() {
  const blob = new Blob([JSON.stringify(exportableItems(), null, 2) + "\n"], { type: "application/json" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = "my-opportunities.json";
  link.click();
  URL.revokeObjectURL(link.href);
}
