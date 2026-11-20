"""Patch the overview post queue section to add full controls."""
import pathlib

path = pathlib.Path(r"C:\peakcut\web\index.html")
src = path.read_text(encoding="utf-8")

# Target: the overview post queue table rows
OLD = r"""      ${o.posts.length ? `<div class="scroll"><table class="stack"><tr><th>When</th><th>Clip</th><th>Creator</th><th>Account</th><th class="num">Views</th><th></th></tr>
      ${o.posts.map(p => `<tr><td data-l="Status">${pst(p)}</td><td data-l="Clip" class="c-main">${p.url ? `<a class="lnk" href="${esc(p.url)}" target="_blank" rel="noopener">${esc(p.title)}</a>` : esc(p.title)}${p.error ? `<div class="err" style="margin:2px 0 0">${esc(p.error)}</div>` : ""}</td><td data-l="Creator">${esc(p.creator_name || "None")}</td><td data-l="Account">${esc(p.account_name)}</td><td data-l="Views" class="num">${p.views ?? "–"}</td>
        <td class="c-act" style="text-align:right">${p.status === "scheduled" ? `<button class="btn sm" data-act="pnow" data-id="${p.id}" title="Post now">${ic("send")} Now</button>` : p.status === "failed" ? `<button class="btn sm" data-act="pretry" data-id="${p.id}">Retry</button>` : ""}</td></tr>`).join("")}</table></div>`
      : `<p class="help">Nothing queued or posted yet.</p>`}</div>`);"""

NEW = r"""      ${o.posts.length ? `<div class="scroll"><table class="stack">
        <tr><th>Status</th><th>Clip</th><th>Creator</th><th>Account</th><th>Visibility</th><th class="num">Views</th><th style="min-width:230px;text-align:right">Actions</th></tr>
        ${o.posts.map(p => {
          const isPaused = !!p.paused;
          const statusTxt = isPaused && p.status==="scheduled" ? "\u23F8 Paused" : ({"scheduled":"\uD83D\uDD50 Queued","posting":"\u2B06\uFE0F Uploading","posted":"\u2705 Posted","failed":"\u274C Failed","cancelled":"\u2298 Cancelled"}[p.status]||p.status);
          return `<tr style="${isPaused?"opacity:.75":""}">
            <td data-l="Status" style="white-space:nowrap;font-size:13px">${statusTxt}</td>
            <td data-l="Clip" class="c-main">${p.url ? `<a class="lnk" href="${esc(p.url)}" target="_blank" rel="noopener">${esc(p.title)}</a>` : esc(p.title)}
              ${p.error ? `<div class="err" style="margin:2px 0 0;font-size:11px;color:var(--bad)">${esc(p.error)}</div>` : ""}</td>
            <td data-l="Creator">${esc(p.creator_name || "None")}</td>
            <td data-l="Account">${esc(p.account_name)}</td>
            <td data-l="Visibility" style="font-size:12px">${p.visibility ? ({"public":"\uD83C\uDF10 Public","private":"\uD83D\uDD12 Private","unlisted":"\uD83D\uDD17 Unlisted"}[p.visibility]||p.visibility) : "\u2013"}</td>
            <td data-l="Views" class="num">${p.views ?? "\u2013"}</td>
            <td class="c-act" style="text-align:right">
              <div style="display:flex;align-items:center;gap:5px;justify-content:flex-end;flex-wrap:wrap">
                ${(p.status==="scheduled"&&!isPaused) ? `<button class="btn sm primary" data-act="pnow" data-id="${p.id}" title="Post immediately">${ic("send")} Now</button>` : ""}
                ${(p.status==="failed"||p.status==="cancelled") ? `<button class="btn sm" data-act="pretry" data-id="${p.id}">Retry</button>` : ""}
                ${(p.status==="scheduled"||p.status==="posting") ? (isPaused ? `<button class="btn sm ghost" data-act="presume" data-id="${p.id}">${ic("play")} Resume</button>` : `<button class="btn sm ghost" data-act="ppause" data-id="${p.id}" title="Pause">${ic("pause")}</button>`) : ""}
                ${(p.status==="scheduled"||p.status==="posting") ? `<button class="btn sm ghost" data-act="pstop" data-id="${p.id}" title="Cancel" style="color:var(--bad)">${ic("x")}</button>` : ""}
              </div>
            </td>
          </tr>`;
        }).join("")}</table></div>`
      : `<p class="help">Nothing queued or posted yet.</p>`}</div>`);"""

if OLD in src:
    result = src.replace(OLD, NEW, 1)
    path.write_text(result, encoding="utf-8")
    print(f"Done. File size: {len(result)} bytes")
else:
    print("ERROR: target block not found!")
    idx = src.find('c-act" style="text-align:right')
    print(f"c-act block at index: {idx}")
    # print surrounding context
    if idx > 0:
        print(repr(src[idx-100:idx+300]))
