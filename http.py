import asyncio
import urllib.parse
import random

from util import HTTPHeaderDict
from config import *

class HTTPConnection:
	def __init__(self, method=None, url=None, version=None, headers=None, body=None,
			ssl=None, default_host=None, default_port=None, client=None):
		self.method = method
		self.url = url
		self.version = version
		self.headers = headers
		self.body = body
		self.client = client
		self.reader, self.writer = None, None
		self.ssl = ssl
		self.default_host = default_host
		self.default_port = default_port

		self.hook = None

	@asyncio.coroutine
	def process(self):
		host, port = None, 80
		url = urllib.parse.urlsplit(self.url)
		if url.hostname is None:
			host = self.headers.get(b'host')
		else:
			host = url.hostname
		
		if url.port is not None:
			port = url.port
		
		if self.default_host is not None:
			real_host = self.default_host
		else:
			real_host = host

		if self.default_port is not None:
			real_port = self.default_port
		else:
			real_port = port

		if real_host is None:
			print("where is host header? I don't know")
			return None

		print(real_host, real_port, self.ssl)
		self.reader, self.writer = yield from asyncio.open_connection(real_host, real_port, ssl=self.ssl, loop=loop)
		if url.path is not None:
			uri = url.path
		else:
			uri = b''
		if url.query:
			uri = uri + b'?' + url.query
		payload = b' '.join([self.method, uri, self.version]) + b'\r\n'
		for key, value in self.headers.items():
			payload = payload + (key + b': ' + value + b'\r\n')
		payload = payload + b'\r\n'
		if(self.ssl):
			print(payload, self.url)
		self.writer.write(payload)
		self.writer.write(self.body)
		yield from self._read_response()

	@asyncio.coroutine
	def _read_response(self):
		line = yield from self.reader.readline()
		version, status, message = line.rstrip(b'\r\n').split(b' ', 2)
		#print(version, status, message)	
		body = b''
		headers = HTTPHeaderDict()
		while True:
			line = yield from self.reader.readline()
			if line in (b'\n', b'\r\n'):
				break
			key, value = line.rstrip(b'\r\n').split(b':', 1)
			value = value.lstrip(b' ')
			headers[key] = value

		#print(headers)
		if b'content-length' in headers:
			contentLength = int(headers[b'content-length'])
			body = yield from self.reader.readexactly(contentLength)
		elif headers.get(b'transfer-encoding') is not None:
			#print('transfer-encoding', headers[b'transfer-encoding'])
			if headers[b'transfer-encoding'].lower() == b'chunked':
				while True:
					line = yield from self.reader.readline()
					#print(line)
					length = int(line, 16)
					#print(hex(length))
					if length == 0:
						break
					body += yield from self.reader.readexactly(length)
					#print(hex(len(body)))
					#print(body)
					yield from self.reader.readline()
				del headers[b'transfer-encoding']
				headers[b'content-length'] = str(len(body)).encode()

		if self.hook is not None:
			headers, body = self.hook(self, version, status, message, headers, body)
		payload = b' '.join([version, status, message]) + b'\r\n'
		for key, value in headers.items():
			payload += key + b': ' + value + b'\r\n'
		payload += b'\r\n'
		self.client.writer.write(payload)
		self.client.writer.write(body)

		self.close()

	def close(self):
		print('closing')
		if self.writer:
			self.writer.close()
			self.writer = None
		if self.reader:
			self.reader = None
		print('closed')

class ForwardConnection:
	def __init__(self, host, port, client, ssl_port_map):
		self.client = client
		self.host = host
		self.port = port
		self.ssl_port_map = ssl_port_map
		self.reader = None
		self.writer = None

	@asyncio.coroutine
	def process(self):
		local_port = random.randint(30000, 65535)
		self.ssl_port_map[local_port] = self.host, self.port
		print(local_port)
		self.reader, self.writer = yield from asyncio.open_connection('127.0.0.1', HTTPS_PROXY_PORT, loop=loop, local_addr=('127.0.0.1', local_port))
		self.client.writer.write(b'HTTP/1.1 200 Connection Established\r\n\r\n')
		def relay(source, destination):
			while True: # SSL stream here? or not
				c = yield from source.read(8)
				if c == b'':
					break
				destination.write(c)
		client_read = relay(self.client.reader, self.writer)
		server_read = relay(self.reader, self.client.writer)
		yield from asyncio.wait((client_read, server_read), loop=loop)

class HTTP:
	def __init__(self, reader, writer, ssl_port_map, default_host=None, default_port=None, ssl=False, interceptor=None):
		self.reader = reader
		self.writer = writer
		self.ssl_port_map = ssl_port_map
		self.ssl = ssl
		self.default_host = default_host
		self.default_port = default_port
		self.interceptor = interceptor

	@asyncio.coroutine
	def accept(self):
		line = yield from self.reader.readline()
		if line == b'':
			return None
		print(line)
		method, url, version = line.rstrip(b'\r\n').split(b' ', 2)
		headers = HTTPHeaderDict()
		body = b''
		while True:
			line = yield from self.reader.readline()
			if line in (b'\n', b'\r\n'):
				break
			line = line.rstrip(b'\r\n')
			#print(line)
			key, value = line.split(b':', 1)
			value = value.lstrip(b' ')
			headers[key] = value

		if method == b'CONNECT':
			# turning into ssl
			host, port = url.split(b':', 2)
			port = int(port)
			print('CONNECT request on', host, port)
			return ForwardConnection(host=host,
				port=port,
				client=self,
				ssl_port_map=self.ssl_port_map)

		if headers.get(b'content-length') is not None:
			contentLength = int(headers[b'content-length'])
			print('[post reqest] reading body', contentLength)
			body = yield from self.reader.readexactly(contentLength)

		print(method, url, version)

		if self.interceptor is not None:
			result = self.interceptor(method=method,
				url=url,
				version=version,
				headers=headers,
				body=body,
				client=self)
			if result is not None:
				return result

		return HTTPConnection(method=method,
			url=url,
			version=version,
			headers=headers,
			body=body,
			default_host=self.default_host,
			default_port=self.default_port,
			ssl=self.ssl,
			client=self)
