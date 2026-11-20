// render.js - turns data into HTML strings: cards, skeletons, empty states.
// Every piece of text from the data goes through escapeHTML() first.

import { calendarURL, countdown, daysUntil, escapeHTML, label, safeURL, shortDate } from "./utils.js";

// Small inline icons (no icon font, no external requests).
const ICONS = {
  pin: '<svg viewBox="0 0 24 24"><path d="M12 21s-7-6.2-7-11.5A7 7 0 0 1 19 9.5C19 14.8 12 21 12 21z"/><circle cx="12" cy="9.5" r="2.5"/></svg>',
  globe: '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18"/></svg>',
  coin: '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><path d="M15 9.5c-.5-1-1.6-1.5-3-1.5-1.7 0-3 .8-3 2s1.3 1.7 3 2 3 .8 3 2-1.3 2-3 2c-1.4 0-2.5-.5-3-1.5M12 6.5V8M12 16v1.5"/></svg>',
  people: '<svg viewBox="0 0 24 24"><circle cx="9" cy="8" r="3.5"/><path d="M2.5 20a6.5 6.5 0 0 1 13 0M16 4.5a3.5 3.5 0 0 1 0 7M18 14a6 6 0 0 1 3.5 6"/></svg>',
  calendar: '<svg viewBox="0 0 24 24"><rect x="3.5" y="5" width="17" height="15.5" rx="2.5"/><path d="M3.5 10h17M8 3v4M16 3v4"/></svg>',
  info: '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 7.5v.5"/></svg>',
  star: '<svg viewBox="0 0 24 24"><path d="m12 3.5 2.6 5.3 5.9.9-4.2 4.1 1 5.8L12 16.9l-5.3 2.7 1-5.8-4.2-4.1 5.9-.9z"/></svg>',
  external: '<svg viewBox="0 0 24 24"><path d="M14 4h6v6M20 4l-9 9M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5"/></svg>',
  check: '<svg viewBox="0 0 24 24" class="verified" aria-label="Verified source"><path d="M12 2.5 14.4 4.6 17.6 4.4 18.3 7.5 21 9.3 19.8 12.3 21 15.3 18.3 17.1 17.6 20.2 14.4 20 12 22.1 9.6 20 6.4 20.2 5.7 17.1 3 15.3 4.2 12.3 3 9.3 5.7 7.5 6.4 4.4 9.6 4.6Z"/><path d="m8.5 12.3 2.4 2.4 4.6-4.9"/></svg>',
};

const SOURCE_NAMES = {
  mlh: "MLH", unstop: "Unstop", hackerearth: "HackerEarth", devfolio: "Devfolio",
  kaggle: "Kaggle", dream: "DREAM", embl_ebi: "EMBL-EBI", tess: "TeSS",
  biotecnika: "Biotecnika", galaxy: "Galaxy", nfcore: "nf-core", ncbi: "NCBI",
  custom: "your list", local: "this browser",
};
const MODE_NAMES = { online: "Online", offline: "In person", hybrid: "Hybrid" };
const NEW_DAYS = 3;   // "New" badge for items first seen in the last 3 days

export function sourceName(source) {
  return SOURCE_NAMES[source] || source;
}

/**
 * One opportunity card.
 * ctx = { bookmarked: boolean, selectedFields: Set, firstImport: "YYYY-MM-DD" }
 * firstImport is the earliest date_added in the data: everything imported on
 * the very first run would otherwise all show "New".
 */
export function renderCard(item, ctx) {
  const cd = countdown(item);
  const url = safeURL(item.url);
  const cal = calendarURL(item);
  const isMine = item.source === "custom" || item.source === "local";
  const isNew = !isMine && item.date_added && item.date_added > (ctx.firstImport || "")
    && daysUntil(item.date_added) > -NEW_DAYS;
  const type = escapeHTML(item.type);

  const where = item.mode === "online" && (!item.location || item.location === "Online")
    ? "Online"
    : `${MODE_NAMES[item.mode] || ""} · ${item.location || "location on event page"}`;

  let dates = "";
  if (item.start_date && item.end_date && item.start_date !== item.end_date) dates = `${shortDate(item.start_date)} – ${shortDate(item.end_date)}`;
  else if (item.start_date) dates = `Starts ${shortDate(item.start_date)}`;
  else if (item.end_date) dates = `Until ${shortDate(item.end_date)}`;

  const facts = [
    `<li>${item.mode === "online" ? ICONS.globe : ICONS.pin}<span>${escapeHTML(where)}</span></li>`,
    item.stipend_or_prize && `<li>${ICONS.coin}<span class="prize">${escapeHTML(item.stipend_or_prize)}</span></li>`,
    dates && `<li>${ICONS.calendar}<span>${escapeHTML(dates)}</span></li>`,
    item.eligibility && `<li>${ICONS.people}<span>${escapeHTML(item.eligibility)}</span></li>`,
    item.notes && `<li>${ICONS.info}<span>${escapeHTML(item.notes)}</span></li>`,
  ].filter(Boolean).join("");

  const tags = (item.fields || [])
    .map((f) => `<span class="tag${ctx.selectedFields.has(f) ? " hit" : ""}">${escapeHTML(label(f))}</span>`)
    .join("");

  const calendarButton = cal
    ? `<a class="btn" href="${escapeHTML(cal)}" target="_blank" rel="noopener noreferrer" title="Add the deadline to Google Calendar">${ICONS.calendar}Calendar</a>`
    : `<button class="btn" disabled title="No deadline announced yet">${ICONS.calendar}Calendar</button>`;

  return `
  <article class="card" style="--tc: var(--t-${type}, var(--accent))" data-id="${escapeHTML(item.id)}">
    <div class="card-top">
      <span><span class="type-badge">${escapeHTML(label(item.type))}</span>${isNew ? '<span class="new-badge">New</span>' : ""}</span>
      <span class="countdown ${cd.tone}" ${item.deadline ? `title="Deadline: ${escapeHTML(item.deadline)}"` : ""}>${escapeHTML(cd.text)}</span>
    </div>
    <h3><a href="${escapeHTML(url)}" target="_blank" rel="noopener noreferrer">${escapeHTML(item.title)}</a></h3>
    <div class="org" title="${escapeHTML(item.organiser || "")}">${item.verified ? ICONS.check : ""}${item.organiser
      ? `${escapeHTML(item.organiser)} <span class="src">· via ${escapeHTML(sourceName(item.source))}</span>`
      : `<span class="src">via ${escapeHTML(sourceName(item.source))}</span>`}</div>
    ${tags ? `<div class="tags">${tags}</div>` : ""}
    <ul class="facts">${facts}</ul>
    ${item.source === "local" ? `
    <div class="local-actions">
      <button class="link-btn" data-action="edit">Edit</button>
      <button class="link-btn" data-action="delete">Delete</button>
    </div>` : ""}
    <div class="card-actions">
      <a class="btn btn-primary open" href="${escapeHTML(url)}" target="_blank" rel="noopener noreferrer">Open link ${ICONS.external}</a>
      <button class="btn icon-only bookmark" data-action="bookmark" aria-pressed="${ctx.bookmarked}"
        aria-label="${ctx.bookmarked ? "Remove bookmark" : "Bookmark"}" title="${ctx.bookmarked ? "Remove bookmark" : "Bookmark"}">${ICONS.star}</button>
      ${calendarButton}
    </div>
  </article>`;
}

