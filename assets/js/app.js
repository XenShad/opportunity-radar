// app.js - the main file: holds the page state, applies filters/sorting,
// and wires up every button. Read top to bottom:
//   1. constants & state   2. loading data   3. filtering & sorting
//   4. rendering           5. event handlers 6. start-up

import { countdown, daysUntil, debounce, hasStipend, isExpired, label, load, save, slugify, sortDate, timeAgo, escapeHTML, safeURL } from "./utils.js";
import { renderCard, renderEmpty, renderError, renderSkeletons, sourceName } from "./render.js";
import { guessRegion, initForm, openForm } from "./form.js";

// ---------------------------------------------------------------------------
// 1. Constants & state
// ---------------------------------------------------------------------------
const TYPES = ["hackathon", "internship", "fellowship", "competition", "conference", "workshop", "webinar", "summer-school"];
const MODES = ["online", "offline", "hybrid"];
const MODE_LABELS = { online: "Online", offline: "In person", hybrid: "Hybrid" };
const REGIONS = ["India", "International", "Online"];
const WITHIN_OPTIONS = [0, 7, 30, 90];          // 0 = any time
const CLOSING_SOON_DAYS = 14;                   // what the "Closing soon" tab means

const DEFAULT_FILTERS = { fields: [], types: [], modes: [], regions: [], within: 0, stipend: false, verified: false };

const state = {
  remote: [],                                   // from data/opportunities.json + data/custom.json
  local: load("localItems", []),                // added in this browser
  meta: {},
  filters: { ...DEFAULT_FILTERS, ...load("filters", {}) },
  sort: load("sort", "deadline"),
  tab: load("tab", "all"),
  search: "",
  bookmarks: new Set(load("bookmarks", [])),
  customFields: load("customFields", []),       // fields you added with "Add a field"
  loaded: false,
};

const $ = (id) => document.getElementById(id);

// ---------------------------------------------------------------------------
// 2. Loading data
// ---------------------------------------------------------------------------
async function fetchJSON(path) {
  const response = await fetch(path, { cache: "no-cache" });   // always check for a newer file
  if (!response.ok) throw new Error(`${path}: HTTP ${response.status}`);
  return response.json();
}

/** custom.json is also read directly, so edits show up even before the updater runs. */
function normaliseCustom(entry, existing) {
  const mode = MODES.includes(entry.mode) ? entry.mode : "offline";
  const location = entry.location || (mode === "online" ? "Online" : "");
  return {
    ...existing,
    ...entry,
    id: entry.id || `custom-${slugify(entry.title)}`,
    fields: entry.fields?.length ? entry.fields : existing?.fields || [],
    mode,
    location,
    region: entry.region || existing?.region || guessRegion(location, mode),
    source: "custom",
    verified: true,
  };
}

async function loadData() {
  state.loaded = false;
  $("grid").setAttribute("aria-busy", "true");
  $("grid").innerHTML = renderSkeletons();
  try {
    const [opportunities, custom] = await Promise.all([
      fetchJSON("data/opportunities.json"),
      fetchJSON("data/custom.json").catch(() => ({ items: [] })),   // optional
    ]);
    state.meta = opportunities.meta || {};
    const byId = new Map((opportunities.items || []).map((item) => [item.id, item]));
    for (const entry of custom.items || []) {
      if (!entry.title || !entry.url || !TYPES.includes(entry.type)) continue;
      const item = normaliseCustom(entry, byId.get(entry.id));
      byId.set(item.id, item);
    }
    state.remote = [...byId.values()];
    state.loaded = true;
  } catch (error) {
    console.error(error);
    $("grid").innerHTML = renderError(error.message);
    $("lastUpdated").textContent = "Couldn't load data";
    $("grid").setAttribute("aria-busy", "false");
    return;
  }
  $("grid").setAttribute("aria-busy", "false");
  renderSidebarExtras();
  renderAll();
}

// ---------------------------------------------------------------------------
// 3. Filtering & sorting
// ---------------------------------------------------------------------------
/** Every open opportunity (expired ones are hidden even if the data is a few hours old). */
function openItems() {
  return [...state.remote, ...state.local].filter((item) => !isExpired(item));
}

function filtersActive() {
  const f = state.filters;
  return Boolean(f.fields.length || f.types.length || f.modes.length || f.regions.length
    || f.within || f.stipend || f.verified || state.search);
}

function activeFilterCount() {
  const f = state.filters;
  return f.fields.length + f.types.length + f.modes.length + f.regions.length
    + (f.within ? 1 : 0) + (f.stipend ? 1 : 0) + (f.verified ? 1 : 0);
}

