import graphviz as gv
from collections import defaultdict


# build supplemental data structures necessary for visualization with graphviz
def get_formatting_states(regex):
    states_list = []
    invisible_transitions = []

    for i, unit in enumerate(regex):
        states_list.append((i, unit))
        if i > 0:
            invisible_transitions.append((i - 1, i))

    return states_list, invisible_transitions


# build match transition digraph
def get_match_transitions(regex):
    # create dictionary that can support keys with multiple edges
    match_transitions = defaultdict(list)
    for i, unit in enumerate(regex):
        if i > 0 and regex[i - 1].isalpha():
            match_transitions[i - 1].append(i)

    return match_transitions


# build epsilon transition digraph
# need to create mini dictionaries of specific edges for graphviz formatting
def get_epsilon_transitions(regex):
    # create dictionary the can support keys with multiple edges
    epsilon_transitions = defaultdict(list)

    # make a bunch of smaller edge dictionaries for graphviz formatting
    star_dict = {"N": [], "S": []}
    closure_dict = {"(": [], "|": []}

    operator_idx_stack = []
    for i, unit in enumerate(regex):
        left_paren_idx = i
        if unit == "(" or unit == "|":
            operator_idx_stack.append(i)
        elif unit == ")":
            or_idx_list = []
            while True:
                op_idx = operator_idx_stack.pop(-1)
                if regex[op_idx] == "|":
                    or_idx_list.append(op_idx)
                elif regex[op_idx] == "(":
                    left_paren_idx = op_idx
                    # left parenthesis edges
                    # [epsilon_transitions[left_paren_idx].append(or_idx + 1) for or_idx in or_idx_list]
                    [closure_dict["("].append((left_paren_idx, or_idx + 1)) for or_idx in or_idx_list]

                    # or edges
                    # [epsilon_transitions[or_idx].append(i) for or_idx in or_idx_list]
                    [closure_dict["|"].append((or_idx, i)) for or_idx in or_idx_list]

                    break

        if (i < (len(regex) - 1)) and regex[i + 1] == "*":
            star_dict["N"].append((left_paren_idx, i + 1))
            star_dict["S"].append((i + 1, left_paren_idx))

        if unit in "(*)" and i < len(regex) - 1:
            epsilon_transitions[i].append(i + 1)

    return epsilon_transitions, star_dict, closure_dict


def draw_nfa(gv_states, gv_edges, match_transitions, epsilon_transitions, star_dict, closure_dict):
    graph = gv.Digraph(comment="NFA")
    graph.attr(rankdir="LR", ranksep=".25")

    # add states
    [graph.node(str(tup[0]), str(tup[1])) for tup in gv_states]

    # add invisible edges for proper node ordering
    [graph.edge(str(tup[0]), str(tup[1]), style="invis", weight="10") for tup in gv_edges]

    # add match transition edges
    # convert from dict to list of tuples
    match_trans_list = []
    for key in match_transitions.keys():
        for val in match_transitions[key]:
            match_trans_list.append((key, val))

    [graph.edge(str(tup[0]) + ":e", str(tup[1]) + ":w", color="black", weight="10") for tup in match_trans_list]

    # add epsilon transition edges
    # convert from dict to list of tuples
    epsilon_trans_list = []
    for key in epsilon_transitions.keys():
        for val in epsilon_transitions[key]:
            epsilon_trans_list.append((key, val))
    [graph.edge(str(tup[0]) + ":e", str(tup[1]) + ":w", color="red", weight="10") for tup in epsilon_trans_list]

    # add * edges
    [graph.edge(str(tup[0]) + ":ne", str(tup[1]) + ":nw", color="red") for tup in star_dict["N"]]
    [graph.edge(str(tup[0]) + ":sw", str(tup[1]) + ":se", color="red") for tup in star_dict["S"]]

    # add | closure edges
    [graph.edge(str(tup[0]), str(tup[1]), color="red") for tup in closure_dict["("]]
    [graph.edge(str(tup[0]), str(tup[1]), color="red") for tup in closure_dict["|"]]

    graph.render("output/nfa", format="png").replace("\\", "/")


alphabet = "A B C D".split()
metacharacters = "( ) . * |".split()
test_re = "((A*B|AC)D)"
test_re = "(.*AB((C|D|E)F)*G)"

gv_states, gv_edges = get_formatting_states(test_re)
match_edge_dict = get_match_transitions(test_re)
epsilon_edge_dict, star_dict, closure_dict = get_epsilon_transitions(test_re)

print(f"match transitions: {match_edge_dict}")
print(f"epsilon transitions: {epsilon_edge_dict}")
draw_nfa(gv_states, gv_edges, match_edge_dict, epsilon_edge_dict, star_dict, closure_dict)
