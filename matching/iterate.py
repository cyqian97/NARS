import itertools


def iteration_matchings(IDs, mg):
    if len(IDs) == 0:
        return [mg]

    ID1 = IDs[0]
    feasible_ids = mg.feasible_ids(ID1,1,-1)
    if len(feasible_ids) < mg[ID1, 1]:
        return []

    mgs = []
    for combo in itertools.combinations(feasible_ids, mg[ID1, 1]):
        _mg = mg.copy()
        for ID2 in combo:
            _mg.connect(ID1, 1, ID2, -1)
        mgs += iteration_matchings(IDs[1:], _mg)
    return mgs