/** Grey placeholder cards shown while the data loads. */
export function renderSkeletons(count = 6) {
  const one = `
  <div class="card skeleton" aria-hidden="true">
    <div class="card-top"><div class="bar" style="width:90px;height:20px"></div><div class="bar" style="width:110px;height:20px"></div></div>
    <div class="bar" style="width:85%;height:16px"></div>
    <div class="bar" style="width:55%"></div>
    <div style="display:flex;gap:6px"><div class="bar" style="width:70px"></div><div class="bar" style="width:90px"></div></div>
    <div class="bar" style="width:70%"></div>
    <div class="bar" style="width:100%;height:32px;margin-top:8px"></div>
  </div>`;
  return one.repeat(count);
}

const RADAR_ART = `
<svg class="illus" viewBox="0 0 120 120" aria-hidden="true">
  <circle cx="60" cy="60" r="50" opacity=".35"/><circle cx="60" cy="60" r="34" opacity=".5"/>
  <circle cx="60" cy="60" r="18" opacity=".7"/><path d="M60 60 96 26" stroke-width="2.4"/>
  <path d="M60 10v100M10 60h100" opacity=".18"/>
  <circle cx="84" cy="38" r="3.5" fill="currentColor" stroke="none" opacity=".9"/>
  <circle cx="38" cy="78" r="2.5" fill="currentColor" stroke="none" opacity=".35"/>
</svg>`;

const STAR_ART = `
<svg class="illus" viewBox="0 0 120 120" aria-hidden="true">
  <circle cx="60" cy="60" r="50" opacity=".25"/>
  <path d="m60 28 9.4 19 21 3.1-15.2 14.8 3.6 20.9L60 75.9l-18.8 9.9 3.6-20.9L29.6 50.1l21-3.1z" stroke-width="2.2"/>
</svg>`;

const EMPTY_STATES = {
  filtered: {
    art: RADAR_ART, title: "Nothing on the radar",
    text: "No opportunities match these filters. Try removing one or two, or clearing the search.",
    button: '<button class="btn btn-primary" data-action="reset">Reset filters</button>',
  },
  bookmarked: {
    art: STAR_ART, title: "No bookmarks yet",
    text: "Tap the star on any card to keep it here. Bookmarks are saved in this browser.",
    button: '<button class="btn" data-action="tab" data-tab="all">Browse all</button>',
  },
  closing: {
    art: RADAR_ART, title: "Nothing closes in the next 14 days",
    text: "No deadlines are this close right now. Plan ahead from the full list.",
    button: '<button class="btn" data-action="tab" data-tab="all">See everything</button>',
  },
  mine: {
    art: RADAR_ART, title: "Your own finds go here",
    text: "Add opportunities you spot elsewhere. They're saved in this browser, and Export JSON lets you copy them into data/custom.json.",
    button: '<button class="btn btn-primary" data-action="add">Add opportunity</button>',
  },
};

/** Friendly empty state. kind = "filtered" | "bookmarked" | "closing" | "mine" */
export function renderEmpty(kind, filtersActive) {
  const s = { ...EMPTY_STATES[kind] };
  let extra = "";
  // If filters might be hiding things in this tab, offer to reset them instead.
  if (filtersActive && kind !== "filtered") {
    s.button = EMPTY_STATES.filtered.button;
    extra = "<p>Some filters or a search are on, which may be hiding items.</p>";
  }
  return `<div class="state">${s.art}<h2>${s.title}</h2><p>${s.text}</p>${extra}${s.button}</div>`;
}

/** Shown when the JSON file can't be loaded. */
export function renderError(message) {
  const fileProtocol = location.protocol === "file:";
  return `
  <div class="state">
    ${RADAR_ART}
    <h2>Couldn't load the opportunities</h2>
    <p>${fileProtocol
      ? "Browsers block loading data from a page opened as a file. In the project folder run <code>python -m http.server 8000</code> and open <code>http://localhost:8000</code>."
      : escapeHTML(message)}</p>
    <button class="btn btn-primary" data-action="retry">Try again</button>
  </div>`;
}
