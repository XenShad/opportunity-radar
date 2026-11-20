// utils.js - small helpers used by the other files.
// Nothing here touches the page directly; it's all plain functions.

// ---------------------------------------------------------------------------
// localStorage (wrapped in try/catch: private windows can block it)
// ---------------------------------------------------------------------------
const PREFIX = "radar.";

export function load(key, fallback) {
  try {
    const raw = localStorage.getItem(PREFIX + key);
    return raw === null ? fallback : JSON.parse(raw);
  } catch {
    return fallback;
  }
}

export function save(key, value) {
  try {
    localStorage.setItem(PREFIX + key, JSON.stringify(value));
  } catch {
    /* storage full or blocked: the page still works, it just won't remember */
  }
}

// ---------------------------------------------------------------------------
// Dates. All dates in the data are "YYYY-MM-DD" strings (no time).
// ---------------------------------------------------------------------------
const DAY_MS = 24 * 60 * 60 * 1000;

/** Today's date as "YYYY-MM-DD" in the viewer's own timezone. */
export function todayISO() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

/** Whole days from today until the given "YYYY-MM-DD" (negative = in the past). */
export function daysUntil(iso) {
  if (!iso) return null;
  const [y, m, d] = iso.split("-").map(Number);
  const [ty, tm, td] = todayISO().split("-").map(Number);
  return Math.round((Date.UTC(y, m - 1, d) - Date.UTC(ty, tm - 1, td)) / DAY_MS);
}

/** "2026-11-30" -> "30 Nov" (adds the year if it isn't this year). */
export function shortDate(iso) {
  if (!iso) return "";
  const [y, m, d] = iso.split("-").map(Number);
  const date = new Date(Date.UTC(y, m - 1, d));
  const opts = { day: "numeric", month: "short", timeZone: "UTC" };
  if (y !== new Date().getFullYear()) opts.year = "numeric";
  return date.toLocaleDateString("en-GB", opts);
}

/** "2026-11-20T09:00:00+00:00" -> "3 hours ago" */
export function timeAgo(isoDateTime) {
  const seconds = (Date.now() - new Date(isoDateTime).getTime()) / 1000;
  if (!isFinite(seconds)) return "unknown";
  if (seconds < 90) return "just now";
  const minutes = seconds / 60;
  if (minutes < 60) return `${Math.round(minutes)} min ago`;
  const hours = minutes / 60;
  if (hours < 36) return `${Math.round(hours)} h ago`;
  return `${Math.round(hours / 24)} days ago`;
}

/** Has this opportunity closed? (deadline passed, or ended with no deadline) */
export function isExpired(item) {
  if (item.deadline) return daysUntil(item.deadline) < 0;
  if (item.end_date) return daysUntil(item.end_date) < 0;
  return false;
}

/**
 * What the coloured pill on each card says.
 * Returns { text, tone } where tone is "red" | "amber" | "green" | "expected" | "".
 * Red under 7 days, amber under 30, as requested.
 */
export function countdown(item) {
  if (item.deadline) {
    const days = daysUntil(item.deadline);
    const tone = days < 7 ? "red" : days < 30 ? "amber" : "";
    if (days === 0) return { text: "Closes today", tone };
    if (days === 1) return { text: "1 day left", tone };
    return { text: `${days} days left · ${shortDate(item.deadline)}`, tone };
  }
  if (item.expected) return { text: "Dates expected", tone: "expected" };
  const startsIn = daysUntil(item.start_date);
  if (startsIn !== null && startsIn > 0) return { text: `Starts in ${startsIn} days`, tone: "" };
  if (item.end_date) return { text: `Ongoing · until ${shortDate(item.end_date)}`, tone: "green" };
  return { text: "Rolling", tone: "" };
}

/**
 * Date used for "soonest first" sorting:
 * deadline, else a future start date, else the end date (ongoing things you
 * can still join), else far in the future (undated items go last).
 */
export function sortDate(item) {
  if (item.deadline) return item.deadline;
  if (item.start_date && item.start_date >= todayISO()) return item.start_date;
  return item.end_date || "9999-12-31";
}

// ---------------------------------------------------------------------------
// Text
// ---------------------------------------------------------------------------
/** Make text safe to put inside HTML (stops "<script>" in data from running). */
export function escapeHTML(text) {
  return String(text ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[c]);
}

/** Only allow http(s) links, so a bad entry can't sneak in "javascript:" URLs. */
export function safeURL(url) {
  try {
    const u = new URL(url);
    return u.protocol === "http:" || u.protocol === "https:" ? u.href : "#";
  } catch {
    return "#";
  }
}

/** "drug-discovery" -> "Drug discovery", "ml-ai" -> "ML / AI" */
const SPECIAL_LABELS = { "ml-ai": "ML / AI", "healthcare-ai": "Healthcare AI", "summer-school": "Summer school", "multi-omics": "Multi-omics", "single-cell": "Single-cell" };
export function label(slug) {
  if (SPECIAL_LABELS[slug]) return SPECIAL_LABELS[slug];
  const words = String(slug).replace(/-/g, " ");
  return words.charAt(0).toUpperCase() + words.slice(1);
}

/** "Ecology & Evolution" -> "ecology-evolution" (format used for field tags) */
export function slugify(text) {
  return String(text).toLowerCase().trim().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
}

/** Does a stipend/prize text describe actual money or perks? */
export function hasStipend(text) {
  const t = String(text || "").trim().toLowerCase();
  if (!t) return false;
  return !/^(none|n\/?a|nil|unpaid|no stipend|knowledge|kudos|swag|-)$/.test(t);
}

/** Wait until the user stops typing before running fn. */
export function debounce(fn, ms = 150) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), ms);
  };
}

/** Google Calendar "add event" link for the deadline (an all-day event). */
export function calendarURL(item) {
  if (!item.deadline) return null;
  const start = item.deadline.replace(/-/g, "");
  const [y, m, d] = item.deadline.split("-").map(Number);
  const next = new Date(Date.UTC(y, m - 1, d + 1)).toISOString().slice(0, 10).replace(/-/g, "");
  const lines = [
    item.organiser && `Organiser: ${item.organiser}`,
    item.stipend_or_prize && `Stipend/prize: ${item.stipend_or_prize}`,
    item.eligibility && `Eligibility: ${item.eligibility}`,
    item.url,
  ].filter(Boolean);                       // drop the empty ones
  const details = lines.join("\n") + "\n\nAdded from Opportunity Radar";
  const params = new URLSearchParams({
    action: "TEMPLATE",
    text: `Deadline: ${item.title}`,
    dates: `${start}/${next}`,
    details,
  });
  return `https://calendar.google.com/calendar/render?${params}`;
}
