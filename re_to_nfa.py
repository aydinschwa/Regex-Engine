import graphviz as gv


# build supplemental data structures necessary for visualization with gv
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
    match_transitions = []
    for i, unit in enumerate(regex):
        if i > 0 and regex[i - 1].isalpha():
            match_transitions.append((i - 1, i))
        else:
            pass
    return match_transitions


# build epsilon transition digraph
def get_epsilon_transitions(regex):
    epsilon_transitions = []
    operator_idx_stack = []
    for i, unit in enumerate(regex):
        if unit == "(" or unit == "|":
            operator_idx_stack.append(i)
        elif unit == ")":
            op_idx = operator_idx_stack.pop(-1)
            if regex[op_idx] == "|":
                left_paren_idx = operator_idx_stack.pop(-1)
                epsilon_transitions.append((left_paren_idx, op_idx + 1))
                epsilon_transitions.append((op_idx, i))
            else:
                left_paren_idx = op_idx
        if (i < (len(regex) - 1)) and regex[i + 1] == "*":
            epsilon_transitions.append((i, i + 1))
            epsilon_transitions.append((i + 1, i))

        if unit in "(*)" and i < len(regex) - 1:
            epsilon_transitions.append((i, i + 1))

    print(epsilon_transitions)
    return epsilon_transitions


def draw_nfa(gv_states, gv_edges, match_transitions, epsilon_transitions):
    graph = gv.Digraph(comment="NFA")
    graph.attr(rankdir="LR", ordering="in")

    # add states
    [graph.node(str(tup[0]), str(tup[1]), rank="same") for tup in gv_states]

    # add invisible edges for proper node ordering
    [graph.edge(str(tup[0]), str(tup[1]), style="invis") for tup in gv_edges]

    # add match transition edges
    [graph.edge(str(tup[0]), str(tup[1]), color="black", constraint="false", rank="max") for tup in match_transitions]

    # add epsilon transition edges
    [graph.edge(str(tup[0]), str(tup[1]), color="red", constraint="false") for tup in epsilon_transitions]

    # add invisible edges for proper node ordering
    [graph.edge(str(tup[0]), str(tup[1]), style="invis") for tup in gv_edges]

    graph.render('output/nfa').replace('\\', '/')


alphabet = "A B C D".split()
metacharacters = "( ) . * |".split()
test_re = "((A*B|AC(AD)D)"

gv_states, gv_edges = get_formatting_states(test_re)
match_edge_dict = get_match_transitions(test_re)
epsilon_edge_dict = get_epsilon_transitions(test_re)

draw_nfa(gv_states, gv_edges, match_edge_dict, epsilon_edge_dict)
