import os
from sslserver import MyLoop

loop = MyLoop()
HTTP_PROXY_PORT = 8080
HTTPS_PROXY_PORT = 8081
BIND_ADDRESS = '0.0.0.0'

DOMAIN_CERT_PATH = os.path.dirname(__file__) + '/domains'

try:
	os.mkdir(DOMAIN_CERT_PATH)
except:
	pass