import itertools


def iteration_matchings(ids, mg):
    if len(ids) == 0:
        return [mg]

    id1 = ids[0]
    feasible_ids = [id2 for id2 in ids if id2 != id and mg[id2, -1] > 0]
    if len(feasible_ids) < mg[id1, 1]:
        return []

    mgs = []
    for combo in itertools.combinations(feasible_ids, mg[id1, 1]):
        _mg = mg.copy()
        for id2 in combo:
            _mg.connect(id1, 1, id2, -1)
        mgs += iteration_matchings(ids[1:], _mg)
    return mgs
