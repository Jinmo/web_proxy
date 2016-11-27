EMPTY_ITEM = (None, None)

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
		print('get', key)
		return self.get(key)
	def __delitem__(self, key):
		del self.dict[key.lower()]
	def __iter__(self):
		return self.dict.__iter__()