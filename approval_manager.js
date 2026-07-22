#!/usr/bin/env node

/**
 * Approval Manager Launcher
 * CLI interface for managing pending approvals
 */

module.exports = {
  run: [
    // List pending approvals
    {
      method: "shell.run",
      params: {
        venv: "env",
        path: "app/omni-source",
        message: [
          "python scripts/approval_manager.py list"
        ],
        on: [{
          event: "/.*/",
          done: true
        }]
      }
    }
  ]
}
