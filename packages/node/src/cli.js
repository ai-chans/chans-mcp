#!/usr/bin/env node
import { bridge, configuration, doctor, VERSION } from './bridge.js';

const args = process.argv.slice(2);
if (args.length === 1 && args[0] === '--version') {
  console.log(VERSION);
} else if (args.length === 1 && ['--help', '-h'].includes(args[0])) {
  console.log('Usage: chans-mcp [doctor|--version|--help]\nSet CHANS_API_KEY; optionally CHANS_MCP_URL. No arguments starts the stdio bridge.');
} else if (args.length > 1 || (args.length === 1 && args[0] !== 'doctor')) {
  console.error('Usage: chans-mcp [doctor|--version|--help]');
  process.exitCode = 2;
} else {
  try {
    const config = configuration();
    if (args[0] === 'doctor') await doctor(config);
    else await bridge(config);
  } catch (error) {
    // SDK/HTTP errors can contain URLs and headers; never print them verbatim.
    console.error(error.message.startsWith('CHANS_') || error.message.startsWith('Set CHANS_')
      ? error.message : 'Chans MCP connection failed. Check credentials, endpoint and connectivity. Check operation status before retrying an interrupted tool call.');
    process.exitCode = 1;
  }
}
