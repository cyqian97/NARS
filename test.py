class A:
    def __init__(self, value):
        self.value = value

# Create an instance of A
a = A(10)

# Add the instance to two different lists and a set
list1 = [a]
list2 = [a]
set1 = {a}

# Modify the instance's attribute
a.value = 20

# Check if the modification is reflected across all collections
print(list1[0].value)  # Output: 20
print(list2[0].value)  # Output: 20

# For sets, the output depends on how the object's equality and hash code are defined.
# If you haven't overridden __eq__ and __hash__, this will work as expected.
# But modifying an object that affects its hash or equality while it's in a set can lead to undefined behavior.
print([item.value for item in set1])  # Output: [20] (assuming the object's hash/equality doesn't depend on 'value')

b = A(30)
set1.add(b)
b.value = 31
print([item.value for item in set1])  # Output: [20] (assuming the object's hash/equality doesn't depend on 'value')
list1.append(1)
print([item for item in list1]) 