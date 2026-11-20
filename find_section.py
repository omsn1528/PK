import pathlib
path = pathlib.Path(r"C:\peakcut\web\index.html")
src = path.read_text(encoding="utf-8")
start = src.find("/* ============================================================ upload status */")
end = src.find("\nfunction barChart(")
print(f"start={start}, end={end}, length={end-start}")
print("--- SECTION FIRST 400 chars ---")
print(repr(src[start:start+400]))
