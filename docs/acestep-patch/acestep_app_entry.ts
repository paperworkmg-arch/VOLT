// ── use-audio-apps.ts — ACE-Step entry ──────────────────────────────────────
// Paste this object into the audio-apps array in
//   app/volt-dashboard/src/hooks/use-audio-apps.ts
// alongside the StableDAW / Stable Audio 3 / TASCAR / WanGP entries.
// Field names mirror the plan's description of that list; if a sibling
// entry uses a different key for the same idea (e.g. `href` vs `url`),
// match the sibling — the values are what matter:
//
//   id      stable slug the rest of the UI keys off
//   port    the launcher UI (the generate panel below talks to the hub
//           on 8500, not to this port — the card is for launch/status)
//   kind    generation surface, so the card can badge it correctly
// ────────────────────────────────────────────────────────────────────────────

export const ACE_STEP_APP = {
  id: "ace-step",
  name: "ACE-Step 1.5",
  description: "Local text-to-song — full songs with vocals, offline, MIT weights",
  port: 3000,
  url: "http://127.0.0.1:3000",
  kind: "song-generation",
  // The hub health endpoint reports engine/comfyui/model in one call;
  // point the card's status probe here instead of the launcher port.
  healthUrl: "/api/acestep/health",
};
