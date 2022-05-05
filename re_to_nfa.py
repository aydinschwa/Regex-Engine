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

    # add final accepting state
    states_list.append((len(regex), ""))
    invisible_transitions.append((len(regex) - 1, len(regex)))

    return states_list, invisible_transitions


# build match transition digraph
def get_match_transitions(regex):
    # create dictionary that can support keys with multiple edges
    match_transitions = defaultdict(list)
    for i, unit in enumerate(regex):
        if i > 0 and (regex[i - 1].isalpha() or regex[i - 1] == "."):
            match_transitions[i - 1].append(i)

    return match_transitions


# build epsilon transition digraph
# need to create mini dictionaries of specific edges for graphviz formatting
def get_epsilon_transitions(regex):
    # make a bunch of smaller edge dictionaries for graphviz formatting
    star_dict = {"N": [], "S": []}
    question_dict = {"N": [], "S": []}
    closure_dict = {"(": [], "|": []}
    next_transition_dict = {"next": []}

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
                    [closure_dict["("].append((left_paren_idx, or_idx + 1)) for or_idx in or_idx_list]

                    # or edges
                    [closure_dict["|"].append((or_idx, i)) for or_idx in or_idx_list]
                    break

        if (i < (len(regex) - 1)) and regex[i + 1] == "*":
            star_dict["N"].append((left_paren_idx, i + 1))
            star_dict["S"].append((i + 1, left_paren_idx))

        # TODO: might be wrong, need to write test cases
        if (i < (len(regex) - 1)) and regex[i + 1] == "?":
            question_dict["N"].append((left_paren_idx, i + 2))

        if unit in "(*)?" and i < len(regex):
            next_transition_dict["next"].append((i, i + 1))

    return star_dict, closure_dict, next_transition_dict, question_dict


def combine_epsilon_edges(*args):
    epsilon_transitions = defaultdict(list)
    for edge_dict in args:
        for coord_list in edge_dict.values():
            for tup in coord_list:
                epsilon_transitions[tup[0]].append(tup[1])
    return epsilon_transitions


def draw_nfa(gv_states, gv_edges, match_transitions, star_dict, closure_dict, next_transition_dict, question_dict):
    graph = gv.Digraph(comment="NFA")
    graph.attr(rankdir="LR", ranksep=".25")

    # add states
    [graph.node(str(tup[0]), str(tup[1])) for tup in gv_states]

    # add invisible edges for proper node ordering
    [graph.edge(str(tup[0]), str(tup[1]), style="invis", weight="10") for tup in gv_edges]

    # add match transition edges
    [graph.edge(str(k) + ":e", str(v[0]) + ":w", color="black", weight="10") for k, v in match_transitions.items()]

    # add next state epsilon transition edges
    [graph.edge(str(tup[0]) + ":e", str(tup[1]) + ":w", color="red", weight="10") for tup in next_transition_dict["next"]]

    # add * edges
    [graph.edge(str(tup[0]) + ":ne", str(tup[1]) + ":nw", color="red") for tup in star_dict["N"]]
    [graph.edge(str(tup[0]) + ":sw", str(tup[1]) + ":se", color="red") for tup in star_dict["S"]]

    # add ? edges
    [graph.edge(str(tup[0]), str(tup[1]), color="red") for tup in question_dict["N"]]
    [graph.edge(str(tup[0]) + ":sw", str(tup[1]) + ":se", color="red") for tup in question_dict["S"]]

    # add | closure edges
    [graph.edge(str(tup[0]), str(tup[1]), color="red") for tup in closure_dict["("]]
    [graph.edge(str(tup[0]), str(tup[1]), color="red") for tup in closure_dict["|"]]
    graph.render("output/nfa", format="png").replace("\\", "/")


# find all states possible through epsilon transitions
def digraph_dfs(graph, node):
    reachable_states = []

    def find_states(graph, node):
        if not graph[node]:
            reachable_states.append(node)
            return
        elif node in reachable_states:
            return
        else:
            reachable_states.append(node)
            for state in graph[node]:
                find_states(graph, state)

    find_states(graph, node)
    return reachable_states


def recognize(text, regex, match_transitions, epsilon_transitions):
    epsilon_states = digraph_dfs(epsilon_transitions, 0)
    epsilon_chars = [regex[state] for state in epsilon_states]
    for i, letter in enumerate(text):
        # get epsilon transition states that match letter of input text
        matched_states = []
        [matched_states.append(state) for state, char in zip(epsilon_states, epsilon_chars) if char == letter]

        # take match transition from matched state to next state
        next_states = []
        [next_states.extend(match_transitions[node]) for node in matched_states]

        # get next epsilon transitions
        epsilon_states = []
        [epsilon_states.extend(digraph_dfs(epsilon_transitions, node)) for node in next_states]

        if len(regex) in epsilon_states:
            return True

    return False


alphabet = "A B C D".split()
metacharacters = "( ) . * |".split()
test_re = "((A*B|AC)D)"
# test_re = "(.*AB((C|D|E)F)*G)"
# test_re = "((A.?)?)"
print(test_re)

gv_states, gv_edges = get_formatting_states(test_re)
match_edge_dict = get_match_transitions(test_re)
star_dict, closure_dict, next_transition_dict, question_dict = get_epsilon_transitions(test_re)
epsilon_edge_dict = combine_epsilon_edges(star_dict, closure_dict, next_transition_dict, question_dict)

print(f"match transitions: {match_edge_dict}")
print(f"epsilon transitions: {epsilon_edge_dict}")
draw_nfa(gv_states, gv_edges, match_edge_dict, star_dict, closure_dict, next_transition_dict, question_dict)

print(recognize("AABD", test_re, match_edge_dict, epsilon_edge_dict))
