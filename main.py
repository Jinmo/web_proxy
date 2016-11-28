#!/usr/bin/python3

import asyncio
from http import HTTP, HTTPConnection

cache = {}

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
		yield from self._read_response()

def cacheable(headers):
	if b'cache-control' in headers:
		cacheControl = headers[b'cache-control'].split(b',')
		cacheControl = [x.strip() for x in cacheControl]
		#print(cacheControl)
		if not all((keyword not in cacheControl for keyword in NO_CACHE_KEYWORDS)):
			return False
	if b'pragma' in headers:
		pragma = headers[b'pragma']
		if pragma == b'no-cache':
			return False
	return True

def hook_response(conn, version, status, message, headers, body):
	host = conn.headers.get(b'host', b'')
	if host == b'search.daum.net':
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
			headers[b'accept-encoding'] = b'none'
	return None

def handle_echo(reader, writer):
	http = HTTP(reader, writer)
	http.interceptor = intercept_with_cache
	while True:
		conn = yield from http.accept()
		if conn is None:
			break
		conn.hook = hook_response
		result = yield from conn.process()

loop = asyncio.get_event_loop()
coro = asyncio.start_server(handle_echo, '127.0.0.1', 20000, loop=loop)
server = loop.run_until_complete(coro)

# Serve requests until Ctrl+C is pressed
print('Serving on {}'.format(server.sockets[0].getsockname()))
try:
    loop.run_forever()
except KeyboardInterrupt:
    pass

# Close the server
server.close()
loop.run_until_complete(server.wait_closed())
loop.close()