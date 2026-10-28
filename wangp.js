// WanGP (Wan2GP by DeepBeepMeep) — Omni Studio launcher
// Generative video / image / audio / TTS super-app, vendored at app/wangp.
// Runs wgp.py (Gradio) in its own venv at app/wangp/env — create that env with
// WanGP's own installer (app/wangp/scripts/install.sh) or:
//   python3.11 -m venv env && pip install torch + -r requirements.txt
// WanGP needs a GPU for real generation; on a GPU-less machine the UI still
// loads but generation will fail. Default Gradio port: 7860.
module.exports = {
  daemon: true,
  run: [
    {
      method: "shell.run",
      params: {
        venv: "env",
        path: "app/wangp",
        env: {},
        message: [
          "python wgp.py --server-name 127.0.0.1 --server-port 7860 --open-browser"
        ],
        on: [{
          event: "/(http:\\/\\/\\S+)/",
          done: true
        }]
      }
    }
  ]
}
