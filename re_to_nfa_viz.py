import graphviz as gv
from collections import defaultdict


class RegexEngine:

    def __init__(self, regex):
        # regex must be wrapped in parentheses. If it's already wrapped, an extra layer won't hurt
        self.regex = "(" + regex + ")"
        self.metacharacters = "( ) | ? * .".split()

        # get formatting states/edges
        self.gv_states, self.gv_edges = self._get_formatting_states()

        # match transition edges
        self.match_transitions = self._get_match_transitions()

        # epsilon transition edges
        self.epsilon_transitions, self.star_dict, self.closure_dict, self.question_dict, self.next_transition_dict = \
            self._get_epsilon_transitions()

        self._draw_nfa((), (), ())

    def _get_formatting_states(self):
        states_list = []
        invisible_transitions = []

        for i, unit in enumerate(self.regex):
            states_list.append((i, unit))
            if i > 0:
                invisible_transitions.append((i - 1, i))

        # add final accepting state
        states_list.append((len(self.regex), ""))
        invisible_transitions.append((len(self.regex) - 1, len(self.regex)))

        return states_list, invisible_transitions

    # build match transition digraph
    def _get_match_transitions(self):
        # create dictionary that can support keys with multiple edges
        match_transitions = {}
        for i, unit in enumerate(self.regex):
            if i > 0 and (self.regex[i - 1].isalpha() or self.regex[i - 1] == "." or self.regex[i - 1] == " "):
                match_transitions[i - 1] = i

        return match_transitions

    # build epsilon transition digraph
    # need to create mini dictionaries of specific edges for graphviz formatting
    def _get_epsilon_transitions(self):
        # make a bunch of smaller edge dictionaries for graphviz formatting
        star_dict = {"N": [], "S": []}
        question_dict = {"N": [], "S": []}
        closure_dict = {"(": [], "|": []}
        next_transition_dict = {"next": []}

        operator_idx_stack = []
        for i, unit in enumerate(self.regex):
            left_paren_idx = i
            if unit == "(" or unit == "|":
                operator_idx_stack.append(i)
            elif unit == ")":
                or_idx_list = []
                while True:
                    op_idx = operator_idx_stack.pop(-1)
                    if self.regex[op_idx] == "|":
                        or_idx_list.append(op_idx)
                    elif self.regex[op_idx] == "(":
                        left_paren_idx = op_idx
                        # left parenthesis edges
                        [closure_dict["("].append((left_paren_idx, or_idx + 1)) for or_idx in or_idx_list]

                        # or edges
                        [closure_dict["|"].append((or_idx, i)) for or_idx in or_idx_list]
                        break

            if (i < (len(self.regex) - 1)) and self.regex[i + 1] == "*":
                star_dict["N"].append((left_paren_idx, i + 1))
                star_dict["S"].append((i + 1, left_paren_idx))

            if (i < (len(self.regex) - 1)) and self.regex[i + 1] == "?":
                question_dict["N"].append((left_paren_idx, i + 2))

            if unit in "(*)?" and i < len(self.regex):
                next_transition_dict["next"].append((i, i + 1))

        epsilon_transitions = self._combine_epsilon_edges(star_dict, closure_dict, next_transition_dict, question_dict)

        return epsilon_transitions, star_dict, closure_dict, question_dict, next_transition_dict

    @staticmethod
    def _combine_epsilon_edges(*args):
        epsilon_transitions = defaultdict(list)
        for edge_dict in args:
            for coord_list in edge_dict.values():
                for tup in coord_list:
                    epsilon_transitions[tup[0]].append(tup[1])
        return epsilon_transitions

    def _draw_nfa(self, active_states, active_match_transitions, active_epsilon_transitions):

        graph = gv.Digraph(comment="NFA")
        graph.attr(rankdir="LR", ranksep=".25")

        # add states
        for idx, label in self.gv_states:
            if idx in active_states:
                graph.node(str(idx), str(label), color="black", style="bold")
            else:
                graph.node(str(idx), str(label))

        # add invisible edges for proper node ordering
        [graph.edge(str(tail), str(head), style="invis", weight="10") for tail, head in self.gv_edges]

        # add match transition edges
        for tail, head in self.match_transitions.items():
            if (tail, head) in active_match_transitions:
                graph.edge(str(tail) + ":e", str(head) + ":w", color="black", weight="10", style="bold")
            else:
                graph.edge(str(tail) + ":e", str(head) + ":w", color="black", weight="10")

        # add next state epsilon transition edges
        for tail, head in self.next_transition_dict["next"]:
            if (tail, head) in active_epsilon_transitions:
                graph.edge(str(tail) + ":e", str(head) + ":w", color="red", weight="10", arrowsize="1.33", style="bold")
            else:
                graph.edge(str(tail) + ":e", str(head) + ":w", color="red", weight="10")

        # add * edges
        for tail, head in self.star_dict["N"]:
            if (tail, head) in active_epsilon_transitions:
                graph.edge(str(tail) + ":ne", str(head) + ":nw", color="red", arrowsize="1.33", style="bold")
            else:
                graph.edge(str(tail) + ":ne", str(head) + ":nw", color="red")

        for tail, head in self.star_dict["S"]:
            if (tail, head) in active_epsilon_transitions:
                graph.edge(str(tail) + ":sw", str(head) + ":se", color="red", arrowsize="1.33", style="bold")
            else:
                graph.edge(str(tail) + ":sw", str(head) + ":se", color="red")

        # add ? edges
        for tail, head in self.question_dict["N"]:
            if (tail, head) in active_epsilon_transitions:
                graph.edge(str(tail), str(head), color="red", arrowsize="1.33", style="bold")
            else:
                graph.edge(str(tail), str(head), color="red")

        for tail, head in self.question_dict["S"]:
            if (tail, head) in active_epsilon_transitions:
                graph.edge(str(tail) + ":sw", str(head) + ":se", color="red", arrowsize="1.33", style="bold")
            else:
                graph.edge(str(tail) + ":sw", str(head) + ":se", color="red")

        # add | closure edges
        for tail, head in self.closure_dict["("]:
            if (tail, head) in active_epsilon_transitions:
                graph.edge(str(tail), str(head), color="red", arrowsize="1.33", style="bold")
            else:
                graph.edge(str(tail), str(head), color="red")

        for tail, head in self.closure_dict["|"]:
            if (tail, head) in active_epsilon_transitions:
                graph.edge(str(tail), str(head), color="red", arrowsize="1.33", style="bold")
            else:
                graph.edge(str(tail), str(head), color="red")

        graph.render("output/nfa", format="png")

    # find all states possible through epsilon transitions
    @staticmethod
    def _digraph_dfs(graph, node):
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

    def _recognize(self, text, display=False):
        # get epsilon states before scanning first character
        epsilon_states = self._digraph_dfs(self.epsilon_transitions, 0)
        epsilon_chars = [self.regex[state] for state in epsilon_states]
        for i, letter in enumerate(text):
            # get epsilon transition states that match letter of input text
            matched_states = []
            [matched_states.append(state) for state, char in zip(epsilon_states, epsilon_chars) if
             char == letter or char == "."]

            # take match transition from matched state to next state
            next_states = []
            [next_states.append(self.match_transitions[node]) for node in matched_states]

            # get next epsilon transitions
            epsilon_states = []
            [epsilon_states.extend(self._digraph_dfs(self.epsilon_transitions, node)) for node in next_states]

            # check if nfa has reached an accepting state
            if len(self.regex) in epsilon_states:
                return True

            epsilon_chars = [self.regex[state] for state in epsilon_states]

            if display:
                print(f"States before scanning: {epsilon_states}")
                print(f"Letter: {letter}")
                print(f"Matched States: {matched_states}")
                print(f"Match Transitions: {next_states}")
                print(f"Epsilon Transitions: {epsilon_states}", end=" ")
                print()

        return False

    def search(self, text, display=False):

        if display:
            self._draw_nfa((), (), ())

        return self._recognize(text, display)


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
                  ("hi my name is XÆA-Xii", ".*X...Xii", True)]

    for text, regex, answer in test_cases:
        out = RegexEngine(regex).search(text, display=True)
        if out != answer:
            print(f"Test case failed: {text}, {regex}")


if __name__ == "__main__":
    RegexEngine("(A|B|C)*AS")
