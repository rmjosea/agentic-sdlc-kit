#!/usr/bin/env bash
# Clean-context per-task Ralph execution loop for Agentic SDLC Kit (tasks.md).
#
# Usage:
#   bash .agents/tools/ralph-loop.sh <TASKS_FILE> [options]
#
# Options:
#   --repo <repo-id>       Execute only tasks tagged for <repo-id>.
#   --tasks <T01,T02>      Execute only the comma-separated task IDs.
#   --only-autonomous      Execute only [A] tasks; pause before [I] or [*].
#   --tool <cli>           AI CLI: devin (default), claude, codex, gemini.
#   --max-attempts <N>     Circuit breaker cap per task (default: 2).
#   --metrics-file <path>  JSONL telemetry output (default: .work/metrics.jsonl).
#   --dry-run              Print the execution schedule and model per task without running.
#   -h, --help             Show this help message.

set -euo pipefail

usage() {
  cat <<'EOF'
Usage: ralph-loop.sh <TASKS_FILE> [options]

Executes unchecked tasks (- [ ] **T0x**) from a canonical tasks.md file, running
one fresh, clean-context AI CLI session per task:
  - Changes model capability (low/med/high) directly in Bash (0 ACUs wasted on .env edits).
  - Pauses automatically when an interactive [I] task is reached.
  - Enforces a 2-attempt Circuit Breaker per task with structured failure diagnosis.
  - Appends execution telemetry to JSONL for empirical benchmarking.

Options:
  --repo <repo-id>       Filter tasks belonging to <repo-id>.
  --tasks <T01,T02>      Filter specific comma-separated task IDs.
  --only-autonomous      Run strictly [A] tasks; stop on [I] or [*].
  --tool <cli>           Agent CLI: devin (default), claude, codex, gemini.
  --max-attempts <N>     Max attempts per task before circuit breaker stops (default: 2).
  --metrics-file <path>  Path to JSONL telemetry log (default: .work/metrics.jsonl).
  --dry-run              Preview selected tasks and inferred model tier without running.
  -h, --help             Show this help text.
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" || "$#" -eq 0 ]]; then
  usage
  exit 0
fi

TASKS_FILE="$1"
shift

FILTER_REPO=""
FILTER_TASKS=""
ONLY_AUTONOMOUS=0
TOOL="${RALPH_TOOL:-devin}"
MAX_ATTEMPTS=2
METRICS_FILE=".work/metrics.jsonl"
DRY_RUN=0

while [[ "$#" -gt 0 ]]; do
  case "$1" in
    --repo)
      FILTER_REPO="${2:-}"
      shift 2
      ;;
    --tasks)
      FILTER_TASKS="${2:-}"
      shift 2
      ;;
    --only-autonomous)
      ONLY_AUTONOMOUS=1
      shift
      ;;
    --tool)
      TOOL="${2:-}"
      shift 2
      ;;
    --max-attempts)
      MAX_ATTEMPTS="${2:-2}"
      shift 2
      ;;
    --metrics-file)
      METRICS_FILE="${2:-.work/metrics.jsonl}"
      shift 2
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Error: unknown option '$1'" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ ! -f "$TASKS_FILE" ]]; then
  echo "Error: tasks file not found: $TASKS_FILE" >&2
  exit 2
fi

case "$TOOL" in
  devin|claude|codex|gemini) ;;
  *)
    echo "Error: --tool must be one of: devin, claude, codex, gemini" >&2
    exit 2
    ;;
esac

# Parse unchecked tasks from tasks.md using Python 3 stdlib (zero external deps).
PARSED_TASKS="$(python3 - "$TASKS_FILE" "$FILTER_REPO" "$FILTER_TASKS" <<'PY'
import re
import sys

tasks_path, filter_repo, filter_tasks = sys.argv[1], sys.argv[2], sys.argv[3]
wanted_ids = {t.strip() for t in filter_tasks.split(",") if t.strip()}
lines = open(tasks_path, encoding="utf-8").read().splitlines()

