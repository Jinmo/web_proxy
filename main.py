#!/usr/bin/python3

import asyncio
import ssl
import sys
import traceback
from http import HTTP, HTTPConnection
from config import HTTP_PROXY_PORT, HTTPS_PROXY_PORT, BIND_ADDRESS, loop
from util import gen_cert

cache = {}
ssl_port_map = {}
ssl_host_map = {}
ssl_connected_port_map = {}

NO_CACHE_KEYWORDS = [
b'no-store',
b'no-cache',
b'must-revalidate'
]

class CacheConnection:
	def __init__(self, client, url, body):
		self.client = client
		self.url = url
		self.body = body
		pass

	@asyncio.coroutine
	def _read_response(self):
		payload = b'HTTP/1.1 200 Cached\r\n'
		payload += b'Content-Length: ' + str(len(self.body)).encode()
		payload += b'\r\n'
		payload += b'\r\n'
		self.client.writer.write(payload)
		self.client.writer.write(self.body)

	@asyncio.coroutine
	def process(self):
		self._read_response()

def cacheable(headers):
	if b'cache-control' in headers:
		cacheControl = headers[b'cache-control'].split(b',')
		cacheControl = [x.strip() for x in cacheControl]
		#print(cacheControl)
		if not all((keyword not in cacheControl for keyword in NO_CACHE_KEYWORDS)):
			return False
	else:
		return False
	if b'pragma' in headers:
		pragma = headers[b'pragma']
		if pragma == b'no-cache':
			return False
	return True

def hook_response(conn, version, status, message, headers, body):
	host = conn.headers.get(b'host', b'')
	if host == b'search.daum.net' or host == b'search.naver.com': # naver, too. SSL!
		body = body.replace(b'Michael', b'GILBERT')
	elif host == b'test.gilgil.net':
		body = body.replace(b'hacking', b'ABCDEFG')
	# cache
	if int(status) == 200 and cacheable(headers):
		cache[conn.url] = body
		print('cache registered for', conn.url)
	return headers, body

def intercept_with_cache(method, url, version, headers, body, client):
	print('searching cache for', url)
	if cache.get(url) is not None:
		print('got cache for', url)
		return CacheConnection(client=client, url=url, body=cache[url])
	# remove gzip encoding
	host = headers.get(b'host', b'')
	if b'accept-encoding' in headers:
		if b'gzip' in headers[b'accept-encoding']:
			del headers[b'accept-encoding']
	return None

def httpproxy(reader, writer):
	global ssl_port_map, ssl_connected_port_map
	host, port = writer.get_extra_info('peername')
	if port in ssl_connected_port_map:
		default_host, default_port = ssl_connected_port_map[port]
		with_ssl = True
	else:
		default_host, default_port = None, None
		with_ssl = False
	http = HTTP(reader, writer, ssl_port_map,
		default_host=default_host,
		default_port=default_port,
		ssl=with_ssl)
	http.interceptor = intercept_with_cache
	while True:
		conn = yield from http.accept()
		if conn is None:
			break
		conn.hook = hook_response
		try:
			result = yield from conn.process()
		except:
			traceback.print_exc(file=sys.stdout)
			writer.close()
			return

def ssl_generator(sock):
	global ssl_host_map, ssl_port_map
	addr, port = sock.getpeername()
	if port not in ssl_port_map:
		return
	domain, dstport = ssl_port_map[port]
	print(domain,dstport)
	del ssl_port_map[port]
	key_path, cert_path = gen_cert(domain, 'root/root.crt', 'root/root.key')
	ssl_host_map[domain] = cert_path, key_path
	ssl_connected_port_map[port] = domain, dstport
	context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
	context.load_cert_chain(cert_path, key_path)
	return context

loop.ssl_generator = ssl_generator
coro = asyncio.start_server(httpproxy, BIND_ADDRESS, HTTP_PROXY_PORT, loop=loop)
coroSSL = asyncio.start_server(httpproxy, BIND_ADDRESS, HTTPS_PROXY_PORT, loop=loop)
server = loop.run_until_complete(coro)
sslserver = loop.run_until_complete(coroSSL)

# Serve requests until Ctrl+C is pressed
for socket in server.sockets:
	print('Serving on {}'.format(socket.getsockname()))
for socket in sslserver.sockets:
	print('SSL Serving on {}'.format(socket.getsockname()))
try:
    loop.run_forever()
except KeyboardInterrupt:
    pass

# Close the server
server.close()
sslserver.close()
loop.run_until_complete(server.wait_closed())
loop.run_until_complete(sslserver.wait_closed())
loop.close()