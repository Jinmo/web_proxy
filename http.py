import asyncio
import urllib.parse

from util import HTTPHeaderDict

class HTTPConnection:
	def __init__(self, method=None, url=None, version=None, headers=None, body=None, ssl=None, client=None):
		self.method = method
		self.url = url
		self.version = version
		self.headers = headers
		self.body = body
		self.client = client
		self.reader, self.writer = None, None
		self.ssl = ssl

		self.hook = None

	@asyncio.coroutine
	def process(self):
		host, port = None, 80
		url = urllib.parse.urlsplit(self.url)
		if url.hostname is None:
			host = self.headers.get('host')
		else:
			host = url.hostname
		if host is None:
			print("where is host header? I don't know")
			return None
		if url.port is not None:
			port = url.port

		#print(host, port)
		self.reader, self.writer = yield from asyncio.open_connection(host, port, ssl=self.ssl)
		if url.path is not None:
			uri = url.path
		else:
			uri = b''
		if url.query is not None:
			uri = uri + b'?' + url.query
		payload = b' '.join([self.method, uri, self.version]) + b'\r\n'
		for key, value in self.headers.items():
			payload = payload + (key + b': ' + value + b'\r\n')
		payload = payload + b'\r\n'
		#print(payload)
		self.writer.write(payload)
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
		if headers.get(b'content-length') is not None:
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

class HTTP:
	def __init__(self, reader, writer):
		self.reader = reader
		self.writer = writer
		self.interceptor = None

	@asyncio.coroutine
	def accept(self):
		line = yield from self.reader.readline()
		if line == b'':
			return None
		method, url, version = line.rstrip(b'\r\n').split(b' ', 2)
		headers = HTTPHeaderDict()
		body = ''
		while True:
			line = yield from self.reader.readline()
			if line in (b'\n', b'\r\n'):
				break
			line = line.rstrip(b'\r\n')
			#print(line)
			key, value = line.split(b':', 1)
			value = value.lstrip(b' ')
			headers[key] = value

		if headers.get(b'content-length') is not None:
			contentLength = int(headers[b'content-length'])
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
			client=self)
