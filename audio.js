module.exports = {
  daemon: true,
  run: [
    {
      method: "shell.run",
      params: {
        message: [
          "echo 'Omni Studio Audio Production Center'",
          "echo '====================================='",
          "echo ''",
          "echo 'Integrated Audio Applications:'",
          "echo '1. StableDAW - AI Audio DAW'",
          "echo '2. Stable Audio 3 - Text-to-Audio'",
          "echo '3. TASCAR - Spatial Audio Rendering'",
          "echo ''",
          "echo 'Checking application status...'   "
        ],
        on: [{
          event: "/.*/",
          done: true
        }]
      }
    },
    {
      method: "shell.run",
      params: {
        message: [
          "cd ../stabledaw.pinokio.git && pterm status"
        ],
        on: [{
          event: "/.*/",
          done: true
        }]
      }
    },
    {
      method: "shell.run",
      params: {
        message: [
          "cd ../stable-audio-3-small.pinokio.git && pterm status"
        ],
        on: [{
          event: "/.*/",
          done: true
        }]
      }
    },
    {
      method: "shell.run",
      params: {
        message: [
          "cd ../tascar && pterm status"
        ],
        on: [{
          event: "/.*/",
          done: true
        }]
      }
    }
  ]
}
