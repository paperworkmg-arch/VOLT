module.exports = {
  title: "VS Code",
  link: "https://code.visualstudio.com/",
  icon: "vscode.png",
  description: "The AI Code Editor",
  run: [{
    when: "{{which('code')}}",
    method: "exec",
    params: {
      message: "code .",
      path: "{{args.cwd}}",
    }
  }, {
    when: "{{!which('code')}}",
    method: "notify",
    params: {
      html: "Visual Studio Code is not installed. Click to visit the Visual Studio Code homepage to download",
      href: "https://code.visualstudio.com/",
      target: "_blank"
    }
  }]
}
