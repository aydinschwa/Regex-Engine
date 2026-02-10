const METACHARS = new Set(["(", ")", "[", "]", "{", "}", "|", "?", "*", "+"]);

function tokenize(regex) {
  const symbols = Array.from(regex);
  const tokens = [];

  const collectRepeatToken = () => {
    const last = tokens[tokens.length - 1];
    if (last === "]") {
      return ["[", tokens[tokens.length - 2], "]"];
    }
    if (last === ")") {
      const group = [];
      for (let i = tokens.length - 1; i >= 0; i -= 1) {
        group.unshift(tokens[i]);
        if (tokens[i] === "(") {
          break;
        }
      }
      return group;
    }
    return [last];
  };

  for (let i = 0; i < symbols.length; i += 1) {
    const symbol = symbols[i];
    if (symbol === "[") {
      const bracket = [];
      i += 1;
      while (i < symbols.length && symbols[i] !== "]") {
        bracket.push(symbols[i]);
        i += 1;
      }
      tokens.push("[");
      tokens.push(bracket.join(""));
      tokens.push("]");
    } else if (symbol === "{") {
      const content = [];
      i += 1;
      while (i < symbols.length && symbols[i] !== "}") {
        content.push(symbols[i]);
        i += 1;
      }
      const range = content.join("").replace(/\s+/g, "");
      const [minText, maxText] = range.split(",");
      const minReps = Number.parseInt(minText, 10);
      const maxReps = Number.parseInt(maxText, 10);
      const repeatToken = collectRepeatToken();
      for (let j = 0; j < minReps - 1; j += 1) {
        tokens.push(...repeatToken);
      }
      for (let j = 0; j < maxReps - minReps; j += 1) {
        tokens.push(...repeatToken, "?");
      }
    } else {
      tokens.push(symbol);
    }
  }

  return tokens;
}

function textRange(start, stop) {
  const startCode = start.charCodeAt(0);
  const stopCode = stop.charCodeAt(0);
  let out = "";
  for (let i = startCode; i <= stopCode; i += 1) {
    out += String.fromCharCode(i);
  }
  return out;
}

function getFormattingStates(regexTokens) {
  const states = [];
  const edges = [];
  for (let i = 0; i < regexTokens.length; i += 1) {
    states.push([i, regexTokens[i]]);
    if (i > 0) {
      edges.push([i - 1, i]);
    }
  }
  states.push([regexTokens.length, ""]);
  edges.push([regexTokens.length - 1, regexTokens.length]);
  return { states, edges };
}

function getMatchTransitions(regexTokens) {
  const transitions = new Map();
  for (let i = 0; i < regexTokens.length; i += 1) {
    if (i > 0 && !METACHARS.has(regexTokens[i - 1])) {
      transitions.set(i - 1, i);
    }
  }
  return transitions;
}

function combineEpsilonEdges(...edgeMaps) {
  const epsilon = new Map();
  for (const edgeMap of edgeMaps) {
    Object.values(edgeMap).forEach((edges) => {
      edges.forEach(([tail, head]) => {
        if (!epsilon.has(tail)) {
          epsilon.set(tail, []);
        }
        epsilon.get(tail).push(head);
      });
    });
  }
  return epsilon;
}

function getEpsilonTransitions(regexTokens) {
  const star = { N: [], S: [] };
  const question = { N: [], S: [] };
  const closure = { "(": [], "|": [] };
  const plus = { N: [] };
  const next = { next: [] };

  const operatorStack = [];
  for (let i = 0; i < regexTokens.length; i += 1) {
    const unit = regexTokens[i];
    let leftParenIdx = i;

    if (unit === "(" || unit === "|") {
      operatorStack.push(i);
    } else if (unit === ")") {
      const orList = [];
      while (operatorStack.length) {
        const opIdx = operatorStack.pop();
        if (regexTokens[opIdx] === "|") {
          orList.push(opIdx);
        } else if (regexTokens[opIdx] === "(") {
          leftParenIdx = opIdx;
          orList.forEach((orIdx) => closure["("].push([leftParenIdx, orIdx + 1]));
          orList.forEach((orIdx) => closure["|"].push([orIdx, i]));
          break;
        }
      }
    } else if (unit === "]") {
      leftParenIdx = i - 2;
    }

    if (i < regexTokens.length - 1 && regexTokens[i + 1] === "*") {
      star.N.push([leftParenIdx, i + 1]);
      star.S.push([i + 1, leftParenIdx]);
    }

    if (i < regexTokens.length - 1 && regexTokens[i + 1] === "+") {
      plus.N.push([i + 1, leftParenIdx]);
    }

    if (i < regexTokens.length - 1 && regexTokens[i + 1] === "?") {
      question.N.push([leftParenIdx, i + 2]);
    }

    if (METACHARS.has(unit) && i < regexTokens.length) {
      next.next.push([i, i + 1]);
    }
  }

  const epsilon = combineEpsilonEdges(star, plus, closure, next, question);
  return { epsilon, star, plus, closure, question, next };
}

