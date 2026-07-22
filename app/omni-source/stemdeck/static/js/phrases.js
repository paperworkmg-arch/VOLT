// Playful labels rotated by job.js every ROTATION_MS while a job is in
// progress. Keyed by Job.status values from the backend. The progress
// bar carries the real percentage; this is purely UI personality.
//
// Edit freely — additions/removals don't require any code changes.

export const stagePhrases = {
  queued: [
    "Lacing up…",
    "Tuning forks…",
    "Spinning up…",
    "Warming the tubes…",
  ],
  // Downloading is load-in: gear arriving, getting set up, before the
  // sound check starts.
  downloading: [
    "Load-in…",
    "Rolling in flight cases…",
    "Setting up the kit…",
    "Snaking the cables…",
    "Plugging into the patch bay…",
  ],
  // Separating is the long stage — keep the user company with band /
  // sound-check vignettes. Short observational sentences, the kind of
  // thing you'd overhear at a rehearsal.
  separating: [
    "Tuning the bass…",
    "Guitarist checking himself in the mirror…",
    "Pick fell on the floor…",
    "In-ear check…",
    "Mic check, one two…",
    "\"More me in the monitor\"…",
    "Drummer adjusting the snare…",
    "Singer warming up… lalala",
    "Capo on, capo off…",
    "Tightening the lugs…",
    "Tuning the floor tom…",
    "Coiling a cable…",
    "Bassist plugged in backwards…",
    "Pedalboard wiggling…",
    "Tech swapping a 9V battery…",
    "Roadie taping down the setlist…",
    "\"Is this thing on?\"…",
    "Stepping on a fuzz pedal…",
    "Tuning the high E…",
    "Drummer twirling sticks…",
    "Singer sipping tea…",
    "Quick bathroom break…",
    "\"Can I get more vocals?\"…",
    "Snare too snappy…",
    "Levels look good…",
  ],
  default: ["Working on it…"],
};
