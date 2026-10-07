"""One public HTTPS page, with DNS-pinned TLS and bounded extraction.

Runs in a disposable process: the parent's deadline also bounds DNS lookup.
No proxy, cookies, credentials, JavaScript, local files or automatic retries.
"""
from __future__ import annotations
from html.parser import HTMLParser
import http.client
import ipaddress
import json
import re
import socket
import ssl
import sys
from urllib.parse import urljoin, urlsplit, urlunsplit

MAX_BYTES = 1024 * 1024
MAX_TEXT = 6000
METADATA = {'metadata.google.internal', 'metadata.google.com'}

class PageError(ValueError):
    pass

def network_error(exc, phase):
    """Stable codes only: never expose exception text, destination or TLS details."""
    if isinstance(exc, ssl.SSLCertVerificationError):
        return 'tls_certificate_invalid'
    if isinstance(exc, ssl.SSLError):
        return 'tls_error'
    if isinstance(exc, TimeoutError):
        return phase + '_timeout'
    if isinstance(exc, ConnectionRefusedError):
        return phase + '_refused'
    if isinstance(exc, http.client.IncompleteRead):
        return 'body_incomplete'
    if isinstance(exc, http.client.RemoteDisconnected):
        return phase + '_disconnected'
    if isinstance(exc, http.client.HTTPException):
        return phase + '_invalid_http'
    if isinstance(exc, OSError):
        return phase + '_network_error'
    return 'unexpected_worker_error'

def address_allowed(value):
    ip = ipaddress.ip_address(value)
    if isinstance(ip, ipaddress.IPv6Address):
        if ip.ipv4_mapped:
            return address_allowed(str(ip.ipv4_mapped))
        # Transition addresses can conceal another destination.
        if ip.sixtofour or ip.teredo or any(ip in ipaddress.ip_network(net) for net in ('::/96', '64:ff9b::/96', '64:ff9b:1::/48')):
            return False
    return ip.is_global and not ip.is_multicast and str(ip) != '100.100.100.200'

def target(url):
    if not isinstance(url, str) or len(url) > 2048 or any(ord(c) <= 32 or ord(c) == 127 for c in url) or '\\' in url:
        raise PageError('invalid_url')
    try:
        parts = urlsplit(url)
        host = (parts.hostname or '').encode('idna').decode('ascii').lower().rstrip('.')
        port = parts.port
    except (ValueError, UnicodeError):
        raise PageError('invalid_url') from None
    if parts.scheme != 'https' or not host or parts.username is not None or parts.password is not None or port not in (None, 443):
        raise PageError('https_public_only')
    if host in METADATA or host == 'localhost' or host.endswith(('.localhost', '.local', '.internal')):
        raise PageError('private_destination')
    try:
        rows = socket.getaddrinfo(host, 443, socket.AF_UNSPEC, socket.SOCK_STREAM)
        addresses = list(dict.fromkeys(row[4][0] for row in rows))
        if not addresses or len(addresses) > 16 or not all(address_allowed(ip) for ip in addresses):
            raise PageError('private_destination')
    except (socket.gaierror, ValueError) as exc:
        if isinstance(exc, PageError):
            raise
        raise PageError('dns_unavailable') from None
    path = urlunsplit(('', '', parts.path or '/', parts.query, ''))
    return host, addresses[0], path

class PinnedHTTPS(http.client.HTTPSConnection):
    def __init__(self, host, address):
        super().__init__(host, timeout=8, context=ssl.create_default_context())
        self.address = address

    def connect(self):
        # Numeric address from the checked DNS result; TLS authenticates the
        # original hostname. No second hostname lookup or alternative IP retry.
        try:
            raw = socket.create_connection((self.address, 443), self.timeout)
        except OSError as exc:
            raise PageError(network_error(exc, 'connection')) from None
        try:
            self.sock = self._context.wrap_socket(raw, server_hostname=self.host)
        except Exception as exc:
            raw.close()
            raise PageError(network_error(exc, 'tls')) from None
        except BaseException:
            raw.close()
            raise

