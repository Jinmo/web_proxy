from hashlib import sha256
from OpenSSL import crypto
import os

EMPTY_ITEM = (None, None)
verbose = False

class HTTPHeaderDict:
	def __init__(self, *args, **kwargs):
		self.dict = dict(*args, **kwargs)
	def get(self, key, default=None):
		return self.dict.get(key.lower(), EMPTY_ITEM)[1]
	def items(self):
		return (item for key, item in self.dict.items())
	def __setitem__(self, key, value):
		if key.lower() in self.dict:
			key = self.dict[key.lower()][0] # preserve the key if exists
		self.dict[key.lower()] = (key, value)
	def __getitem__(self, key):
		if verbose:
			print('get', key)
		return self.get(key)
	def __delitem__(self, key):
		del self.dict[key.lower()]
	def __iter__(self):
		return self.dict.__iter__()

def gen_cert(domain,
            ca_crt,
            ca_key
            ):
    """This function takes a domain name as a parameter and then creates a certificate and key with the
    domain name(replacing dots by underscores), finally signing the certificate using specified CA and 
    returns the path of key and cert files. If you are yet to generate a CA then check the top comments"""
    
    domain = domain.decode()
    allowed_alphabet = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ012345789.'
    sanitized_domain = ''.join(filter(lambda x: x in allowed_alphabet, domain))
    domain_hash = sha256(domain.encode()).hexdigest()
    key_path = os.path.join(os.path.dirname(__file__),"domains",sanitized_domain + "_" + domain_hash+".key")
    cert_path = os.path.join(os.path.dirname(__file__),"domains",sanitized_domain + "_" + domain_hash+".crt")

    # Check happens if the certificate and key pair already exists for a domain
    if os.path.exists(key_path) and os.path.exists(cert_path):
        pass
    else:
        #Serial Generation - Serial number must be unique for each certificate,
        # so serial is generated based on domain name
        serial = int(domain_hash, 36)

        # The CA stuff is loaded from the same folder as this script
        ca_cert = crypto.load_certificate(crypto.FILETYPE_PEM, open(ca_crt).read())
        # The last parameter is the password for your CA key file
        ca_key = crypto.load_privatekey(crypto.FILETYPE_PEM, open(ca_key).read())


        key = crypto.PKey()
        key.generate_key( crypto.TYPE_RSA, 2048)

        cert = crypto.X509()
        cert.get_subject().C = "IN"
        cert.get_subject().ST = "AP"
        cert.get_subject().L = domain
        cert.get_subject().O = "jinmo123"
        cert.get_subject().OU = "Inbound-Proxy"
        cert.get_subject().CN = domain # This is where the domain fits
        cert.gmtime_adj_notBefore(0)
        cert.gmtime_adj_notAfter(365*24*60*60)
        cert.set_serial_number(serial)
        cert.set_issuer(ca_cert.get_subject())
        cert.set_pubkey(key)
        cert.sign(ca_key, "sha256")

        # The key and cert files are dumped and their paths are returned
        domain_key = open(key_path,"wb")
        domain_key.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, key))
        domain_key.close()
        
        domain_cert = open(cert_path,"wb")
        domain_cert.write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert))
        domain_cert.close()
    return key_path, cert_path

