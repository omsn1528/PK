"""Add new post action handlers to index.html."""
import pathlib

path = pathlib.Path(r"C:\peakcut\web\index.html")
src = path.read_text(encoding="utf-8")

OLD = '''    if (a === "postalln") {
      if (!await ask("Post all queued clips now?", "All clips currently scheduled will be sent to their accounts immediately, in order.")) return;
      await api("/api/posts/expedite-all", {method:"POST"});
      toast("All clips moved to post now", "ok");
      await loadUploads();
      return;
    }
    if (a === "ssave")'''

NEW = '''    if (a === "postalln") {
      if (!await ask("Post all queued clips now?", "All clips currently scheduled will be sent to their accounts immediately, in order.")) return;
      await api("/api/posts/expedite-all", {method:"POST"});
      toast("All clips moved to post now", "ok");
      await loadUploads();
      return;
    }
    if (a === "ppause") {
      await api(`/api/posts/${d.id}/pause`, {method:"POST"});
      toast("Upload paused", "ok");
      if (S.view === "uploads") await loadUploads(); else await loadOverview();
      return;
    }
    if (a === "presume") {
      await api(`/api/posts/${d.id}/resume`, {method:"POST"});
      toast("Upload resumed", "ok");
      if (S.view === "uploads") await loadUploads(); else await loadOverview();
      return;
    }
    if (a === "pstop") {
      if (!await ask("Cancel this upload?", "It will be removed from the queue. You can retry it later.", "Cancel upload", true)) return;
      await api(`/api/posts/${d.id}/stop`, {method:"POST"});
      toast("Upload cancelled", "ok");
      if (S.view === "uploads") await loadUploads(); else await loadOverview();
      return;
    }
    if (a === "pmoveup") {
      await send(`/api/posts/${d.id}/move`, {direction:"up"});
      await loadUploads();
      return;
    }
    if (a === "pmovedown") {
      await send(`/api/posts/${d.id}/move`, {direction:"down"});
      await loadUploads();
      return;
    }
    if (a === "pschedule") {
      await openPostSchedule(d.id);
      return;
    }
    if (a === "refreshuploads") {
      await loadUploads();
      return;
    }
    if (a === "ssave")'''

if OLD in src:
    result = src.replace(OLD, NEW, 1)
    path.write_text(result, encoding="utf-8")
    print(f"Done. File size: {len(result)} bytes")
else:
    print("ERROR: target block not found!")
    idx = src.find('if (a === "postalln")')
    print(f"postalln block at index: {idx}")
