const path = require('path')

module.exports = {
  version: "7.0",
  title: "Omni Studio",
  description: "Unified audio AI studio — StableDAW + Stable Audio 3 + TASCAR + Catalog Intelligence. https://github.com/Stability-AI/stable-audio-3 / https://github.com/gantasmo/stabledaw",
  icon: "icon.png",
  menu: async (kernel) => {
    let installing = await kernel.running(__dirname, "install.js")
    let installed = await kernel.exists(__dirname, "app", "dashboard", "venv")
    let running = await kernel.running(__dirname, "start.js")

    if (installing) {
      return [{
        default: true,
        icon: "fa-solid fa-plug",
        text: "Installing",
        href: "install.js"
      }]
    } else if (running) {
      let local = kernel.memory.local[path.resolve(__dirname, "start.js")]
      if (local && local.url) {
        return [{
          default: true,
          icon: "fa-solid fa-rocket",
          text: "Open Web UI",
          href: local.url
        }, {
          icon: "fa-solid fa-terminal",
          text: "Terminal",
          href: "start.js"
        }]
      } else {
        return [{
          default: true,
          icon: "fa-solid fa-terminal",
          text: "Terminal",
          href: "start.js"
        }]
      }
    } else if (installed) {
      return [{
        default: true,
        icon: "fa-solid fa-power-off",
        text: "Start",
        href: "start.js"
      }, {
        icon: "fa-solid fa-plug",
        text: "Update",
        href: "update.js"
      }, {
        icon: "fa-solid fa-plug",
        text: "Install",
        href: "install.js"
      }, {
        icon: "fa-solid fa-file-zipper",
        text: "<div><strong>Save Disk Space</strong><div>Deduplicates redundant library files</div></div>",
        href: "link.js"
      }, {
        icon: "fa-solid fa-bell",
        text: "<div><strong>Approval Monitor</strong><div>Auto-check pending approvals</div></div>",
        href: "approval_monitor.js"
      }, {
        icon: "fa-solid fa-briefcase",
        text: "<div><strong>Freelance Bot</strong><div>Monitor job postings</div></div>",
        href: "freelance_bot.js"
      }, {
        icon: "fa-regular fa-circle-xmark",
        text: "Reset",
        href: "reset.js",
        confirm: "Are you sure you wish to reset the app?"
      }]
    } else {
      return [{
        default: true,
        icon: "fa-solid fa-plug",
        text: "Install",
        href: "install.js"
      }]
    }
  }
}
