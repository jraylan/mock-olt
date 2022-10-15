import pickle
import re

class PersistentDict(dict):

    def __init__(self, filename, *args, **kwargs):
        self.filename = re.sub(r'[^a-zA-Z0-9]', '', filename)
        if not self.filename:
            self.filename = '__empty__'            
        self.filename += '.data'
        try:
            with open(filename, 'rb') as f:
                self.update(pickle.load(f))
        except:
            pass
        self.update(dict(*args, **kwargs))

    def __setitem__(self, key, item):
        dict.__setitem__(self, key, item)
        self.save()

    def __delitem__(self, key):
        dict.__delitem__(self, key)
        self.save()

    def update(self, *args, **kwargs):
        dict.update(self, *args, **kwargs)
        self.save()

    def save(self):
        with open(self.filename, 'wb') as f:
            pickle.dump(dict(self), f, 2)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.save()