function digraphDfs(graph, start, draw = false) {
  const reachable = [];
  const edges = [];
  const visited = new Set();

  const walk = (node) => {
    if (visited.has(node)) return;
    visited.add(node);
    reachable.push(node);
    const neighbors = graph.get(node) || [];
    if (!neighbors.length) return;
    neighbors.forEach((next) => {
      edges.push([node, next]);
      walk(next);
    });
  };

  walk(start);
  return draw ? edges : reachable;
}

class RegexEngine {
  constructor(regex) {
    this.regex = tokenize(`(${regex})`);
    this.text = "";
    this.formatting = getFormattingStates(this.regex);
    this.matchTransitions = getMatchTransitions(this.regex);
    const epsilonData = getEpsilonTransitions(this.regex);
    this.epsilonTransitions = epsilonData.epsilon;
    this.edgeBuckets = epsilonData;
  }

  getEdgeSets() {
    const matchEdges = new Set();
    this.matchTransitions.forEach((head, tail) => {
      matchEdges.add(`${tail}->${head}`);
    });

    const epsilonEdges = new Set();
    Object.values(this.edgeBuckets).forEach((bucket) => {
      if (!bucket) return;
      Object.values(bucket).forEach((edges) => {
        if (!Array.isArray(edges)) return;
        edges.forEach(([tail, head]) => epsilonEdges.add(`${tail}->${head}`));
      });
    });

    return { matchEdges, epsilonEdges };
  }

