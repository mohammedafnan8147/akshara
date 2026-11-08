import { api, setCsrf } from "./api.js";

export const state = {
  user: null,
  settings: {},
  meta: {},
  counts: {},
  csrf: null,
};

export function applySession(data) {
  state.user = data.user;
  state.settings = data.settings || {};
  state.meta = data.meta || {};
  state.counts = data.counts || {};
  state.csrf = data.csrf || data.user?.csrf || null;
  setCsrf(state.csrf);
  return state;
}

export async function loadSession() {
  const data = await api.session();
  return applySession(data);
}

export function isSupervisor() {
  return state.user?.role === "supervisor" || state.user?.role === "admin";
}

export function isAdmin() {
  return state.user?.role === "admin";
}

export function roleLabel() {
  return { reviewer: "Reviewer", supervisor: "Supervisor", admin: "Administrator" }[state.user?.role] || "Reviewer";
}

export function updateCounts(counts) {
  if (counts) state.counts = counts;
}