function matchesFilters(item) {
  const f = state.filters;
  if (f.fields.length && !f.fields.some((field) => item.fields?.includes(field))) return false;
  if (f.types.length && !f.types.includes(item.type)) return false;
  if (f.modes.length && !f.modes.includes(item.mode)) return false;
  if (f.regions.length && !f.regions.includes(item.region)) return false;
  if (f.within) {
    const days = daysUntil(item.deadline);
    if (days === null || days > f.within) return false;
  }
  if (f.stipend && !hasStipend(item.stipend_or_prize)) return false;
  if (f.verified && !item.verified) return false;
  return true;
}

/** Every word you type must appear somewhere in the item. */
function matchesSearch(item) {
  const words = state.search.toLowerCase().split(/\s+/).filter(Boolean);
  if (!words.length) return true;
  const haystack = [
    item.title, item.organiser, item.location, item.region, item.type, label(item.type),
    (item.fields || []).map(label).join(" "), item.eligibility, item.notes, item.stipend_or_prize,
    sourceName(item.source),
  ].join(" ").toLowerCase();
  return words.every((word) => haystack.includes(word));
}

function inTab(item, tab) {
  if (tab === "bookmarked") return state.bookmarks.has(item.id);
  if (tab === "closing") {
    const days = daysUntil(item.deadline);
    return days !== null && days <= CLOSING_SOON_DAYS;
  }
  if (tab === "mine") return item.source === "custom" || item.source === "local";
  return true;
}

const SORTERS = {
  deadline: (a, b) => sortDate(a).localeCompare(sortDate(b)) || a.title.localeCompare(b.title),
  added: (a, b) => (b.date_added || "").localeCompare(a.date_added || "") || SORTERS.deadline(a, b),
  start: (a, b) => (a.start_date || "9999").localeCompare(b.start_date || "9999") || SORTERS.deadline(a, b),
};

// ---------------------------------------------------------------------------
// 4. Rendering
// ---------------------------------------------------------------------------
function renderAll() {
  renderFilterControls();
  renderResults();
  renderHeader();
}

/** Field list: from the data + your own added fields. Your filters first, "general" last. */
function allFields() {
  const counts = fieldCounts();
  const fields = new Set([...(state.meta.fields || []), ...Object.keys(counts), ...state.customFields]);
  return [...fields].sort((a, b) =>
    (a === "general") - (b === "general") || (counts[b] || 0) - (counts[a] || 0) || a.localeCompare(b));
}

function fieldCounts() {
  const counts = {};
  for (const item of openItems()) for (const f of item.fields || []) counts[f] = (counts[f] || 0) + 1;
  return counts;
}

function chipHTML(group, value, text, pressed, extra = "") {
  return `<button type="button" class="chip" data-group="${group}" data-value="${escapeHTML(value)}" aria-pressed="${pressed}">${extra}${escapeHTML(text)}</button>`;
}

function renderFilterControls() {
  const f = state.filters;
  const counts = fieldCounts();
  $("fieldChips").innerHTML = allFields().map((field) => {
    const removable = state.customFields.includes(field)
      ? `<span class="x" data-remove-field="${escapeHTML(field)}" role="button" aria-label="Remove field ${escapeHTML(label(field))}">×</span>` : "";
    return chipHTML("fields", field, label(field), f.fields.includes(field))
      .replace("</button>", ` <span class="n">${counts[field] || 0}</span>${removable}</button>`);
  }).join("");

  $("typeChips").innerHTML = TYPES.map((t) =>
    chipHTML("types", t, label(t), f.types.includes(t), `<span class="dot" style="background: var(--t-${t})"></span>`)).join("");
  $("modeChips").innerHTML = MODES.map((m) => chipHTML("modes", m, MODE_LABELS[m], f.modes.includes(m))).join("");
  $("regionChips").innerHTML = REGIONS.map((r) => chipHTML("regions", r, r, f.regions.includes(r))).join("");
  $("withinSeg").innerHTML = WITHIN_OPTIONS.map((d) =>
    `<button type="button" role="radio" data-within="${d}" aria-checked="${f.within === d}">${d ? `${d}d` : "Any"}</button>`).join("");
  $("stipendOnly").checked = f.stipend;
  $("verifiedOnly").checked = f.verified;
  $("sort").value = state.sort;

  const n = activeFilterCount();
  $("filterCount").hidden = n === 0;
  $("filterCount").textContent = n;
}

