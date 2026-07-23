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
          "uv run --no-sync uvicorn server_wrapper:app --host 127.0.0.1 --port 8600"
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
          "npx vite --host 127.0.0.1 --config ../../vite.launcher.config.mjs"
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
        env: {
          GRADIO_SERVER_NAME: "127.0.0.1"
        },
        path: "app/stable-audio-3",
        message: {
          _: [
            "python",
            "launch.py",
            "--model",
            "small-music",
            "--title",
            "Stable Audio 3 Small Music"
          ]
        },
        on: [{
          event: "/(http:\\/\\/\\S+)/",
          done: true
        }]
      }
    },
    {
      method: "local.set",
      params: {
        stable_audio_url: "{{input.event[1]}}"
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
    }
  ]
}