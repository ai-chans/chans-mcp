#!/usr/bin/env node
import { parseArgs } from 'node:util';
import { bridge, configuration, doctor, VERSION } from './bridge.js';
import { ConfigurationError } from './headers.js';

let parsed;
try {
  parsed = parseArgs({
    allowPositionals: true,
    options: {
      header: { type: 'string', multiple: true }, url: { type: 'string' },
      help: { type: 'boolean', short: 'h' }, version: { type: 'boolean' },
    },
  });
  if (parsed.positionals.length > 1 ||
      (parsed.positionals.length === 1 && parsed.positionals[0] !== 'doctor')) throw new Error();
} catch {
  console.error('Usage: chans-mcp [doctor] [--url URL] [--header "Name: value"] [--version|--help]');
  process.exitCode = 2;
}
if (parsed && process.exitCode !== 2) {
  const { values, positionals } = parsed;
  if (values.version) console.log(VERSION);
  else if (values.help) {
    console.log('Usage: chans-mcp [doctor] [--url URL] [--header "Name: value"]\nRepeat --header for additional HTTP headers. Set CHANS_API_KEY or pass Authorization.');
  } else {
    try {
      const config = configuration(process.env, values);
      if (positionals[0] === 'doctor') await doctor(config);
      else await bridge(config);
    } catch (error) {
      // Never print raw HTTP/SDK errors or command-line values.
      console.error(error instanceof ConfigurationError ? error.message :
        'Chans MCP connection failed. Check credentials, endpoint and connectivity. Check operation status before retrying an interrupted tool call.');
      process.exitCode = 1;
    }
  }
}
