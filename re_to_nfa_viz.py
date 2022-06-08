import graphviz as gv
from collections import defaultdict, deque
import os
import glob
from PIL import Image


class RegexEngine:

    def __init__(self, regex):
        # regex must be wrapped in parentheses. If it's already wrapped, an extra layer won't hurt
        self.regex = self._tokenize("(" + regex + ")")
        self.text = None
        self.metacharacters = "( ) | ? * + [ ] { }".split()

        # get formatting states/edges
        self.gv_states, self.gv_edges = self._get_formatting_states()

        # match transition edges
        self.match_transitions = self._get_match_transitions()

        # epsilon transition edges
        self.epsilon_transitions, \
            self.star_dict, \
            self.plus_dict, \
            self.closure_dict, \
            self.question_dict, \
            self.next_transition_dict = \
            self._get_epsilon_transitions()

        # clear output directory before creating new images
        files = glob.glob("output/*")
        [os.remove(file) for file in files]

    @staticmethod
    def _tokenize(regex):
        regex_symbols = deque(regex)
        regex_tokens = []

        # splits square bracket into three tokens: left brace, middle text, right brace
        def process_sq_bracket():
            regex_tokens.append(symbol)
            next_symbol = regex_symbols.popleft()
            bracket_text = []
            while next_symbol != "]":
                bracket_text.append(next_symbol)
                next_symbol = regex_symbols.popleft()
            bracket_text = "".join(bracket_text)
            regex_tokens.append(bracket_text)
            regex_tokens.append(next_symbol)

        # converts repetition counter to series of ? operators
        # needs to convert match groups like [] and ()
        def process_curl_bracket():
            repeat_token = regex_tokens[-1]

            if repeat_token == "]":
                repeat_token = ["[", regex_tokens[-2], "]"]

            elif repeat_token == ")":
                match_group = deque()
                for token in reversed(regex_tokens):
                    if token == "(":
                        match_group.appendleft(token)
                        break
                    match_group.appendleft(token)
                repeat_token = list(match_group)

            # otherwise, repeat token will just be a letter/number
            else:
                repeat_token = [repeat_token]

            # get number representing minimum number of repetitions
            min_reps = int(regex_symbols.popleft())
            regex_symbols.popleft()  # pop comma
            regex_symbols.popleft()  # pop space
            # get number representing max number of repetitions
            max_reps = int(regex_symbols.popleft())

            # adding text and ? tokens where necessary
            [regex_tokens.extend(repeat_token) for _ in range(min_reps - 1)]
            [regex_tokens.extend(repeat_token + ["?"]) for _ in range(max_reps - min_reps)]

            # remove the rightmost curly bracket
            regex_symbols.popleft()

        while regex_symbols:
            symbol = regex_symbols.popleft()
            if symbol == "{":
                process_curl_bracket()
            elif symbol == "[":
                process_sq_bracket()
            else:
                regex_tokens.append(symbol)

        return regex_tokens

    @staticmethod
    def _text_range(start, stop):
        return "".join([chr(num) for num in range(ord(start), ord(stop) + 1)])

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
            if i > 0 and self.regex[i - 1] not in self.metacharacters:
                match_transitions[i - 1] = i

        return match_transitions

    # build epsilon transition digraph
    # need to create mini dictionaries of specific edges for graphviz formatting
    def _get_epsilon_transitions(self):
        # make a bunch of smaller edge dictionaries for graphviz formatting
        star_dict = {"N": [], "S": []}
        question_dict = {"N": [], "S": []}
        closure_dict = {"(": [], "|": []}
        plus_dict = {"N": []}
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

            elif unit == "]":
                left_paren_idx = i - 2

            if (i < (len(self.regex) - 1)) and self.regex[i + 1] == "*":
                star_dict["N"].append((left_paren_idx, i + 1))
                star_dict["S"].append((i + 1, left_paren_idx))

            if (i < (len(self.regex) - 1)) and self.regex[i + 1] == "+":
                plus_dict["N"].append((i + 1, left_paren_idx))

            if (i < (len(self.regex) - 1)) and self.regex[i + 1] == "?":
                question_dict["N"].append((left_paren_idx, i + 2))

            if unit in self.metacharacters and i < len(self.regex):
                next_transition_dict["next"].append((i, i + 1))

        epsilon_transitions = self._combine_epsilon_edges(star_dict, plus_dict, closure_dict,
                                                          next_transition_dict, question_dict)

        return epsilon_transitions, star_dict, plus_dict, closure_dict, question_dict, next_transition_dict

    @staticmethod
    def _combine_epsilon_edges(*args):
        epsilon_transitions = defaultdict(list)
        for edge_dict in args:
            for coord_list in edge_dict.values():
                for tup in coord_list:
                    epsilon_transitions[tup[0]].append(tup[1])
        return epsilon_transitions

    def _draw_nfa(self, active_states, active_match_transitions, active_epsilon_transitions, letter_idx,
                  filename="nfa"):

        graph = gv.Digraph()

        if self.text:

            header_text = f'''<<table border="0" cellborder="1" cellspacing="0">
                              <tr>
                              <td colspan="{str(len(self.text) + 1)}"><FONT POINT-SIZE="16">Search Text</FONT></td>
                              </tr>
                              <tr>'''

            use_text = " " + self.text
            for i, letter in enumerate(use_text):
                color = "orange" if letter_idx == i else "white"
                letter = "   " if letter == " " else letter
                row_text = f'<td port="p{i}" bgcolor="{color}" colspan="1">{letter}</td>\n'
                header_text += row_text

            header_text += "</tr></table>>"

            graph.attr(ranksep=".25", rankdir="LR", labelloc="t", fontsize="22", shape="plain", label=header_text)

        else:
            graph.attr(ranksep=".25", rankdir="LR")

        # add states
        for idx, label in self.gv_states:
            if idx in active_states:
                graph.node(str(idx), str(label), color="green", style="filled", rank="sink")
            else:
                graph.node(str(idx), str(label))

        # add invisible edges for proper node ordering
        [graph.edge(str(tail), str(head), style="invis", weight="10") for tail, head in self.gv_edges]

        # add match transition edges
        for tail, head in self.match_transitions.items():
            if (tail, head) in active_match_transitions:
                graph.edge(str(tail) + ":e", str(head) + ":w", color="black", weight="10", style="bold",
                           arrowsize="1.33")
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

        # add + edges
        for tail, head in self.plus_dict["N"]:
            if (tail, head) in active_epsilon_transitions:
                graph.edge(str(tail) + ":nw", str(head) + ":ne", color="red", arrowsize="1.33", style="bold")
            else:
                graph.edge(str(tail) + ":nw", str(head) + ":ne", color="red")

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

        graph.render(f"output/{filename}", format="png")

    # find all states possible through epsilon transitions
    @staticmethod
    def _digraph_dfs(graph, node, draw=False):
        reachable_states = []
        epsilon_arrows = []

        def find_states(graph, node):

            # base case 1: node has already been visited
            if node in reachable_states:
                return

            # base case 2: node has no outgoing edges
            elif node not in graph.keys():
                reachable_states.append(node)
                return

            else:
                reachable_states.append(node)
                for state in graph[node]:
                    epsilon_arrows.append((node, state))
                    find_states(graph, state)

        find_states(graph, node)

        if draw:
            return epsilon_arrows
        else:
            return reachable_states

    def search(self, text, filename="nfa_state_"):
        self.text = text

        # get epsilon states before scanning first character
        epsilon_states = self._digraph_dfs(self.epsilon_transitions, 0)
        epsilon_arrows = self._digraph_dfs(self.epsilon_transitions, 0, draw=True)

        # graph_state will be the index for keeping pics in order
        graph_state = 0
        self._draw_nfa(epsilon_states, (), epsilon_arrows, 0, filename + str(graph_state).zfill(3))
        graph_state += 1

        # check if nfa has reached an accepting state
        if len(self.regex) in epsilon_states:
            self._draw_nfa([len(self.regex)], (), (), 0, filename + str(graph_state).zfill(3))
            graph_state += 1
            self._draw_nfa([len(self.regex)], (), (), 0, filename + str(graph_state).zfill(3))
            graph_state += 1
            self._draw_nfa([len(self.regex)], (), (), 0, filename + str(graph_state).zfill(3))
            graph_state += 1
            return True

        epsilon_chars = [self.regex[state] for state in epsilon_states]

        for i, letter in enumerate(text):
            # scan to next letter
            self._draw_nfa(epsilon_states, (), epsilon_arrows, i + 1, filename + str(graph_state).zfill(3))
            graph_state += 1

            # get epsilon transition states that match letter of input text
            matched_states = []
            for state, char_group in zip(epsilon_states, epsilon_chars):
                if letter in char_group or "." in char_group:
                    matched_states.append(state)
                elif "-" in char_group:
                    ranges = ""
                    for i, char in enumerate(char_group):
                        if char == "-":
                            ranges += self._text_range(char_group[i - 1], char_group[i + 1])
                    if letter in ranges:
                        matched_states.append(state)

            # take match transition from matched state to next state
            next_states = []
            [next_states.append(self.match_transitions[node]) for node in matched_states]

            # draw match transitions and their associated states
            match_arrows = list(zip(matched_states, next_states))
            self._draw_nfa(next_states, match_arrows, (), i + 1, filename + str(graph_state).zfill(3))
            graph_state += 1

            # get next epsilon transitions
            epsilon_states = []
            [epsilon_states.extend(self._digraph_dfs(self.epsilon_transitions, node)) for node in next_states]

            epsilon_arrows = []
            [epsilon_arrows.extend(self._digraph_dfs(self.epsilon_transitions, node, draw=True)) for node in
             next_states]

            self._draw_nfa(epsilon_states, (), epsilon_arrows, i + 1, filename + str(graph_state).zfill(3))
            graph_state += 1

            # check if nfa has reached an accepting state
            if len(self.regex) in epsilon_states:
                self._draw_nfa([len(self.regex)], (), (), i + 1, filename + str(graph_state).zfill(3))
                graph_state += 1
                self._draw_nfa([len(self.regex)], (), (), i + 1, filename + str(graph_state).zfill(3))
                graph_state += 1
                self._draw_nfa([len(self.regex)], (), (), i + 1, filename + str(graph_state).zfill(3))
                graph_state += 1
                return True

            epsilon_chars = [self.regex[state] for state in epsilon_states]

        return False

    @staticmethod
    # https://pythonprogramming.altervista.org/png-to-gif/
    def convert_to_gif():
        frames = []
        imgs = glob.glob("output/*.png")
        for i in sorted(imgs):
            new_frame = Image.open(i)
            frames.append(new_frame)

        # Save into a GIF file that loops forever
        frames[0].save('png_to_gif.gif', format='GIF',
                       append_images=frames[1:],
                       save_all=True,
                       duration=1000, loop=0)

    def draw_regex(self):
        self._draw_nfa((), (), (), 0)


if __name__ == "__main__":

    search = True

    # if you want the gif of the NFA scanning through the text, use the following syntax
    if search:
        # print(RegexEngine("S+NAKE").search("SSSSNAKE"))
        print(RegexEngine("[abc]+").search("abcabc"))
        # print(RegexEngine("[a-z]{2, 3}ch").search("ech"))

        # print(RegexEngine("(A*B|AC)D").search("AABD"))
        RegexEngine.convert_to_gif()

    # if you only want the NFA without searching any text, use the following syntax
    else:
        RegexEngine("[AB]{2, 3}").draw_regex()
        # RegexEngine(".*AB((C|D*E)F)*G").draw_regex()
