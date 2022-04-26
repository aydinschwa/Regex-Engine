import graphviz as gv


# build supplemental data structures necessary for visualization with gv
def get_formatting_states(regex):
    states_list = []
    invisible_transitions = []

    for i, unit in enumerate(regex):
        states_list.append((str(i), unit))
        if i > 0:
            invisible_transitions.append((str(i - 1), str(i)))

    return states_list, invisible_transitions


# build match transition digraph
def get_match_transitions(regex):
    match_transitions = {}
    for i, unit in enumerate(regex):
        if i > 0 and regex[i - 1].isalpha():
            match_transitions[str(i - 1)] = str(i)
        else:
            pass
    return match_transitions


# build epsilon transition digraph
def get_epsilon_transitions(regex):
    epsilon_transitions = {}
    for i, unit in enumerate(regex):
        if i > 0 and unit in "()":
            epsilon_transitions[str(i - 1)] = str(i)
        # TODO: implement single-character and expression closures
        elif unit == "*":
            epsilon_transitions[str(i - 1)] = str(i)
            epsilon_transitions[str(i)] = str(i - 1)

    return epsilon_transitions


def draw_nfa(gv_states, gv_edges, match_transitions, epsilon_transitions):
    graph = gv.Digraph(comment="NFA")
    graph.attr(rankdir="LR")

    # add states
    [graph.node(tup[0], tup[1]) for tup in gv_states]

    # add invisible edges for proper node ordering
    [graph.edge(tup[0], tup[1], style="invis") for tup in gv_edges]

    # add match transition edges
    edges = [(key, value) for key, value in match_transitions.items()]
    graph.edges(edges)

    # add epsilon transition edges
    edges = [(key, value) for key, value in epsilon_transitions.items()]
    [graph.edge(tup[0], tup[1], color="red") for tup in edges]

    # add invisible edges for proper node ordering
    [graph.edge(tup[0], tup[1], style="invis") for tup in gv_edges]

    graph.render('output/nfa').replace('\\', '/')


alphabet = "A B C D".split()
metacharacters = "( ) . * |".split()
test_re = "((A*B|AC)D)"

gv_states, gv_edges = get_formatting_states(test_re)
match_edge_dict = get_match_transitions(test_re)
epsilon_edge_dict = get_epsilon_transitions(test_re)

draw_nfa(gv_states, gv_edges, match_edge_dict, epsilon_edge_dict)
