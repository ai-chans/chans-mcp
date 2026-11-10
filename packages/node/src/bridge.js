import { StreamableHTTPClientTransport } from '@modelcontextprotocol/sdk/client/streamableHttp.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { Client } from '@modelcontextprotocol/sdk/client/index.js';

export const VERSION = '0.1.1';

export function configuration(env = process.env) {
  const key = env.CHANS_API_KEY?.trim();
  if (!key || /[\r\n]/.test(key)) throw new Error('Set CHANS_API_KEY to a valid Chans API key.');
  let url;
  const endpoint = env.CHANS_MCP_URL ?? 'https://api.chans.ai/mcp/';
  try {
    if (/\s/.test(endpoint)) throw new Error();
    url = new URL(endpoint);
  }
  catch { throw new Error('CHANS_MCP_URL must be a valid endpoint URL.'); }
  const loopback = ['localhost', '127.0.0.1', '[::1]'].includes(url.hostname);
  if ((url.protocol !== 'https:' && !(url.protocol === 'http:' && loopback)) ||
      url.username || url.password || url.search || url.hash) {
    throw new Error('CHANS_MCP_URL requires HTTPS (HTTP is allowed on loopback), without credentials, query or fragment.');
  }
  return { url, key };
}

function transport({ url, key }) {
  return new StreamableHTTPClientTransport(url, {
    requestInit: { headers: { Authorization: `Bearer ${key}` }, redirect: 'error' },
    // SSE reconnection can resume streams; never replay a failed tool POST.
    reconnectionOptions: { maxRetries: 0, initialReconnectionDelay: 1000,
      maxReconnectionDelay: 1000, reconnectionDelayGrowFactor: 1 },
  });
}

export async function doctor(config) {
  const client = new Client({ name: 'chans-mcp-doctor', version: VERSION });
  try {
    await client.connect(transport(config));
    let cursor;
    let count = 0;
    do {
      const page = await client.listTools(cursor ? { cursor } : undefined);
      count += page.tools.length;
      cursor = page.nextCursor;
    } while (cursor);
    console.error(`Chans MCP connected; ${count} authorized tools available. No tools executed.`);
  } finally { await client.close(); }
}

export async function bridge(config) {
  const local = new StdioServerTransport();
  const remote = transport(config);
  let initializeId;
  let closing = false;
  let rejectFailure;
  const failure = new Promise((_, reject) => { rejectFailure = reject; });
  const fail = () => rejectFailure(new Error('Chans MCP transport failed. Check credentials, endpoint and connectivity. In-flight operations may have completed; check their status before retrying.'));
  const close = async () => {
    if (closing) return;
    closing = true;
    await Promise.allSettled([local.close(), remote.close()]);
  };
  let finish;
  const ended = new Promise(resolve => { finish = resolve; });
  local.onerror = fail;
  remote.onerror = fail;
  local.onclose = finish;
  remote.onclose = finish;
  local.onmessage = message => {
    if (message.method === 'initialize') initializeId = message.id;
    // Preserve JSON-RPC IDs and capabilities: the hosted server owns negotiation.
    remote.send(message).catch(fail);
  };
  remote.onmessage = message => {
    if (message.id === initializeId && message.result?.protocolVersion) {
      remote.setProtocolVersion(message.result.protocolVersion);
    }
    local.send(message).catch(fail);
  };
  const signal = () => finish();
  process.once('SIGINT', signal);
  process.once('SIGTERM', signal);
  const eof = () => finish();
  process.stdin.once('end', eof);
  try {
    await remote.start();
    await local.start();
    await Promise.race([ended, failure]);
  } finally {
    process.removeListener('SIGINT', signal);
    process.removeListener('SIGTERM', signal);
    process.stdin.removeListener('end', eof);
    await close();
  }
}