  buildDot(activeStates = [], matchEdges = [], epsilonEdges = [], letterIndex = 0) {
    const { states, edges } = this.formatting;
    const activeStateSet = new Set(activeStates);
    const activeMatchSet = new Set(matchEdges.map(([a, b]) => `${a}->${b}`));
    const activeEpsSet = new Set(epsilonEdges.map(([a, b]) => `${a}->${b}`));
    const acceptingState = this.regex.length;

    let labelBlock = "";
    if (this.text) {
      const useText = ` ${this.text}`;
      const header = [];
      header.push('<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0">');
      header.push(`<TR><TD COLSPAN="${useText.length}"><FONT POINT-SIZE="16">Search Text</FONT></TD></TR>`);
      header.push("<TR>");
      for (let i = 0; i < useText.length; i += 1) {
        const letter = useText[i] === " " ? "&nbsp;&nbsp;" : useText[i];
        const color = letterIndex === i ? "#ffcf91" : "#ffffff";
        header.push(`<TD BGCOLOR="${color}">${letter}</TD>`);
      }
      header.push("</TR></TABLE>");
      labelBlock = `label=<${header.join("")}>;labelloc=t;`;
    }

    const lines = [
      "digraph {",
      "rankdir=LR;",
      "ranksep=0.4;",
      "nodesep=0.3;",
      "node [shape=circle, fontname=\"IBM Plex Mono\"];",
      "edge [fontname=\"IBM Plex Mono\"];",
      labelBlock,
    ];

    const escapeLabel = (value) =>
      String(value)
        .replace(/\\/g, "\\\\")
        .replace(/"/g, "\\\"");

    states.forEach(([idx, label]) => {
      const isActive = activeStateSet.has(idx);
      const isAccept = idx === acceptingState;
      const fill = isActive ? "#3bb273" : "#ffffff";
      const style = isActive ? "filled" : "";
      const shape = isAccept ? "doublecircle" : "circle";
      lines.push(
        `${idx} [label="${escapeLabel(label)}", fillcolor="${fill}", style="${style}", shape="${shape}"];`
      );
    });

    edges.forEach(([tail, head]) => {
      lines.push(`${tail} -> ${head} [style=invis, weight=10];`);
    });

    const drawEdge = (tail, head, color, isActive, tailPort = null, headPort = null) => {
      const bold = isActive ? ", penwidth=2.6" : "";
      const arrow = isActive ? ", arrowsize=1.2" : "";
      const from = tailPort ? `${tail}:${tailPort}` : `${tail}`;
      const to = headPort ? `${head}:${headPort}` : `${head}`;
      lines.push(`${from} -> ${to} [color="${color}"${bold}${arrow}];`);
    };

    this.matchTransitions.forEach((head, tail) => {
      drawEdge(tail, head, "#1b1f2a", activeMatchSet.has(`${tail}->${head}`), "e", "w");
    });

    this.edgeBuckets.next.next.forEach(([tail, head]) => {
      drawEdge(tail, head, "#ff7a1a", activeEpsSet.has(`${tail}->${head}`), "e", "w");
    });

    this.edgeBuckets.star.N.forEach(([tail, head]) => {
      drawEdge(tail, head, "#ff7a1a", activeEpsSet.has(`${tail}->${head}`), "ne", "nw");
    });

    this.edgeBuckets.star.S.forEach(([tail, head]) => {
      drawEdge(tail, head, "#ff7a1a", activeEpsSet.has(`${tail}->${head}`), "sw", "se");
    });

    this.edgeBuckets.plus.N.forEach(([tail, head]) => {
      drawEdge(tail, head, "#ff7a1a", activeEpsSet.has(`${tail}->${head}`), "nw", "ne");
    });

    this.edgeBuckets.question.N.forEach(([tail, head]) => {
      drawEdge(tail, head, "#ff7a1a", activeEpsSet.has(`${tail}->${head}`));
    });

    this.edgeBuckets.closure["("].forEach(([tail, head]) => {
      drawEdge(tail, head, "#ff7a1a", activeEpsSet.has(`${tail}->${head}`));
    });

    this.edgeBuckets.closure["|"].forEach(([tail, head]) => {
      drawEdge(tail, head, "#ff7a1a", activeEpsSet.has(`${tail}->${head}`));
    });

    lines.push("}");
    return lines.filter(Boolean).join("\n");
  }

