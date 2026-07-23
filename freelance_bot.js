#!/usr/bin/env node

/**
 * Freelance Bot Launcher
 * Monitors .pinokio-temp for new job postings and sends desktop notifications
 */

module.exports = {
  daemon: true,
  run: [
    // Run the freelance bot check
    {
      method: "shell.run",
      params: {
        path: "app/omni-source",
        message: [
          "python scripts/freelance_bot.py check"
        ],
        on: [{
          event: "/.*/",
          done: true
        }]
      }
    },
    // Run again in 10 minutes (daemon mode keeps this running)
    {
      method: "shell.run",
      params: {
        path: "app/omni-source",
        message: [
          "sleep 600 && python scripts/freelance_bot.py check"
        ],
        on: [{
          event: "/.*/",
          done: true
        }]
      }
    }
  ]
}
