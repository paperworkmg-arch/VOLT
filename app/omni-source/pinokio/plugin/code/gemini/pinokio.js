module.exports = {
  title: "Gemini CLI",
  icon: "gemini.jpeg",
  link: "https://github.com/google-gemini/gemini-cli",
  run: [{
    id: "run",
    method: "shell.run",
    params: {
      message: "npx -y @google/gemini-cli {{args.prompt ? '-i ' + JSON.stringify(args.prompt) : ''}} --include-directories {{kernel.path('prototype')}}",
      path: "{{args.cwd}}",
      buffer: 1024,
      input: true
    }
  }]
}
