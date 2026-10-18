# -*- coding: utf-8 -*-
"""fix-agent 18.10 — stage ONLY the hunks of one file that contain a marker (never stash, never `git add` a file
that carries someone else's uncommitted work). usage: python3 stage_hunk.py <path> <marker>
Pipes `git diff -- <path>` through a hunk filter into `git apply --cached`."""
import subprocess, sys
path, marker = sys.argv[1], sys.argv[2]
diff = subprocess.run(["git", "diff", "--", path], capture_output=True, text=True, check=True).stdout
lines = diff.splitlines(keepends=True)
head, hunks, cur = [], [], None
for ln in lines:
    if ln.startswith("@@"):
        cur = [ln]; hunks.append(cur)
    elif cur is None:
        head.append(ln)
    else:
        cur.append(ln)
keep = [h for h in hunks if any(marker in x for x in h)]
if not keep:
    print("no hunk contains", marker); sys.exit(1)
patch = "".join(head) + "".join("".join(h) for h in keep)
r = subprocess.run(["git", "apply", "--cached", "--recount", "-"], input=patch, text=True, capture_output=True)
print("staged %d of %d hunks for %s rc=%d %s" % (len(keep), len(hunks), path, r.returncode, (r.stderr or "").strip()))
sys.exit(r.returncode)
