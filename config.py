import os
from sslserver import MyLoop

loop = MyLoop()
HTTP_PROXY_PORT = 20000
HTTPS_PROXY_PORT = 20001
BIND_ADDRESS = '0.0.0.0'

DOMAIN_CERT_PATH = os.path.dirname(__file__) + '/domains'

try:
	os.mkdir(DOMAIN_CERT_PATH)
except:
	pass