// ── VOLT starter — ACE-Step block ───────────────────────────────────────────
// NEW FILE at the repo root, next to start.js. Written in the same Pinokio
// script idiom as the other root scripts.
//
// To wire it in, add ONE step to start.js, right after the Stable Audio
// daemon block:
//
//     {
//       method: "script.start",
//       params: { uri: "start_acestep.js" }
//     },
//
// Graceful skip: every step is guarded by `when` on the staged launcher's
// folder, so on any machine where ACE-Step was never installed the whole
// block is skipped and the rest of the studio boots exactly as before —
// the same behaviour the plan requires of the Stable Audio block.
// ────────────────────────────────────────────────────────────────────────────

const ACESTEP_DIR = "app/omni-source/pinokio/api/ace-step-ui.pinokio";

module.exports = {
  run: [
    // Announce the skip honestly instead of failing the boot.
    {
      when: "{{!exists('" + ACESTEP_DIR + "')}}",
      method: "log",
      params: {
        raw: "[acestep] launcher not installed (" + ACESTEP_DIR + ") — skipping. " +
             "Run its install.js once to enable song generation.",
      },
    },
    // Start the staged launcher as a daemon: UI on 3000, its backend on
    // 3001, the engine API on its own port (see the launcher's start.js).
    {
      when: "{{exists('" + ACESTEP_DIR + "')}}",
      method: "script.start",
      params: {
        uri: ACESTEP_DIR + "/start.js",
        params: { daemon: true },
      },
    },
    // Publish the address the hub/front end should talk to. The hub reads
    // ACESTEP_API_BASE from the environment (default http://127.0.0.1:3001);
    // this local mirrors it for anything in the Pinokio layer that asks.
    {
      when: "{{exists('" + ACESTEP_DIR + "')}}",
      method: "local.set",
      params: { acestep_url: "http://127.0.0.1:3001" },
    },
  ],
};
