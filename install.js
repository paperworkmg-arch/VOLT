module.exports = {
  requires: {
    bundle: "ai"
  },
  run: [
    {
      when: "{{!exists('app/stable-audio-3')}}",
      method: "shell.run",
      params: {
        message: "git clone https://github.com/Stability-AI/stable-audio-3.git app/stable-audio-3"
      }
    },
    {
      when: "{{!exists('app/stabledaw')}}",
      method: "shell.run",
      params: {
        message: "git clone https://github.com/gantasmo/stabledaw.git app/stabledaw"
      }
    },
    {
      when: "{{!exists('app/tascar')}}",
      method: "shell.run",
      params: {
        message: "git clone https://github.com/gisogrimm/tascar.git app/tascar"
      }
    },
    {
      method: "shell.run",
      params: {
        venv: "env",
        path: "app",
        message: [
          "uv pip install -r requirements.txt"
        ]
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
      when: "{{!exists('app/volt-dashboard/node_modules')}}",
      method: "shell.run",
      params: {
        path: "app/volt-dashboard",
        message: [
          "npm ci"
        ]
      }
    },
    {
      method: "shell.run",
      params: {
        path: "app/volt-dashboard",
        message: [
          "npm run build"
        ]
      }
    },
    {
      method: "notify",
      params: {
        html: "Install complete. Click Start to launch Omni Studio."
      }
    }
  ]
}
