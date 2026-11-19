#!/usr/bin/env node
'use strict';

const { spawnSync } = require('child_process');
const path = require('path');
const fs = require('fs');

// Check that python3 is available
const checkPython = spawnSync('python3', ['--version'], { stdio: 'pipe' });
if (checkPython.error || checkPython.status !== 0) {
  console.error('Error: Python 3 is required by Agentic SDLC Kit but was not found in PATH.');
  console.error('Please install Python 3 (standard library only, no pip dependencies required) and retry.');
  process.exit(1);
}

// Locate the kit root directory containing scripts/install.py
const kitRoot = path.resolve(__dirname, '..');
const installScript = path.join(kitRoot, 'scripts', 'install.py');

if (!fs.existsSync(installScript)) {
  console.error(`Error: Installer script not found at ${installScript}`);
  process.exit(1);
}

const rawArgs = process.argv.slice(2);
const isHelp = rawArgs.includes('-h') || rawArgs.includes('--help');

let args = [];

if (isHelp) {
  args = rawArgs;
} else {
  const VALUE_OPTIONS = new Set(['--profile', '--with', '--on-conflict']);
  let explicitTarget = null;
  const passthroughArgs = [];
  let i = 0;

  while (i < rawArgs.length) {
    const arg = rawArgs[i];
    if (VALUE_OPTIONS.has(arg)) {
      passthroughArgs.push(arg);
      i++;
      if (i < rawArgs.length) {
        passthroughArgs.push(rawArgs[i]);
        i++;
      }
    } else if (
      arg.startsWith('--profile=') ||
      arg.startsWith('--with=') ||
      arg.startsWith('--on-conflict=')
    ) {
      passthroughArgs.push(arg);
      i++;
    } else if (arg.startsWith('-')) {
      passthroughArgs.push(arg);
      i++;
    } else {
      if (explicitTarget === null) {
        explicitTarget = arg;
      } else {
        passthroughArgs.push(arg);
      }
      i++;
    }
  }

  const target = explicitTarget !== null ? explicitTarget : process.cwd();
  args = [target, ...passthroughArgs];
}

// Execute install.py forwarding stdio and exit code
const result = spawnSync('python3', [installScript, ...args], {
  stdio: 'inherit',
  env: process.env,
});

if (result.error) {
  console.error(`Error executing installer: ${result.error.message}`);
  process.exit(1);
}

process.exit(result.status ?? 0);
