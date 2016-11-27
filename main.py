#!/usr/bin/python3

import asyncio
from http import HTTP, HTTPConnection

def hook_response(conn, headers, body):
	return headers, body

def handle_echo(reader, writer):
	http = HTTP(reader, writer)
	while True:
		conn = yield from http.accept()
		if conn is None:
			break
		# remove gzip encoding
		if b'accept-encoding' in conn.headers:
			if b'gzip' in conn.headers[b'accept-encoding']:
				conn.headers[b'accept-encoding'] = b'none'
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