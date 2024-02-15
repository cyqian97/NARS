class MyMultiIndexClass:
    def __init__(self):
        self.data = {'a': 1, 'b': 2, 'c': 3}
    
    def __getitem__(self, key1, key2=None):
        print(key1)
        print(key2)
        if key2 is None:
            return self.data[key1]
        else:
            # Example of handling two keys
            return self.data[key1] + self.data[key2]

obj = MyMultiIndexClass()
print(obj['a'])  # Outputs: 1
print(obj['a','b'])  # Outputs: 3 (1 + 2)
