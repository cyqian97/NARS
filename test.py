class test:
    def __init__(self,x):
        self.x = x     
    def __eq__(self, t):
        return t and self.x == t.x
    

    def __hash__(self):
        return self.x.__hash__()

a = test(1)
d = {a:"a"}
b = test(1)
print(a==b)
print(d[a])
print(d[b])
