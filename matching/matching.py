import csv
import os
from tqdm import tqdm
from definitions import *
from iterate import *
from collections import defaultdict
from plot import *
import matplotlib.pyplot as plt

ground_truth = defaultdict(set)
IDs = set()

# Define the path to your CSV file
csv_file_path = "environments/2024-05-19_18-05-28.csv"  # "environments/2024-05-19_18-01-26.csv" #'bitcomp.csv'
node_num = -1
# Open the CSV file and read it line by line
with open(csv_file_path, mode="r", newline="") as csvfile:
    csvreader = csv.reader(csvfile)
    for row in csvreader:
        # Convert each element in the row to an integer
        ID1, side1, ID2, side2 = [int(element) for element in row]
        if ID1 > node_num - 1:
            node_num = ID1 + 1
        if ID2 > node_num - 1:
            node_num = ID2 + 1
        if (side1 == 1 and side2 == -1) or (side1 == -1 and side2 == 1):
            ground_truth[ID1, side1].update([(ID2, side2)])
            ground_truth[ID2, side2].update([(ID1, side1)])
            IDs.update([ID1, ID2])
IDs = list(IDs)
IDs.sort()
mg = MatchingGraph(node_num)
for ID in IDs:
    n_p = len(ground_truth[(ID, 1)])
    n_n = len(ground_truth[(ID, -1)])
    mg.add_node(ID, n_p, n_n)

print("Generating all possible matchings...")
mgs = iteration_matchings(IDs, mg)
print(f"\t{len(mgs)} matching generated")

print("Checking matchings...")
num_valid = 0
for mg in tqdm(mgs):
    if mg.check_matching():
        plot_directed_graph_on_circle(
            mg.node_num - 1,
            mg.all_edges(),
            file_name=os.path.splitext(csv_file_path)[0] + f"_{num_valid}.svg",
        )
        num_valid += 1
print(f"Valid matching: {num_valid}")
