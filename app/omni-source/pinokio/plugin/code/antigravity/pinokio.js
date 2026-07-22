module.exports = {
  title: "Antigravity",
  link: "https://antigravity.google/",
  icon: "antigravity.png",
  description: "The AI IDE from Google",
  run: [{
    when: "{{which('antigravity')}}",
    method: "exec",
    params: {
      message: "antigravity .",
      path: "{{args.cwd}}",
    }
  }, {
    when: "{{!which('antigravity')}}",
    method: "notify",
    params: {
      html: "Antigravity is not installed. Click to visit the Google Antigravity homepage to download",
      href: "https://antigravity.google/download",
      target: "_blank"
    }
  }]
}
