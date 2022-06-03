import json

import deepdiff
import dictdiffer
import mo_sql_parsing


def transform_dict(d: dict) -> dict:
    n = {}

    if "and" not in d:
        d = {"and": [d]}

    for cond in d["and"]:
        for k, v in cond.items():
            n[v[0]] = {"op": k, "v": v[1]}

    return n


def reverse_dict(d: dict) -> dict:
    n = {"and": []}

    for k, v in d.items():
        n["and"].append({v["op"]: [k, v["v"]]})

    if len(d) == 1:
        return n["and"][0]

    return n


if __name__ == "__main__":
    query_1 = """
    select resource_group_id, count(member)
    from resource_group_membership
    join resource_group rg on resource_group_membership.resource_group_id = rg.id
    where resource_group_membership.resource_group_id > 500
    and resource_group_membership.active is true
    group by resource_group_id
    having count(member) > 1
    """

    query_2 = """
    select resource_group_id, count(member)
    from resource_group_membership
    join resource_group rg on resource_group_membership.resource_group_id = rg.id
    where resource_group_membership.active is true
    group by resource_group_id
    """

    # Query
    d1 = mo_sql_parsing.parse(query_1)["where"]
    print(d1)
    d1 = transform_dict(d1)
    print(d1)

    # MView
    d2 = mo_sql_parsing.parse(query_2)["where"]
    print(d2)
    d2 = transform_dict(d2)
    print(d2)

    diff = {}
    for k, v in d1.items():
        if k in d2:
            continue
        diff[k] = v

    print(diff)
    print(len(diff))

    conds = reverse_dict(diff)
    print(conds)
    print(mo_sql_parsing.format(conds))