  computeSteps(text) {
    this.text = text;
    const steps = [];
    const accepting = this.regex.length;

    const describe = (phase, context = {}) => {
      const { letter, matchedStatesCount, nextStatesCount, epsilonCount } = context;
      switch (phase) {
        case "initial":
          return "Step 1: From the start state, follow all epsilon transitions (no input consumed) to build the initial candidate-state set.";
        case "scan":
          return `Step 2: Scan the next input character (${letter}). Candidate states remain highlighted during the scan.`;
        case "match":
          return `Step 3: From candidate states, keep only those whose symbol matches the character, then follow their match transitions (matched: ${matchedStatesCount || 0}, new active states: ${nextStatesCount || 0}).`;
        case "epsilon":
          return `Step 4: From the new active states, take all epsilon transitions to form the next candidate-state set (size: ${epsilonCount || 0}).`;
        case "accept":
          return "Accept: The accepting state is reachable in the candidate set, so the regex matches at this position.";
        case "reject":
          return "Reject: Input is consumed without reaching the accepting state, so no match was found.";
        case "static":
          return "Static view of the NFA structure without running the simulation.";
        default:
          return "";
      }
    };

    let epsilonStates = digraphDfs(this.epsilonTransitions, 0);
    let epsilonEdges = digraphDfs(this.epsilonTransitions, 0, true);

    steps.push({
      activeStates: epsilonStates,
      matchEdges: [],
      epsilonEdges,
      letterIndex: 0,
      note: "Initial epsilon closure",
      explanation: describe("initial"),
    });

    if (epsilonStates.includes(accepting)) {
      steps.push({
        activeStates: [accepting],
        matchEdges: [],
        epsilonEdges: [],
        letterIndex: 0,
        note: "Accepted before scanning text",
        explanation: describe("accept"),
      });
      return steps;
    }

    let epsilonChars = epsilonStates.map((state) => this.regex[state]);

    for (let i = 0; i < text.length; i += 1) {
      const letter = text[i];
      steps.push({
        activeStates: epsilonStates,
        matchEdges: [],
        epsilonEdges,
        letterIndex: i + 1,
        note: `Scan '${letter}'`,
        explanation: describe("scan", { letter }),
      });

      const matchedStates = [];
      epsilonStates.forEach((state, idx) => {
        const charGroup = epsilonChars[idx];
        if (!charGroup) return;
        if (charGroup.includes(letter) || charGroup.includes(".")) {
          matchedStates.push(state);
        } else if (charGroup.includes("-")) {
          let ranges = "";
          for (let j = 0; j < charGroup.length; j += 1) {
            if (charGroup[j] === "-") {
              ranges += textRange(charGroup[j - 1], charGroup[j + 1]);
            }
          }
          if (ranges.includes(letter)) {
            matchedStates.push(state);
          }
        }
      });

      const nextStates = [];
      const matchEdges = [];
      matchedStates.forEach((state) => {
        const next = this.matchTransitions.get(state);
        if (next !== undefined) {
          nextStates.push(next);
          matchEdges.push([state, next]);
        }
      });

      steps.push({
        activeStates: nextStates,
        matchEdges,
        epsilonEdges: [],
        letterIndex: i + 1,
        note: "Match transitions",
        explanation: describe("match", {
          matchedStatesCount: matchedStates.length,
          nextStatesCount: nextStates.length,
        }),
      });

      const nextStateSet = new Set();
      const nextEpsilonEdges = [];
      nextStates.forEach((state) => {
        digraphDfs(this.epsilonTransitions, state).forEach((s) => nextStateSet.add(s));
        nextEpsilonEdges.push(...digraphDfs(this.epsilonTransitions, state, true));
      });

      epsilonStates = Array.from(nextStateSet);
      epsilonEdges = nextEpsilonEdges;
      steps.push({
        activeStates: epsilonStates,
        matchEdges: [],
        epsilonEdges,
        letterIndex: i + 1,
        note: "Epsilon closure",
        explanation: describe("epsilon", { epsilonCount: epsilonStates.length }),
      });

      if (epsilonStates.includes(accepting)) {
        steps.push({
          activeStates: [accepting],
          matchEdges: [],
          epsilonEdges: [],
          letterIndex: i + 1,
          note: "Accepted",
          explanation: describe("accept"),
        });
        return steps;
      }

      epsilonChars = epsilonStates.map((state) => this.regex[state]);
    }

    steps.push({
      activeStates: [],
      matchEdges: [],
      epsilonEdges: [],
      letterIndex: text.length,
      note: "Rejected",
      explanation: describe("reject"),
    });

    return steps;
  }
}

const viz = new Viz();
let currentEngine = null;
let steps = [];
let stepIndex = 0;
let isPlaying = false;
let playTimer = null;

const regexInput = document.getElementById("regexInput");
const textInput = document.getElementById("textInput");
const renderBtn = document.getElementById("renderBtn");
const runBtn = document.getElementById("runBtn");
const prevBtn = document.getElementById("prevBtn");
const nextBtn = document.getElementById("nextBtn");
const playBtn = document.getElementById("playBtn");
const stepSlider = document.getElementById("stepSlider");
const statusText = document.getElementById("statusText");
const graph = document.getElementById("graph");
const details = document.getElementById("details");
const explanationText = document.getElementById("explanationText");
const legendActiveCount = document.getElementById("legendActiveCount");
const legendMatchCount = document.getElementById("legendMatchCount");
const legendEpsilonCount = document.getElementById("legendEpsilonCount");

