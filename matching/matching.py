import csv
from matching import *

ground_truth = defaultdict(set)
mg = MatchingGraph()
max_id = -1

# Define the path to your CSV file
csv_file_path = 'bitcomp.csv'
# Open the CSV file and read it line by line
with open(csv_file_path, mode='r', newline='') as csvfile:
    csvreader = csv.reader(csvfile)
    for row in csvreader:
        # Convert each element in the row to an integer
        id1,side1,id2,side2 = [int(element) for element in row]
        if (side1 == 1 and side2 == -1) or (side1 == -1 and side2 == 1): 
            ground_truth[id1, side1].update([(id2, side2)])
            ground_truth[id2, side2].update([(id1, side1)])
        if id1 > max_id:
            max_id = id1

for id in range(max_id+1):
    n_p = len(ground_truth[(id,1)])
    n_n = len(ground_truth[(id,-1)])
    mg.add_node(id,n_p,n_n)

