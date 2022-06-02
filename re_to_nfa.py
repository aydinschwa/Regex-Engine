from collections import defaultdict
from collections import deque


# splits brace into three tokens: left brace, middle text, right brace
def process_brace():
    pass


def process_bracket():
    pass


# split regex into tokens corresponding to individual nodes
def tokenize(regex):
    regex_symbols = deque(regex)
    regex_tokens = []
    while regex_symbols:
        symbol = regex_symbols.popleft()
        if symbol == "{":
            pass
        elif symbol == "[":
            regex_tokens.append(symbol)
            next_symbol = regex_symbols.popleft()
            bracket_text = []
            while next_symbol != "]":
                bracket_text.append(next_symbol)
                next_symbol = regex_symbols.popleft()
            bracket_text = "".join(bracket_text)
            regex_tokens.append(bracket_text)
            regex_tokens.append(next_symbol)
        else:
            regex_tokens.append(symbol)
    return regex_tokens


# build match transition digraph
def get_match_transitions(regex):
    # create dictionary that can support keys with multiple edges
    match_transitions = defaultdict(list)
    for i, unit in enumerate(regex):
        if i > 0 and regex not in metacharacters:
            match_transitions[i - 1].append(i)
    return match_transitions


# build epsilon transition digraph
def get_epsilon_transitions(regex):
    epsilon_transition_dict = defaultdict(list)

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
                    [epsilon_transition_dict[left_paren_idx].append(or_idx + 1) for or_idx in or_idx_list]

                    # or edges
                    [epsilon_transition_dict[or_idx].append(i) for or_idx in or_idx_list]

                    break

        if (i < (len(regex) - 1)) and regex[i + 1] == "*":
            epsilon_transition_dict[left_paren_idx].append(i + 1)
            epsilon_transition_dict[i + 1].append(left_paren_idx)

        if (i < (len(regex) - 1)) and regex[i + 1] == "+":
            epsilon_transition_dict[i + 1].append(left_paren_idx)

        if (i < (len(regex) - 1)) and regex[i + 1] == "?":
            epsilon_transition_dict[left_paren_idx].append(i + 2)

        if unit in metacharacters and i < len(regex):
            epsilon_transition_dict[i].append(i + 1)

    return epsilon_transition_dict


# find all states possible through epsilon transitions
def digraph_dfs(graph, node):
    reachable_states = []

    def find_states(graph, node):
        if node not in graph.keys():
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


def recognize(text, regex, match_transitions, epsilon_transitions, display=False):
    # get epsilon states before scanning first character
    epsilon_states = digraph_dfs(epsilon_transitions, 0)

    if display:
        print()
        print(f"States before scanning: {epsilon_states}")

    # check if nfa has reached an accepting state
    if len(regex) in epsilon_states:
        return True

    epsilon_chars = [regex[state] for state in epsilon_states]
    for i, letter in enumerate(text):
        # get epsilon transition states that match letter of input text
        matched_states = []
        [matched_states.append(state) for state, char_group in zip(epsilon_states, epsilon_chars) if
         letter in char_group or char_group == "."]

        # take match transition from matched state to next state
        next_states = []
        [next_states.extend(match_transitions[node]) for node in matched_states]

        # get next epsilon transitions
        epsilon_states = []
        [epsilon_states.extend(digraph_dfs(epsilon_transitions, node)) for node in next_states]

        if display:
            print()
            print(f"States before scanning: {epsilon_states}")
            print(f"Letter: {letter}")
            print(f"Matched States: {matched_states}")
            print(f"Match Transitions: {next_states}")
            print(f"Epsilon Transitions: {epsilon_states}", end=" ")
            print()

        # check if nfa has reached an accepting state
        if len(regex) in epsilon_states:
            return True

        epsilon_chars = [regex[state] for state in epsilon_states]

    return False


def search(text, regex, display=False):
    # regex must be wrapped in parentheses. If it's already wrapped, an extra layer won't hurt
    regex = "(" + regex + ")"
    regex = tokenize(regex)
    match_edge_dict = get_match_transitions(regex)
    epsilon_edge_dict = get_epsilon_transitions(regex)

    return recognize(text, regex, match_edge_dict, epsilon_edge_dict, display)


def run_test_cases():
    test_cases = [("Python", "Python", True),
                  ("Python", "python", False),
                  # testing single, multiway or
                  ("Python", "(P|p)ython", True),
                  ("python", "(P|p)ython", True),
                  ("cython", "(P|p|c)ython", True),
                  ("mython", "(P|p|c)ython", False),
                  # testing *
                  ("snake", "s*nake", True),
                  ("ssssnake", "s*nake", True),
                  ("nake", "s*nake", True),
                  ("shake", "s*nake", False),
                  ("Snake", "(Green)*Snake", True),
                  ("GreenSnake", "(Green)*Snake", True),
                  # testing ?
                  ("Smith", "(Doctor)?Smith", True),
                  ("DoctorSmith", "(Doctor)?Smith", True),
                  ("DoctorDoctorSmith", "(Doctor)?Smith", False),
                  # testing .
                  # doesn't work with metacharacters
                  ("red orange yellow green", ".*orange.*", True),
                  ("hi my name is XÆA-Xii", ".*X...Xii", True),
                  # testing +
                  ("No", "No+", True),
                  ("Nooooooo", "No+", True),
                  ("N", "No+", False),
                  ("NoNoNo", "(No)+", True),
                  # testing []
                  ("a", "[abcdefg]", True),
                  ("c", "[abcdefg]", True),
                  ("j", "[abcdefg]", False)
                  ]

    for text, regex, answer in test_cases:
        out = search(text, regex)
        if out != answer:
            print(f"Test case failed: {text}, {regex}")


if __name__ == "__main__":
    metacharacters = "( ) [ ] { } | ? * +".split()
    run_test_cases()
    # print(search("AAAB", "A*B", display=True))