function applySvgClasses(svg, step) {
  const activeStateSet = new Set(step.activeStates);
  const activeMatchSet = new Set(step.matchEdges.map(([a, b]) => `${a}->${b}`));
  const activeEpsSet = new Set(step.epsilonEdges.map(([a, b]) => `${a}->${b}`));
  const { matchEdges, epsilonEdges } = currentEngine.getEdgeSets();
  const accepting = currentEngine.regex.length;
  const normalizeEdgeKey = (raw) => {
    const cleaned = raw.replace(/\s+/g, "");
    const parts = cleaned.split("->");
    if (parts.length !== 2) return cleaned;
    const tail = parts[0].split(":")[0];
    const head = parts[1].split(":")[0];
    return `${tail}->${head}`;
  };

  svg.querySelectorAll("g.node").forEach((node) => {
    const title = node.querySelector("title");
    if (!title) return;
    const idx = Number.parseInt(title.textContent, 10);
    node.classList.remove("active", "inactive", "accept");
    if (Number.isFinite(idx)) {
      if (idx === accepting) node.classList.add("accept");
      if (activeStateSet.has(idx)) {
        node.classList.add("active");
      } else {
        node.classList.add("inactive");
      }
    }
  });

  svg.querySelectorAll("g.edge").forEach((edge) => {
    const title = edge.querySelector("title");
    if (!title) return;
    const key = normalizeEdgeKey(title.textContent);
    edge.classList.remove("match", "epsilon", "active-edge");
    if (matchEdges.has(key)) edge.classList.add("match");
    if (epsilonEdges.has(key)) edge.classList.add("epsilon");
    if (activeMatchSet.has(key) || activeEpsSet.has(key)) {
      edge.classList.add("active-edge");
    }
  });
}

function setStatus(note, index) {
  statusText.textContent = `Step ${index + 1} of ${steps.length}. ${note}`;
}

function renderStep(index) {
  if (!steps.length) return;
  stepIndex = Math.min(Math.max(index, 0), steps.length - 1);
  const step = steps[stepIndex];
  const dot = currentEngine.buildDot(
    step.activeStates,
    step.matchEdges,
    step.epsilonEdges,
    step.letterIndex
  );

  viz.renderSVGElement(dot)
    .then((element) => {
      graph.innerHTML = "";
      graph.appendChild(element);
      applySvgClasses(element, step);
      setStatus(step.note, stepIndex);
      stepSlider.value = stepIndex;
      legendActiveCount.textContent = step.activeStates.length;
      legendMatchCount.textContent = step.matchEdges.length;
      legendEpsilonCount.textContent = step.epsilonEdges.length;
      explanationText.textContent = step.explanation || step.note;
      details.textContent = `Active states: ${step.activeStates.join(", ") || "none"}`;
    })
    .catch((err) => {
      graph.textContent = "Graphviz render failed.";
      console.error(err);
    });
}

function buildEngine() {
  const regex = regexInput.value.trim();
  const text = textInput.value;
  if (!regex) {
    statusText.textContent = "Enter a regex to render.";
    return;
  }
  currentEngine = new RegexEngine(regex);
  steps = currentEngine.computeSteps(text);
  stepSlider.max = Math.max(steps.length - 1, 0);
  renderStep(0);
}

function stopPlayback() {
  isPlaying = false;
  playBtn.textContent = "Play";
  if (playTimer) {
    clearInterval(playTimer);
    playTimer = null;
  }
}

renderBtn.addEventListener("click", () => {
  stopPlayback();
  const regex = regexInput.value.trim();
  if (!regex) {
    statusText.textContent = "Enter a regex to render.";
    return;
  }
  currentEngine = new RegexEngine(regex);
  currentEngine.text = textInput.value;
  steps = [{
    activeStates: [],
    matchEdges: [],
    epsilonEdges: [],
    letterIndex: 0,
    note: "Static NFA",
    explanation: "Static view of the NFA structure without running the simulation.",
  }];
  stepSlider.max = 0;
  renderStep(0);
});

runBtn.addEventListener("click", () => {
  stopPlayback();
  buildEngine();
});

prevBtn.addEventListener("click", () => {
  stopPlayback();
  renderStep(stepIndex - 1);
});

nextBtn.addEventListener("click", () => {
  stopPlayback();
  renderStep(stepIndex + 1);
});

stepSlider.addEventListener("input", (event) => {
  stopPlayback();
  renderStep(Number(event.target.value));
});

playBtn.addEventListener("click", () => {
  if (!steps.length) return;
  if (isPlaying) {
    stopPlayback();
    return;
  }
  isPlaying = true;
  playBtn.textContent = "Pause";
  playTimer = setInterval(() => {
    if (stepIndex >= steps.length - 1) {
      stopPlayback();
      return;
    }
    renderStep(stepIndex + 1);
  }, 900);
});

buildEngine();
