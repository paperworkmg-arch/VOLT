#!/usr/bin/env node

/**
 * Approval Monitor Launcher
 * Runs periodic checks and sends desktop notifications for pending approvals
 */

module.exports = {
  daemon: true,
  run: [
    // Run the approval monitor
    {
      method: "shell.run",
      params: {
        path: "app/omni-source",
        message: [
          "python scripts/approval_monitor.py"
        ],
        on: [{
          event: "/.*/",
          done: true
        }]
      }
    },
    // Run again in 5 minutes (daemon mode keeps this running)
    {
      method: "shell.run",
      params: {
        path: "app/omni-source",
        message: [
          "sleep 300 && python scripts/approval_monitor.py"
        ],
        on: [{
          event: "/.*/",
          done: true
        }]
      }
    }
  ]
}
