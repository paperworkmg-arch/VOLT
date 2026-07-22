module.exports = {
  title: "Windsurf",
  link: "https://windsurf.com/",
  icon: "windsurf.png",
  description: "The AI Code Editor",
  run: [{
    when: "{{which('windsurf')}}",
    method: "exec",
    params: {
      message: "windsurf .",
      path: "{{args.cwd}}"
    }
  }, {
    when: "{{!which('windsurf')}}",
    method: "notify",
    params: {
      html: "Windsurf is not installed. Click to visit the Windsurf homepage to download",
      href: "https://windsurf.com/",
      target: "_blank"
    }
  }]
}
