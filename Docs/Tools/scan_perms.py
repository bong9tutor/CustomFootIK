"""Scan recent transcripts for tool calls and propose allowlist patterns."""
import json
import re
import shlex
import sys
from collections import Counter
from pathlib import Path


# Bash subcommand-style commands: count "cmd subcmd"
SUBCOMMAND_COMMANDS = {"git", "gh", "docker", "kubectl", "npm", "yarn", "pnpm", "bun", "cargo", "go", "uv"}

# Commands Claude Code already auto-allows (any args). Skip these — no allowlist needed.
AUTO_ANY_ARGS = {
    "cal", "uptime", "cat", "head", "tail", "wc", "stat", "strings", "hexdump", "od", "nl", "id",
    "uname", "free", "df", "du", "locale", "groups", "nproc", "basename", "dirname", "realpath",
    "cut", "paste", "tr", "column", "tac", "rev", "fold", "expand", "unexpand", "fmt", "comm",
    "cmp", "numfmt", "readlink", "diff", "true", "false", "sleep", "which", "type", "expr",
    "test", "getconf", "seq", "tsort", "pr", "echo", "printf", "ls", "cd", "find",
}
AUTO_ZERO_ARGS = {"pwd", "whoami", "alias"}
# Auto with safe flags
AUTO_SAFE_FLAGS = {
    "xargs", "file", "sed", "sort", "man", "help", "netstat", "ps", "base64", "grep", "egrep",
    "fgrep", "sha256sum", "sha1sum", "md5sum", "tree", "date", "hostname", "info", "lsof",
    "pgrep", "tput", "ss", "fd", "fdfind", "aki", "rg", "jq", "uniq", "history", "arch",
    "ifconfig", "pyright",
}

# git read-only subcommands (auto-allowed)
GIT_READ = {
    "status", "log", "diff", "show", "blame", "branch", "tag", "remote", "ls-files", "ls-remote",
    "rev-parse", "describe", "reflog", "shortlog", "cat-file", "for-each-ref",
}
# gh read-only subcommands (auto-allowed)
GH_READ = {
    "pr", "issue", "run", "workflow", "repo", "release", "auth",
}  # These are top-level; we only count "gh sub" pair, then exclude if sub is one of these (since common subcommand forms like view/list/diff are read-only). To be safe, we approximate by skipping gh entirely if it falls under known-read forms.
# docker read-only subcommands (auto-allowed)
DOCKER_READ = {"ps", "images", "logs", "inspect"}

# Mutating top-level commands — always drop
MUTATING_COMMANDS = {
    "rm", "mv", "cp", "mkdir", "rmdir", "touch", "ln", "chmod", "chown", "kill", "killall",
    "shutdown", "reboot", "useradd", "userdel", "groupadd", "groupdel", "mount", "umount",
    "format", "dd", "fdisk", "parted", "mkfs", "fsck",
    "apt", "apt-get", "yum", "dnf", "pacman", "brew", "snap", "scoop", "choco", "winget", "pip",
    "pip3", "pipx", "gem", "cargo-install",
    "ssh", "scp", "sftp", "rsync", "curl", "wget",
    "sudo", "doas", "su",
    # Push/publish
    "publish",
}

# Tokens to STRIP from the front of a command before analysis (env vars, time, etc.)
PREFIX_STRIPPERS = {"sudo", "doas", "time", "timeout", "nohup", "env", "stdbuf", "nice", "ionice", "command", "exec"}

# Commands that are essentially "run arbitrary code" — never widen these
ARBITRARY_CODE = {
    "python", "python3", "py", "node", "deno", "ruby", "perl", "php", "lua", "java", "kotlin",
    "scala", "dotnet", "powershell", "pwsh", "bash", "sh", "zsh", "fish", "tcsh", "ksh",
    "eval", "exec",
    "npx", "bunx", "uvx", "pnpx",
}


def first_command_after_pipe(cmd: str) -> str:
    """Take the leading shell command, stripping env-var prefixes, sudo, pipes, &&, ||, ;."""
    # Break on the first pipeline/and/or/sep we encounter
    cmd = cmd.strip()
    # Strip leading parentheses/braces
    cmd = cmd.lstrip("({ ")
    # Cut at the first &&, ||, ;, |, or > newline that's at top level (naive: just split on these)
    # We only care about the leading command, so:
    for sep in ["\n", "&&", "||", ";", "|", " > ", " 2>", " >>", " &"]:
        if sep in cmd:
            cmd = cmd.split(sep, 1)[0]
    cmd = cmd.strip()
    return cmd


def parse_leading_token(cmd: str):
    """Return (cmd, subcmd_or_None, leading_args_or_str)."""
    try:
        tokens = shlex.split(cmd, posix=True)
    except ValueError:
        # shlex can fail on unbalanced quotes; fall back to whitespace split
        tokens = cmd.split()

    # Strip env-var prefixes (VAR=value)
    while tokens and re.match(r"^[A-Z_][A-Z0-9_]*=", tokens[0]):
        tokens.pop(0)

    # Strip leading wrappers
    while tokens and tokens[0] in PREFIX_STRIPPERS:
        tokens.pop(0)
        # `timeout 30s cmd` — drop the duration arg
        if tokens and re.match(r"^[0-9]+[smhd]?$", tokens[0]):
            tokens.pop(0)

    if not tokens:
        return None, None, None

    head = tokens[0]
    # Strip path: /usr/bin/git → git
    head_basename = Path(head).name
    head_basename = head_basename.lower()

    sub = tokens[1] if len(tokens) > 1 else None
    return head_basename, sub, tokens