function renderResults() {
  const base = openItems().filter((item) => matchesFilters(item) && matchesSearch(item));

  // tab buttons + counts
  document.querySelectorAll("#tabs [data-tab]").forEach((btn) => {
    const tab = btn.dataset.tab;
    btn.setAttribute("aria-selected", tab === state.tab);
    btn.tabIndex = tab === state.tab ? 0 : -1;
    btn.querySelector(".tab-count").textContent = base.filter((item) => inTab(item, tab)).length;
  });

  const shown = base.filter((item) => inTab(item, state.tab)).sort(SORTERS[state.sort] || SORTERS.deadline);
  const selectedFields = new Set(state.filters.fields);
  const firstImport = state.remote.reduce((min, i) => (i.date_added && i.date_added < min ? i.date_added : min), "9999");

  if (!state.loaded) return;
  if (shown.length === 0) {
    const kind = state.tab === "all" ? "filtered" : state.tab;
    $("grid").innerHTML = renderEmpty(kind, filtersActive());
    $("resultLine").textContent = "";
    return;
  }
  $("grid").innerHTML = shown
    .map((item) => renderCard(item, { bookmarked: state.bookmarks.has(item.id), selectedFields, firstImport }))
    .join("");

  const urgent = shown.filter((item) => countdown(item).tone === "red").length;
  $("resultLine").textContent = `Showing ${shown.length} of ${openItems().length}`
    + (urgent ? ` · ${urgent} closing within a week` : "")
    + (filtersActive() ? " · filters on" : "");
}

function renderHeader() {
  const total = openItems().length;
  $("openCount").textContent = `${total} open`;
  const updated = state.meta.last_updated;
  const el = $("lastUpdated");
  if (updated) {
    const hours = (Date.now() - new Date(updated)) / 36e5;
    el.textContent = `Updated ${timeAgo(updated)}`;
    el.title = `Data last refreshed ${new Date(updated).toLocaleString()}`;
    el.classList.toggle("stale", hours > 24);
    if (hours > 24) el.title += ". The automatic updater may be paused: check the Actions tab on GitHub.";
  } else {
    el.textContent = "Not updated yet";
  }
}

function renderSidebarExtras() {
  $("manualList").innerHTML = (state.meta.manual_sources || []).map((s) =>
    `<li><a href="${escapeHTML(safeURL(s.url))}" target="_blank" rel="noopener noreferrer">${escapeHTML(s.name)}</a><small>${escapeHTML(s.why || "")}</small></li>`
  ).join("") || "<li>None listed</li>";

  $("sourceList").innerHTML = Object.entries(state.meta.sources || {}).map(([name, s]) => {
    const text = s.status === "ok" ? `${s.count} items` : s.status;
    return `<li title="${escapeHTML(s.message || "")}"><span>${escapeHTML(sourceName(name))}</span><span class="st st-${escapeHTML(s.status)}">${escapeHTML(text)}</span></li>`;
  }).join("") || "<li>No run yet</li>";
}

let toastTimer;
function toast(message) {
  const el = $("toast");
  el.textContent = message;
  el.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { el.hidden = true; }, 2200);
}

// ---------------------------------------------------------------------------
// 5. Event handlers
// ---------------------------------------------------------------------------
function saveFilters() {
  save("filters", state.filters);
  renderAll();
}

function resetFilters() {
  state.filters = { ...DEFAULT_FILTERS };
  state.search = "";
  $("search").value = "";
  saveFilters();
}

function setTab(tab) {
  state.tab = tab;
  save("tab", tab);
  renderResults();
}

function toggleInList(list, value) {
  const i = list.indexOf(value);
  i === -1 ? list.push(value) : list.splice(i, 1);
}

function toggleBookmark(id) {
  if (state.bookmarks.has(id)) {
    state.bookmarks.delete(id);
    toast("Bookmark removed");
  } else {
    state.bookmarks.add(id);
    toast("Bookmarked");
  }
  save("bookmarks", [...state.bookmarks]);
  renderResults();
}

function saveLocalItem(item) {
  const i = state.local.findIndex((x) => x.id === item.id);
  i === -1 ? state.local.push(item) : (state.local[i] = item);
  for (const field of item.fields) {           // remember any new field you used
    if (!allFields().includes(field)) state.customFields.push(field);
  }
  save("localItems", state.local);
  save("customFields", state.customFields);
  renderAll();
}

function deleteLocalItem(id) {
  const item = state.local.find((x) => x.id === id);
  if (!item || !confirm(`Delete "${item.title}" from this browser?`)) return;
  state.local = state.local.filter((x) => x.id !== id);
  save("localItems", state.local);
  renderAll();
  toast("Deleted");
}

function openSidebar(open) {
  $("sidebar").classList.toggle("open", open);
  $("backdrop").hidden = !open;
  $("filtersToggle").setAttribute("aria-expanded", open);
}

