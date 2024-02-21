x = {1: [2,3], 3: [4,5], 4: [3,7], 2: [1,0], 0: [0,6]}
print(x)
print(dict(sorted(x.items(), key=lambda item: item[1][0])))
print(dict(sorted(x.items(), key=lambda item: item[1][1])))
print(x[1])