def categorize(cmd_text: str):
    """Return either ("Bash", pattern, reason) for a recommendable entry, or (None, None, drop_reason)."""
    head_full = first_command_after_pipe(cmd_text)
    head, sub, tokens = parse_leading_token(head_full)
    if not head:
        return None, None, "empty"

    # Arbitrary code execution
    if head in ARBITRARY_CODE:
        return None, None, f"arbitrary-code:{head}"

    # Mutating commands
    if head in MUTATING_COMMANDS:
        return None, None, f"mutating:{head}"

    # Auto-allowed: any args
    if head in AUTO_ANY_ARGS:
        return None, None, f"auto-any:{head}"
    # Auto-allowed: zero args
    if head in AUTO_ZERO_ARGS:
        return None, None, f"auto-zero:{head}"
    # Auto-allowed: safe-flags
    if head in AUTO_SAFE_FLAGS:
        return None, None, f"auto-safe:{head}"

    # git, gh, docker — drop if it's a read-only subcommand (auto-allowed)
    if head == "git":
        if sub and sub.lower() in GIT_READ:
            return None, None, f"auto-git:{sub}"
        # config --get is read-only
        if sub == "config" and tokens and len(tokens) > 2 and tokens[2] == "--get":
            return None, None, "auto-git:config-get"
        # Other git: mutating (commit, push, pull, fetch, checkout, etc.)
        return None, None, f"git-mutating:{sub}"

    if head == "gh":
        # gh's read-only verbs are wide; just drop ALL gh — auto-allowed for view/list/diff
        # and the user shouldn't allow `gh pr create` etc. anyway.
        return None, None, f"gh-handled-via-readonly:{sub}"

    if head == "docker":
        if sub in DOCKER_READ:
            return None, None, f"auto-docker:{sub}"
        return None, None, f"docker-other:{sub}"

    # Now we have a non-auto, non-mutating, non-code command. Decide pattern shape.
    if head in SUBCOMMAND_COMMANDS:
        if sub:
            return "Bash", f"{head} {sub} *", f"subcommand-form"
        return "Bash", head, f"bare"

    # Otherwise use single-command pattern
    return "Bash", f"{head} *", f"general"


def scan_file(path: Path) -> Counter:
    counter = Counter()
    try:
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            msg = obj.get("message")
            if not msg:
                continue
            if msg.get("role") != "assistant":
                continue
            for block in msg.get("content", []) or []:
                if not isinstance(block, dict):
                    continue
                if block.get("type") != "tool_use":
                    continue
                tool_name = block.get("name", "")
                inp = block.get("input", {}) or {}
                if tool_name == "Bash":
                    cmd = inp.get("command", "")
                    if not cmd:
                        continue
                    kind, pattern, reason = categorize(cmd)
                    if pattern:
                        counter[("Bash", pattern, reason)] += 1
                    else:
                        counter[("DROP", reason or "?", "")] += 1
                elif tool_name == "PowerShell":
                    # PowerShell tool is its own thing — total count + per-leading-cmdlet
                    cmd = inp.get("command", "") or ""
                    counter[("PS-total", "ALL", "powershell-tool")] += 1
                    # Get leading cmdlet/exe
                    m = re.match(r"\s*([A-Za-z][\w\-\.]*)", cmd)
                    if m:
                        head = m.group(1).lower()
                        counter[("PS-head", head, "")] += 1
                elif tool_name.startswith("mcp__"):
                    # MCP read-only heuristic: name contains read/get/list/search/view/describe/discover/status/info/info
                    low = tool_name.lower()
                    if any(k in low for k in ("read", "get", "list", "search", "view", "describe", "discover", "status", "info", "query", "fetch", "preview", "guide", "test_database_connection", "monolith_status")):
                        counter[("MCP", tool_name, "read-ish")] += 1
                    else:
                        counter[("MCP-MUT", tool_name, "mutating-ish")] += 1
                else:
                    # Other tools (Edit, Write, etc.) don't go in allowlist
                    pass
    except Exception as e:
        print(f"!! err {path}: {e}", file=sys.stderr)
    return counter


def main():
    proj_root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(r"C:\Users\bong9\.claude\projects")
    files = sorted(proj_root.rglob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)[:50]
    print(f"Scanning {len(files)} most-recent transcripts...", file=sys.stderr)

    total = Counter()
    for f in files:
        total.update(scan_file(f))

    # Split
    keep_bash = Counter()
    keep_mcp = Counter()
    drops = Counter()
    mcp_mut = Counter()
    ps_total = 0
    ps_heads = Counter()
    for (kind, pattern, reason), count in total.items():
        if kind == "Bash":
            keep_bash[pattern] += count
        elif kind == "MCP":
            keep_mcp[pattern] += count
        elif kind == "MCP-MUT":
            mcp_mut[pattern] += count
        elif kind == "PS-total":
            ps_total += count
        elif kind == "PS-head":
            ps_heads[pattern] += count
        else:
            drops[reason] += count

    print(f"\n=== POWERSHELL TOOL — total calls: {ps_total} ===")
    for head, cnt in ps_heads.most_common(30):
        print(f"  {cnt:5d}  PowerShell starts with: {head}")

    print("\n=== TOP KEPT BASH PATTERNS ===")
    for pat, cnt in keep_bash.most_common(40):
        print(f"  {cnt:5d}  Bash({pat})")

    print("\n=== TOP KEPT MCP TOOLS ===")
    for name, cnt in keep_mcp.most_common(40):
        print(f"  {cnt:5d}  {name}")

    print("\n=== MCP TOOLS THAT LOOK MUTATING (skipped) ===")
    for name, cnt in mcp_mut.most_common(30):
        print(f"  {cnt:5d}  {name}")

    print("\n=== TOP DROP REASONS ===")
    for reason, cnt in drops.most_common(30):
        print(f"  {cnt:5d}  {reason}")


if __name__ == "__main__":
    main()