function effectiveTheme() {
  const chosen = document.documentElement.dataset.theme;
  if (chosen) return chosen;
  return matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

function bindEvents() {
  $("search").addEventListener("input", debounce((e) => {
    state.search = e.target.value.trim();
    renderResults();
  }));
  // Press "/" anywhere to jump to search
  document.addEventListener("keydown", (e) => {
    const typing = /INPUT|TEXTAREA|SELECT/.test(document.activeElement.tagName);
    if (e.key === "/" && !typing && !document.querySelector("dialog[open]")) {
      e.preventDefault();
      $("search").focus();
    }
    if (e.key === "Escape" && $("sidebar").classList.contains("open")) openSidebar(false);
  });

  // Filter chips (field, type, mode, region) - one listener for the whole sidebar
  $("sidebar").addEventListener("click", (e) => {
    const remove = e.target.closest("[data-remove-field]");
    if (remove) {
      const field = remove.dataset.removeField;
      state.customFields = state.customFields.filter((x) => x !== field);
      state.filters.fields = state.filters.fields.filter((x) => x !== field);
      save("customFields", state.customFields);
      saveFilters();
      return;
    }
    const chip = e.target.closest(".chip[data-group]");
    if (chip) {
      toggleInList(state.filters[chip.dataset.group], chip.dataset.value);
      saveFilters();
      return;
    }
    const within = e.target.closest("[data-within]");
    if (within) {
      state.filters.within = Number(within.dataset.within);
      saveFilters();
    }
  });
  $("stipendOnly").addEventListener("change", (e) => { state.filters.stipend = e.target.checked; saveFilters(); });
  $("verifiedOnly").addEventListener("change", (e) => { state.filters.verified = e.target.checked; saveFilters(); });
  $("resetFilters").addEventListener("click", resetFilters);

  $("addFieldForm").addEventListener("submit", (e) => {
    e.preventDefault();
    const field = slugify($("newField").value);
    if (!field) return;
    if (!allFields().includes(field)) state.customFields.push(field);
    if (!state.filters.fields.includes(field)) state.filters.fields.push(field);
    save("customFields", state.customFields);
    $("newField").value = "";
    saveFilters();
    toast(`Added field "${label(field)}". Tag items with it in Add opportunity or custom.json`);
  });

  // Tabs (click, plus arrow keys for keyboard users)
  $("tabs").addEventListener("click", (e) => {
    const btn = e.target.closest("[data-tab]");
    if (btn) setTab(btn.dataset.tab);
  });
  $("tabs").addEventListener("keydown", (e) => {
    if (e.key !== "ArrowRight" && e.key !== "ArrowLeft") return;
    const tabs = [...document.querySelectorAll("#tabs [data-tab]")];
    const i = tabs.findIndex((t) => t.dataset.tab === state.tab);
    const next = tabs[(i + (e.key === "ArrowRight" ? 1 : tabs.length - 1)) % tabs.length];
    setTab(next.dataset.tab);
    next.focus();
  });

  $("sort").addEventListener("change", (e) => {
    state.sort = e.target.value;
    save("sort", state.sort);
    renderResults();
  });

  // Card buttons and empty-state buttons - one listener for the whole grid
  $("grid").addEventListener("click", (e) => {
    const btn = e.target.closest("[data-action]");
    if (!btn) return;
    const id = btn.closest(".card")?.dataset.id;
    const action = btn.dataset.action;
    if (action === "bookmark") toggleBookmark(id);
    else if (action === "edit") openForm(state.local.find((x) => x.id === id));
    else if (action === "delete") deleteLocalItem(id);
    else if (action === "reset") resetFilters();
    else if (action === "tab") setTab(btn.dataset.tab);
    else if (action === "add") openForm();
    else if (action === "retry") loadData();
  });

  $("addBtn").addEventListener("click", () => openForm());

  $("themeToggle").addEventListener("click", () => {
    const next = effectiveTheme() === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    // Stored as plain text (not JSON) because the tiny script in index.html's
    // <head> reads it before anything else loads, to avoid a white flash.
    try { localStorage.setItem("radar.theme", next); } catch { /* not saved, still works */ }
  });

  $("filtersToggle").addEventListener("click", () => openSidebar(true));
  $("sidebarClose").addEventListener("click", () => openSidebar(false));
  $("backdrop").addEventListener("click", () => openSidebar(false));
}

// ---------------------------------------------------------------------------
// 6. Start-up
// ---------------------------------------------------------------------------
initForm({
  getFields: allFields,
  getLocalItems: () => state.local,
  onSave: saveLocalItem,
  toast,
});
bindEvents();
renderFilterControls();
loadData();

// Re-check countdowns if the tab stays open past midnight, and refresh the
// data when you come back to a tab that has been open for a while.
let lastLoad = Date.now();
document.addEventListener("visibilitychange", () => {
  if (document.visibilityState === "visible" && Date.now() - lastLoad > 30 * 60 * 1000) {
    lastLoad = Date.now();
    loadData();
  }
});