current_section_repo = ""
in_blocked = False
header_re = re.compile(r"^###\s+([A-Za-z0-9_.-]+)")
task_re = re.compile(r"^-\s+\[\s\]\s+\*\*(T[0-9]+)\*\*")
mod_re = re.compile(r"\[(A|I|\*)\]")
imp_re = re.compile(r"\b(accion|analisis|verificacion)\b")
repo_inline_re = re.compile(r"repo:\s*`?([A-Za-z0-9_.-]+)`?")
effort_re = re.compile(r"@effort:(low|med|high)")

for line in lines:
    if line.startswith("## Bloqueadas"):
        in_blocked = True
        continue
    if line.startswith("## ") and not line.startswith("## Bloqueadas"):
        in_blocked = False
    if in_blocked:
        continue
    m_head = header_re.match(line.strip())
    if m_head:
        current_section_repo = m_head.group(1)
        continue
    m_task = task_re.match(line)
    if not m_task:
        continue
    tid = m_task.group(1)
    m_mod = mod_re.search(line)
    m_imp = imp_re.search(line)
    modality = m_mod.group(1) if m_mod else "*"
    impact = m_imp.group(1) if m_imp else "accion"
    m_repo = repo_inline_re.search(line)
    repo = m_repo.group(1) if m_repo else (current_section_repo or "current")
    m_eff = effort_re.search(line)
    if m_eff:
        effort = m_eff.group(1)
    elif impact == "verificacion":
        effort = "high"
    else:
        effort = "med"
    if filter_repo and repo != filter_repo:
        continue
    if wanted_ids and tid not in wanted_ids:
        continue
    print(f"{tid}|{modality}|{impact}|{repo}|{effort}|{line.strip()}")
PY
)"

if [[ -z "$PARSED_TASKS" ]]; then
  echo "No matching unchecked tasks (- [ ]) found in $TASKS_FILE."
  exit 0
fi

model_for_tier() {
  local tool="$1"
  local tier="$2"
  case "$tool:$tier" in
    devin:low)  printf '%s' "${RALPH_DEVIN_MODEL_LOW:-claude-haiku-4.5}" ;;
    devin:med)  printf '%s' "${RALPH_DEVIN_MODEL_MED:-claude-sonnet-4.6}" ;;
    devin:high) printf '%s' "${RALPH_DEVIN_MODEL_HIGH:-claude-opus-4.8}" ;;
    claude:low)  printf '%s' "${RALPH_CLAUDE_MODEL_LOW:-haiku}" ;;
    claude:med)  printf '%s' "${RALPH_CLAUDE_MODEL_MED:-sonnet}" ;;
    claude:high) printf '%s' "${RALPH_CLAUDE_MODEL_HIGH:-opus}" ;;
    codex:low)  printf '%s' "${RALPH_CODEX_MODEL_LOW:-gpt-5.4-mini}" ;;
    codex:med)  printf '%s' "${RALPH_CODEX_MODEL_MED:-gpt-5.4}" ;;
    codex:high) printf '%s' "${RALPH_CODEX_MODEL_HIGH:-gpt-5.5}" ;;
    gemini:low)  printf '%s' "${RALPH_GEMINI_MODEL_LOW:-gemini-2.5-flash-lite}" ;;
    gemini:med)  printf '%s' "${RALPH_GEMINI_MODEL_MED:-gemini-2.5-flash}" ;;
    gemini:high) printf '%s' "${RALPH_GEMINI_MODEL_HIGH:-gemini-2.5-pro}" ;;
  esac
}

echo "=== Clean-Context Task Runner (tool=$TOOL, max_attempts=$MAX_ATTEMPTS, env_edits=0) ==="

