class A:
    def __init__(self, value):
        self.value = value

# Create an instance of A
a = A(10)
b = A(20)
c=a
a=b
b=c
print(a.value)
print(b.value)