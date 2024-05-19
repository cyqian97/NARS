import csv
from tqdm import tqdm
from definitions import *
from iterate import *
from collections import defaultdict

ground_truth = defaultdict(set)
ids = set()

# Define the path to your CSV file
csv_file_path = 'bitcomp.csv'
node_num = -1
# Open the CSV file and read it line by line
with open(csv_file_path, mode='r', newline='') as csvfile:
    csvreader = csv.reader(csvfile)
    for row in csvreader:
        # Convert each element in the row to an integer
        id1, side1, id2, side2 = [int(element) for element in row]
        if id1 > node_num:
            node_num = id1
        if id2 > node_num:
            node_num = id2
        if (side1 == 1 and side2 == -1) or (side1 == -1 and side2 == 1):
            ground_truth[id1, side1].update([(id2, side2)])
            ground_truth[id2, side2].update([(id1, side1)])
            ids.update([id1, id2])
ids = list(ids)
ids.sort()
mg = MatchingGraph(node_num)
for id in ids:
    n_p = len(ground_truth[(id, 1)])
    n_n = len(ground_truth[(id, -1)])
    mg.add_node(id, n_p, n_n)

print("Generating all possible matchings...")
mgs = iteration_matchings(ids, mg)

print("Checking matchings...")
for mg in tqdm(mgs):
    if mg.check_matching():
        print(mg)
