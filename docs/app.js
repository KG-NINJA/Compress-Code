const generateBtn = document.getElementById("generateBtn");
const outputArea = document.getElementById("outputArea");
const sourceInput = document.getElementById("sourceInput");
const explainToggle = document.getElementById("explainToggle");
const diffToggle = document.getElementById("diffToggle");

const sample = {
  summary: "Mock summary (surface cues only): 14 lines, 2 functions, no execution performed.",
  proposals: [
    {
      title: "Trim leading/trailing blank lines",
      code: "def greet(name):\n    return f\"Hello {name}\"\n\n\ndef main():\n    print(greet(\"world\"))\n",
      explanation:
        "Removes empty lines at file boundaries only. Execution semantics remain unchanged.",
      diff:
        "--- original\n+++ proposal-1\n@@\n-\n def greet(name):\n     return f\"Hello {name}\"\n@@\n-\n def main():\n     print(greet(\"world\"))\n-\n",
    },
    {
      title: "Collapse consecutive blank lines",
      code: "def greet(name):\n    return f\"Hello {name}\"\n\n\ndef main():\n    print(greet(\"world\"))\n",
      explanation:
        "Converts multiple blank lines to a single blank line. No control flow changes.",
      diff:
        "--- original\n+++ proposal-2\n@@\n-\n-\n+\n def main():\n     print(greet(\"world\"))\n",
    },
    {
      title: "Remove redundant docstring (if unused)",
      code:
        "def greet(name):\n    \"\"\"Return greeting for the provided name.\"\"\"\n    return f\"Hello {name}\"\n\n\ndef main():\n    print(greet(\"world\"))\n",
      explanation:
        "Docstrings can be removed when not used for runtime behavior. Only do this if no tooling relies on them.",
      diff:
        "--- original\n+++ proposal-3\n@@\n-    \"\"\"Return greeting for the provided name.\"\"\"\n     return f\"Hello {name}\"\n",
    },
  ],
};

function detectLanguage(text) {
  if (text.includes("def ") || text.includes("import ")) return "Python";
  if (text.includes("function ") || text.includes("const ")) return "JavaScript";
  return "Unknown";
}

function buildSummary(text) {
  const lines = text.split("\n").length;
  const lang = detectLanguage(text);
  return `Mock summary (surface cues only): ${lines} lines, language guess: ${lang}.`;
}

function renderOutput() {
  const explain = explainToggle.checked;
  const showDiff = diffToggle.checked;
  const mode = document.querySelector("input[name='mode']:checked").value;
  const summaryText = sourceInput.value.trim()
    ? buildSummary(sourceInput.value)
    : sample.summary;

  const header = `Mode: ${mode}. Example output only; no code is executed or rewritten.`;

  const blocks = [];
  blocks.push(`
    <div class="output-block">
      <h3>Code Summary</h3>
      <p>${summaryText}</p>
      <p class="muted">${header}</p>
    </div>
  `);

  blocks.push(`
    <div class="output-block">
      <h3>Compression Proposals</h3>
      ${sample.proposals
        .map(
          (proposal, idx) => `
            <div class="proposal">
              <p><strong>[${idx + 1}] ${proposal.title}</strong></p>
              ${
                explain
                  ? `<p class="muted">${proposal.explanation}</p>`
                  : ""
              }
              <div class="code-block">${escapeHtml(proposal.code)}</div>
              ${
                showDiff
                  ? `<div class="code-block">${escapeHtml(proposal.diff)}</div>`
                  : ""
              }
            </div>
          `
        )
        .join("")}
    </div>
  `);

  blocks.push(`
    <div class="output-block">
      <h3>Explanation</h3>
      <p>
        Codex explores compression candidates. Humans evaluate and decide. Output is proposals only.
      </p>
      <p class="muted">
        This demo does not perform real optimization or refactoring. The CLI is the execution layer.
      </p>
    </div>
  `);

  outputArea.innerHTML = blocks.join("");
}

function escapeHtml(text) {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

generateBtn.addEventListener("click", renderOutput);