while IFS='|' read -r tid modality impact repo effort raw_line; do
  [[ -z "$tid" ]] && continue
  model="$(model_for_tier "$TOOL" "$effort")"

  if [[ "$modality" == "I" ]]; then
    echo "[PAUSE] Task $tid ($repo) is marked [I] (Interactive). Pausing loop for human IDE execution."
    exit 0
  fi

  if [[ "$ONLY_AUTONOMOUS" -eq 1 && "$modality" != "A" ]]; then
    echo "[PAUSE] Task $tid ($repo) is marked [$modality] and --only-autonomous is set. Stopping."
    exit 0
  fi

  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "[DRY-RUN] Task $tid | repo=$repo | modality=[$modality] | impact=$impact | effort=$effort | model=$model"
    continue
  fi

  mkdir -p "$(dirname "$METRICS_FILE")"
  attempt=1
  task_done=0

  while [[ "$attempt" -le "$MAX_ATTEMPTS" ]]; do
    start_ts="$(date +%s)"
    prompt_tmp="$(mktemp "${TMPDIR:-/tmp}/kit-task-${tid}.XXXXXX")"
    cat >"$prompt_tmp" <<EOF
Read AGENTS.md and execute ONLY task $tid for repository $repo in $TASKS_FILE using the implement skill:
1. Write/locate the Verify test first and confirm it fails (RED).
2. Implement the minimal code reusing existing utilities/components (Zero Duplication).
3. Run the test + linter/typecheck/build until GREEN.
4. Run .agents/tools/check_companions.py if companions exist, and score against .agents/skills/implement/rubrics/.
5. If APROBADO: commit referencing $tid and mark - [x] **$tid** in $TASKS_FILE.
If it fails, leave it unchecked (- [ ]) and output a 5-line failure diagnosis (command, exit code, file:line, expected vs observed, root cause).
EOF

    echo "--- Running $tid (repo=$repo, attempt=$attempt/$MAX_ATTEMPTS, model=$model) ---"
    set +e
    case "$TOOL" in
      devin)
        devin --permission-mode dangerous --model "$model" --prompt-file "$prompt_tmp" -p
        ;;
      claude)
        claude --permission-mode bypassPermissions --model "$model" -p <"$prompt_tmp"
        ;;
      codex)
        codex exec --dangerously-bypass-approvals-and-sandbox -m "$model" - <"$prompt_tmp"
        ;;
      gemini)
        gemini --approval-mode=yolo --model "$model" <"$prompt_tmp"
        ;;
    esac
    rc=$?
    set -e
    rm -f "$prompt_tmp"
    end_ts="$(date +%s)"
    duration=$((end_ts - start_ts))

    if grep -Eq "^-\s+\[[xX]\]\s+\*\*${tid}\*\*" "$TASKS_FILE"; then
      printf '{"task_id":"%s","repo":"%s","modality":"%s","effort":"%s","model":"%s","attempt":%d,"status":"passed","duration_sec":%d,"env_edit_iterations":0}\n' \
        "$tid" "$repo" "$modality" "$effort" "$model" "$attempt" "$duration" >>"$METRICS_FILE"
      echo "[OK] Task $tid completed and checked off [x] on attempt $attempt."
      task_done=1
      break
    fi

    printf '{"task_id":"%s","repo":"%s","modality":"%s","effort":"%s","model":"%s","attempt":%d,"status":"failed","exit_code":%d,"duration_sec":%d,"env_edit_iterations":0}\n' \
      "$tid" "$repo" "$modality" "$effort" "$model" "$attempt" "$rc" "$duration" >>"$METRICS_FILE"
    echo "[WARN] Task $tid not checked off after attempt $attempt/$MAX_ATTEMPTS."
    attempt=$((attempt + 1))
    # Escalate model tier to high on retry
    model="$(model_for_tier "$TOOL" "high")"
  done

  if [[ "$task_done" -eq 0 ]]; then
    echo "[CIRCUIT BREAKER] Task $tid ($repo) failed $MAX_ATTEMPTS consecutive attempts. Stopping loop to preserve ACUs." >&2
    exit 1
  fi
done <<<"$PARSED_TASKS"

echo "=== All selected tasks completed ==="