class TextParser(HTMLParser):
    BLOCK = {'script', 'style', 'noscript', 'iframe', 'svg', 'form', 'nav', 'footer', 'aside', 'template'}
    BREAK = {'p', 'div', 'br', 'li', 'h1', 'h2', 'h3', 'h4', 'article', 'section', 'tr', 'pre'}
    VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'}
    ROLES = {'navigation', 'banner', 'contentinfo', 'search', 'complementary'}
    CHROME = {'related', 'sphinxsidebar', 'sidebar', 'footer', 'headerlink', 'site-header', 'site-footer', 'navigation', 'breadcrumbs', 'breadcrumb'}
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []  # tag, excluded, inside main, inside title
        self.parts = []
        self.main_parts = []
        self.has_main = False
        self.title_parts = []

    def state(self):
        return self.stack[-1][1:] if self.stack else (False, False, False)

    def append(self, data, main):
        self.parts.append(data)
        if main: self.main_parts.append(data)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        excluded, main, title = self.state()
        roles = set((attrs.get('role') or '').lower().split())
        classes = set((attrs.get('class') or '').lower().split())
        hidden_style = re.search(r'(?:display\s*:\s*none|visibility\s*:\s*hidden)', attrs.get('style') or '', re.I)
        excluded = bool(excluded or tag in self.BLOCK or roles & self.ROLES or classes & self.CHROME or 'hidden' in attrs or attrs.get('aria-hidden') == 'true' or hidden_style or (tag == 'header' and not main))
        main = main or (not excluded and (tag == 'main' or 'main' in roles))
        if main and not excluded: self.has_main = True
        title = title or tag == 'title'
        if not excluded and tag in self.BREAK: self.append('\n', main)
        if tag not in self.VOID: self.stack.append((tag, excluded, main, title))

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in self.VOID: self.handle_endtag(tag)

    def handle_endtag(self, tag):
        excluded, main, _ = self.state()
        if not excluded and tag in self.BREAK: self.append('\n', main)
        for index in range(len(self.stack)-1, -1, -1):
            if self.stack[index][0] == tag:
                del self.stack[index:]
                break

    def handle_data(self, data):
        excluded, main, title = self.state()
        if excluded: return
        if title: self.title_parts.append(data)
        else:
            # HTML source wrapping is whitespace within prose, not an evidence
            # boundary. Keep real block/<br> boundaries inserted by tag handlers
            # and code line breaks in <pre>. Preserve spaces around inline tags.
            if not any(entry[0] == 'pre' for entry in self.stack):
                data = re.sub(r'\s+', ' ', data)
            self.append(data, main)

def extract(body, content_type):
    charset_match = re.search(r'charset\s*=\s*["\']?([\w-]+)', content_type, re.I)
    charset = charset_match.group(1) if charset_match else 'utf-8'
    if charset.lower() not in {'utf-8', 'utf8', 'iso-8859-1', 'latin-1', 'windows-1252', 'us-ascii'}:
        raise PageError('unsupported_charset')
    decoded = body.decode(charset, errors='replace')
    title = ''
    if content_type.split(';')[0].strip().lower() == 'text/html':
        parser = TextParser()
        parser.feed(decoded)
        decoded = ''.join(parser.main_parts if parser.has_main else parser.parts)
        title = ' '.join(''.join(parser.title_parts).split())[:200]
    text = '\n'.join(' '.join(line.split()) for line in decoded.splitlines() if line.strip())
    if len(text) < 40:
        raise PageError('no_readable_text')
    return title, text[:MAX_TEXT], len(text) > MAX_TEXT

def fetch_page(url):
    current = url
    for hop in range(3):
        host, address, path = target(current)
        connection = PinnedHTTPS(host, address)
        phase = 'request'
        try:
            connection.request('GET', path, headers={'User-Agent': 'OpenJarvis-Andrea/1.0', 'Accept': 'text/html,text/plain', 'Accept-Encoding': 'identity'})
            phase = 'response'
            response = connection.getresponse()
            if response.status in {301, 302, 303, 307, 308}:
                location = response.getheader('Location')
                if not location or hop == 2: raise PageError('redirect_limit')
                current = urljoin(current, location)
                continue
            if response.status != 200: raise PageError('http_' + str(response.status))
            content_type = response.getheader('Content-Type', '')
            if content_type.split(';')[0].strip().lower() not in {'text/html', 'text/plain'}:
                raise PageError('unsupported_content_type')
            if response.getheader('Content-Encoding', 'identity').lower() != 'identity':
                raise PageError('unsupported_encoding')
            phase = 'body'
            body = response.read(MAX_BYTES + 1)
            if len(body) > MAX_BYTES: raise PageError('page_too_large')
            title, text, partial = extract(body, content_type)
            return {'url': current, 'title': title, 'text': text, 'partial': partial, 'redirects': hop}
        except PageError:
            raise
        except (OSError, http.client.HTTPException) as exc:
            raise PageError(network_error(exc, phase)) from None
        finally:
            connection.close()
    raise PageError('redirect_limit')

def read_request(raw):
    try:
        if len(raw) > 4096: raise PageError('invalid_request')
        try:
            data = json.loads(raw)
        except (ValueError, UnicodeError):
            raise PageError('invalid_request') from None
        if not isinstance(data, dict) or set(data) != {'url'}: raise PageError('invalid_request')
        result = fetch_page(data['url'])
    except PageError as exc:
        result = {'error': str(exc)}
    except Exception:
        result = {'error': 'unexpected_worker_error'}
    return result

if __name__ == '__main__':
    result = read_request(sys.stdin.buffer.read(4097))
    print(json.dumps(result, ensure_ascii=False))
