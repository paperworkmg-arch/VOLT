module.exports = {
  run: [
    {
      method: "shell.run",
      params: {
        message: "git pull"
      }
    },
    {
      method: "shell.run",
      params: {
        path: "app/stable-audio-3",
        message: "git pull"
      }
    },
    {
      method: "shell.run",
      params: {
        path: "app/stabledaw",
        message: "git pull"
      }
    },
    {
      method: "shell.run",
      params: {
        path: "app/tascar",
        message: "git pull"
      }
    },
    {
      method: "shell.run",
      params: {
        venv: "env",
        path: "app/stable-audio-3",
        message: [
          "uv sync --extra ui --active"
        ]
      }
    },
    {
      when: "{{gpu === 'nvidia' && (platform === 'win32' || platform === 'linux')}}",
      method: "script.start",
      params: {
        uri: "torch.js",
        params: {
          venv: "env",
          path: "app/stable-audio-3",
          flashattention: true
        }
      }
    },
    {
      method: "shell.run",
      params: {
        path: "app/volt-dashboard",
        message: [
          "git pull",
          "npm ci",
          "npm run build"
        ]
      }
    },
    {
      method: "shell.run",
      params: {
        venv: "env",
        path: "app/dashboard",
        message: [
          "uv pip install -r requirements.txt"
        ]
      }
    }
  ]
}
