module.exports = {
  run: [
    {
      method: "shell.run",
      params: {
        message: [
          "echo 'Volt Records Catalog Intelligence'",
          "echo '===================================='",
          "echo ''",
          "echo '198 Analyzed Tracks'",
          "echo ''",
          "echo 'Key Metrics:'",
          "echo '- Average HPI: 8.34'",
          "echo '- Average BPM: 117.2'",
          "echo '- Bright/Aggressive: 106 tracks'",
          "echo '- Warm/Dark: 92 tracks'",
          "echo ''",
          "echo 'Top Keys: E, F#, C, F, D'",
          "echo ''",
          "echo 'Verdict Distribution:'",
          "echo '- Playlist Pitch: ~89 tracks'",
          "echo '- Acquisition: ~41 tracks'",
          "echo '- Licensing: ~11 tracks'"
        ],
        on: [{
          event: "/.*/",
          done: true
        }]
      }
    }
  ]
}
