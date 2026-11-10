export class ConfigurationError extends Error {}

// Framing, routing and MCP negotiation belong to the HTTP/MCP transports.
const managed = new Set([
  'host', 'content-length', 'transfer-encoding', 'connection', 'keep-alive',
  'proxy-connection', 'proxy-authenticate', 'proxy-authorization', 'te', 'trailer',
  'upgrade', 'expect', 'accept', 'accept-encoding', 'content-type', 'last-event-id',
]);
const invalidName = /[^!#$%&'*+.^_`|~0-9A-Za-z-]/;

export function requestHeaders(env, extra = []) {
  const headers = {};
  const names = new Set();
  let size = 0;
  const add = (name, value, custom = false) => {
    if (!name || invalidName.test(name) || name.length > 256 || /[^\x20-\x7e]/.test(value)) {
      throw new ConfigurationError('Headers require valid HTTP names and printable ASCII values without control characters.');
    }
    const lower = name.toLowerCase();
    if (custom && (managed.has(lower) || lower.startsWith('mcp-'))) {
      throw new ConfigurationError('Headers must not override HTTP framing, routing or MCP transport headers.');
    }
    if (names.has(lower)) throw new ConfigurationError('Headers contain a duplicate name, including configured authentication headers.');
    size += name.length + value.length + 4;
    if (names.size >= 64 || size > 16384) throw new ConfigurationError('Headers exceed the limit of 64 fields or 16 KiB.');
    names.add(lower);
    // Define an own property even for a valid name such as __proto__.
    Object.defineProperty(headers, name, { value, enumerable: true });
  };
  const key = env.CHANS_API_KEY?.trim();
  if (key) add('Authorization', `Bearer ${key}`);
  const accessId = env.CF_ACCESS_CLIENT_ID?.trim();
  const accessSecret = env.CF_ACCESS_CLIENT_SECRET?.trim();
  if (accessId || accessSecret) {
    if (!accessId || !accessSecret) throw new ConfigurationError('CF_ACCESS_CLIENT_ID and CF_ACCESS_CLIENT_SECRET must both be set.');
    if (!/^[\x21-\x7e]+$/.test(accessId) || !/^[\x21-\x7e]+$/.test(accessSecret)) {
      throw new ConfigurationError('CF_ACCESS_CLIENT_ID and CF_ACCESS_CLIENT_SECRET must be valid header values.');
    }
    add('CF-Access-Client-Id', accessId);
    add('CF-Access-Client-Secret', accessSecret);
  }
  for (const header of extra) {
    if (header.length > 16384) throw new ConfigurationError('Headers exceed the limit of 64 fields or 16 KiB.');
    const colon = header.indexOf(':');
    if (colon < 1) throw new ConfigurationError('Headers must use --header "Name: value".');
    const name = header.slice(0, colon);
    const raw = header.slice(colon + 1);
    // Validate before trimming so leading/trailing CR/LF cannot be hidden.
    if (/[^\x20-\x7e]/.test(raw)) throw new ConfigurationError('Headers must not contain control characters or non-ASCII values.');
    add(name, raw.trim(), true);
  }
  const authorization = Object.entries(headers).find(([name]) => name.toLowerCase() === 'authorization');
  if (!authorization?.[1]) throw new ConfigurationError('Set CHANS_API_KEY or provide an Authorization header.');
  return headers;
}
