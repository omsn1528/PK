"""Replace the drawUploads section in index.html with full-control version."""
import pathlib

path = pathlib.Path(r"C:\peakcut\web\index.html")
src = path.read_text(encoding="utf-8")

MARKER_START = "/* ============================================================ upload status */"
MARKER_END   = "\nfunction barChart("

start = src.find(MARKER_START)
end   = src.find(MARKER_END)
if start == -1 or end == -1:
    raise RuntimeError(f"Markers not found: start={start}, end={end}")

NEW_SECTION = r"""/* ============================================================ upload status */
S.posts = S.posts || [];
async function loadUploads() {
  try { S.posts = await api("/api/posts"); } catch { S.posts = []; }
  drawUploads();
}

/* helpers */
const VIS_LABEL = {public:"\uD83C\uDF10 Public", private:"\uD83D\uDD12 Private", unlisted:"\uD83D\uDD17 Unlisted"};
const VIS_COL   = {public:"var(--good)", private:"var(--bad)", unlisted:"var(--brand-deep)"};

function postCtrlRow(p, inQueue) {
  const id = p.id, s = p.status;
  const isActive = s === "scheduled" || s === "posting";
  const isPaused = !!p.paused;

  /* visibility selector for active/paused posts */
  const visPicker = (isActive || isPaused) ?
    `<select class="pvis-sel" data-id="${id}" title="Visibility"
       style="height:28px;padding:0 6px;font-size:12px;border-radius:6px;border:1px solid var(--line-2);background:#fff;cursor:pointer">
       <option value="public"   ${p.visibility==="public"   ?"selected":""}>&#x1F310; Public</option>
       <option value="private"  ${p.visibility==="private"  ?"selected":""}>&#x1F512; Private</option>
       <option value="unlisted" ${p.visibility==="unlisted" ?"selected":""}>&#x1F517; Unlisted</option>
     </select>` :
    (p.visibility ? `<span style="font-size:11px;color:${VIS_COL[p.visibility]||"var(--dim)"}">${VIS_LABEL[p.visibility]||p.visibility}</span>` : "");

  /* schedule button */
  const schedBtn = isActive ? `<button class="btn sm ghost" data-act="pschedule" data-id="${id}" title="Set schedule time">${ic("clock")}</button>` : "";

  /* move up/down (queued, not paused) */
  const moveCtrl = (inQueue && isActive && !isPaused) ? `
    <button class="btn sm ghost icon" data-act="pmoveup"   data-id="${id}" title="Move up in queue" style="font-size:13px;padding:0 7px">&#8679;</button>
    <button class="btn sm ghost icon" data-act="pmovedown" data-id="${id}" title="Move down in queue" style="font-size:13px;padding:0 7px">&#8681;</button>` : "";

  /* Post Now / Retry */
  let primary = "";
  if (s === "scheduled" && !isPaused)
    primary = `<button class="btn sm primary" data-act="pnow" data-id="${id}" title="Post immediately">${ic("send")} Now</button>`;
  if (s === "failed" || s === "cancelled")
    primary = `<button class="btn sm" data-act="pretry" data-id="${id}">Retry</button>`;

  /* Pause / Resume */
  let pauseBtn = "";
  if (s === "scheduled" || s === "posting") {
    pauseBtn = isPaused
      ? `<button class="btn sm ghost" data-act="presume" data-id="${id}" title="Resume">${ic("play")} Resume</button>`
      : `<button class="btn sm ghost" data-act="ppause"  data-id="${id}" title="Pause">${ic("pause")}</button>`;
  }

  /* Cancel/Stop */
  const stopBtn = (isActive || isPaused)
    ? `<button class="btn sm ghost" data-act="pstop" data-id="${id}" title="Cancel this upload" style="color:var(--bad)">${ic("x")}</button>`
    : "";

  return `<div style="display:flex;align-items:center;gap:5px;flex-wrap:wrap;justify-content:flex-end">
    ${visPicker}${schedBtn}${moveCtrl}${primary}${pauseBtn}${stopBtn}
  </div>`;
}

function drawUploads() {
  const el = $("#upstatus"); if (!el) return;
  const posts = S.posts || [];
  const PSTAT = {scheduled:"\uD83D\uDD50 Queued", posting:"\u2B06\uFE0F Uploading", posted:"\u2705 Posted", failed:"\u274C Failed", cancelled:"\u2298 Cancelled"};
  const PCOL  = {scheduled:"var(--dim)", posting:"var(--brand)", posted:"var(--good)", failed:"var(--bad)", cancelled:"var(--faint)"};

  if (!posts.length) {
    el.innerHTML = `<div class="card"><div class="card-head"><div><h2>Upload Status</h2><p class="sub">Auto-upload history and queue for all connected accounts.</p></div></div>
      <div class="empty"><img src="/brand/favicon.svg" alt=""><b>No uploads yet</b>Turn on Auto Upload when processing a video to post clips automatically.</div></div>`;
    return;
  }

  const uploading = posts.filter(p => p.status === "posting");
  const queued    = posts.filter(p => p.status === "scheduled" && !p.paused);
  const paused    = posts.filter(p => p.status === "scheduled" && p.paused);
  const done      = posts.filter(p => p.status === "posted");
  const failed    = posts.filter(p => p.status === "failed");

  let summary = [];
  if (uploading.length) summary.push(`<span style="color:var(--brand);font-weight:600">${uploading.length} uploading</span>`);
  if (paused.length)    summary.push(`<span style="color:var(--dim)">${paused.length} paused</span>`);
  if (queued.length)    summary.push(`${queued.length} queued`);
  if (done.length)      summary.push(`${done.length} posted`);
  if (failed.length)    summary.push(`<span style="color:var(--bad)">${failed.length} failed</span>`);

  let html = `<div class="card"><div class="card-head"><div><h2>Upload Status</h2>
    <p class="sub">${summary.join(" \xb7 ")}</p></div>
    <div style="display:flex;gap:8px;flex-wrap:wrap">
      ${(queued.length||paused.length) ? `<button class="btn sm primary" data-act="postalln" title="Post all queued immediately">${ic("send")} Post All Now</button>` : ""}
      <button class="btn sm" data-act="refreshuploads">${ic("clock")} Refresh</button>
    </div></div>`;

  /* active upload progress bar */
  if (uploading.length) {
    html += `<div style="margin:0 0 14px;padding:12px 14px;background:var(--muted);border-radius:10px">
      <b style="font-size:13px;display:block;margin-bottom:8px">Uploading now</b>
      ${uploading.map(p => `<div style="margin:0 0 10px">
        <div style="display:flex;justify-content:space-between;font-size:13px;margin-bottom:4px">
          <span style="font-weight:600">${esc(p.title)}</span>
          <span style="color:var(--dim)">${esc(p.account_name)}</span>
        </div>
        ${p.progress != null ? `<div class="bar"><i style="width:${Math.round((p.progress||0)*100)}%"></i></div>
          <div style="display:flex;justify-content:space-between;margin-top:3px">
            <small style="color:var(--dim)">${Math.round((p.progress||0)*100)}% uploaded</small>
            ${postCtrlRow(p, false)}
          </div>` : postCtrlRow(p, false)}
      </div>`).join("")}</div>`;
  }

  /* per-account tables */
  const byAccount = {};
  posts.forEach(p => {
    const key = p.account_name || "Unknown account";
    (byAccount[key] = byAccount[key] || []).push(p);
  });

  Object.entries(byAccount).forEach(([acct, ps]) => {
    const queuedHere = ps
      .filter(p => p.status === "scheduled")
      .sort((a,b) => (a.priority||a.due_at) - (b.priority||b.due_at));
    html += `<div style="margin:16px 0 8px">
      <h3 style="font-size:13px;font-weight:700;color:var(--dim);letter-spacing:.04em;margin-bottom:8px">${esc(acct)}</h3>
      <div class="scroll"><table>
        <tr>
          <th style="min-width:160px">Clip</th>
          <th>Status</th>
          <th>Visibility</th>
          <th>Scheduled for</th>
          <th class="num">Views</th>
          <th style="min-width:280px;text-align:right">Actions</th>
        </tr>
        ${ps.map(p => {
          const inQueue = queuedHere.some(q => q.id === p.id);
          const statusTxt = (p.paused && p.status==="scheduled") ? "\u23F8 Paused" : (PSTAT[p.status]||esc(p.status));
          const statusCol = (p.paused && p.status==="scheduled") ? "var(--dim)" : (PCOL[p.status]||"inherit");
          const whenTs    = p.due_at   ? new Date(p.due_at*1000)    :
                            p.posted_at ? new Date(p.posted_at*1000) : null;
          const whenStr   = whenTs ? whenTs.toLocaleString([],{month:"short",day:"numeric",hour:"2-digit",minute:"2-digit"}) : "\u2013";
          return `<tr style="${p.paused?"opacity:.75":""}">
            <td class="c-main">
              ${p.url ? `<a class="lnk" href="${esc(p.url)}" target="_blank" rel="noopener">${esc(p.title)}</a>` : esc(p.title)}
              ${p.error ? `<div class="err" style="margin:2px 0 0;font-size:11px;color:var(--bad)">${esc(p.error)}</div>` : ""}
            </td>
            <td style="color:${statusCol};white-space:nowrap;font-size:13px">${statusTxt}</td>
            <td style="font-size:12px;white-space:nowrap;color:${VIS_COL[p.visibility]||"var(--dim)"}">
              ${p.visibility ? (VIS_LABEL[p.visibility]||p.visibility) : "\u2013"}
            </td>
            <td style="color:var(--dim);font-size:12px;white-space:nowrap">${whenStr}</td>
            <td class="num" style="color:var(--dim)">${p.views != null ? p.views.toLocaleString() : "\u2013"}</td>
            <td>${postCtrlRow(p, inQueue)}</td>
          </tr>`;
        }).join("")}
      </table></div></div>`;
  });

  html += `</div>`;
  el.innerHTML = html;

  /* live-bind visibility selects */
  el.querySelectorAll(".pvis-sel").forEach(sel => {
    sel.addEventListener("change", async () => {
      try {
        await send(`/api/posts/${sel.dataset.id}`, {visibility: sel.value}, "PATCH");
        toast(`Visibility set to ${sel.value}`, "ok");
        await loadUploads();
      } catch(e) { toast(e.message, "bad"); }
    });
  });
}

async function openPostSchedule(pid) {
  const p = (S.posts||[]).find(x => x.id === pid);
  if (!p) return;
  const cur = p.due_at ? new Date(p.due_at*1000).toISOString().slice(0,16) : "";
  const val = window.prompt(`Schedule time for:\n"${p.title}"\n\nDate/time (YYYY-MM-DDTHH:MM):`, cur);
  if (val === null) return;
  const ts = val ? new Date(val).getTime()/1000 : Date.now()/1000;
  if (val && isNaN(ts)) return toast("That date didn't parse. Try YYYY-MM-DDTHH:MM format.", "bad");
  try {
    await send(`/api/posts/${pid}`, {due_at: ts}, "PATCH");
    toast("Schedule updated", "ok");
    await loadUploads();
  } catch(e) { toast(e.message, "bad"); }
}

"""

result = src[:start] + NEW_SECTION + src[end:]
path.write_text(result, encoding="utf-8")
print(f"Done. File size: {len(result)} bytes")
