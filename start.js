module.exports = {
  daemon: true,
  run: [
    {
      method: "shell.run",
      params: {
        env: {
          SA3_LOCAL_MODELS_DIR: "{{path.resolve(cwd, 'models')}}",
          SA3_LOCAL_ONLY: "1",
          PYTHONPATH: "{{cwd}}"
        },
        path: "app/stabledaw",
        venv: "env",
        message: [
          "python -m uvicorn backend.server:app --host 127.0.0.1 --port 8600"
        ],
        on: [{
          event: "/(http:\\/\\/\\S+)/",
          done: true
        }]
      }
    },
    {
      method: "shell.run",
      params: {
        env: {},
        path: "app/stabledaw/frontend",
        message: [
          "npx vite --host 127.0.0.1"
        ],
        on: [{
          event: "/(http:\\/\\/\\S+)/",
          done: true
        }]
      }
    },
    {
      method: "local.set",
      params: {
        stabledaw_url: "{{input.event[1]}}"
      }
    },
    {
      method: "shell.run",
      params: {
        venv: "env",
        path: "app/dashboard",
        message: [
          "python omni.py"
        ],
        on: [{
          event: "/(http:\\/\\/\\S+)/",
          done: true
        }]
      }
    },
    {
      method: "local.set",
      params: {
        url: "{{input.event[1]}}"
      }
    },
    {
      method: "shell.run",
      params: {
        path: "app/volt-dashboard",
        message: [
          "npm run dev"
        ],
        on: [{
          event: "/(http:\\/\\/\\S+)/",
          done: true
        }]
      }
    },
    {
      method: "local.set",
      params: {
        frontend_url: "{{input.event[1]}}"
      }
    },
    {
      method: "shell.run",
      params: {
        venv: "env",
        env: {
          GRADIO_SERVER_NAME: "127.0.0.1",
          HF_TOKEN: "{{envs.HF_TOKEN}}"
        },
        path: "app/stable-audio-3",
        message: [
          "(python run_gradio.py --model small-music --title 'Stable Audio 3 Small Music' || echo 'stable-audio-3 requires HuggingFace auth - skipped')"
        ],
        on: [{
          event: "/(http:\\/\\/\\S+)/",
          done: true
        }, {
          event: "/stable-audio-3 requires/",
          done: true
        }]
      }
    },
    {
      method: "local.set",
      params: {
        stable_audio_url: "{{input.event[1] || ''}}"
      }
    },
    {
      method: "shell.run",
      params: {
        message: ["tail -f /dev/null"],
        on: [{
          event: "/.*/",
          done: true
        }]
      }
    }
  ]
}
