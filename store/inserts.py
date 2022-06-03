query = """
insert into query (name, sql, overwritten_sql, plan, runs, cost)
values ($1, $2, $3, $4, $5, $6);
"""

action = """
insert into action (type, name, command)
values ($1, $2, $3);
"""

node = """
insert into node (id, action, parent, gain, cost, recommended)
select $1, id, $3, $4, $5, $6
from action
where name = $2;
"""

results = """
insert into node_query_result (node, query, gain)
select $1, id, $3
from query
where name = $2;
"""
