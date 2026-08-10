import subprocess, sys, time, threading, http.server, socketserver, os, functools
from playwright.sync_api import sync_playwright

DIR = os.path.dirname(os.path.abspath(__file__))
PORT = 8899

handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=DIR)
socketserver.TCPServer.allow_reuse_address = True
httpd = socketserver.TCPServer(("127.0.0.1", PORT), handler)
threading.Thread(target=httpd.serve_forever, daemon=True).start()

failures = []
def check(name, cond, detail=""):
    print(("PASS  " if cond else "FAIL  ") + name + (f"  {detail}" if detail else ""))
    if not cond:
        failures.append(name)

with sync_playwright() as p:
    browser = p.chromium.launch(
        executable_path="/opt/pw-browsers/chromium-1194/chrome-linux/chrome",
        args=["--no-sandbox", "--autoplay-policy=no-user-gesture-required"],
    )
    page = browser.new_page()
    console_errors = []
    page.on("console", lambda m: console_errors.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: console_errors.append("PAGEERROR: " + str(e)))

    page.goto(f"http://127.0.0.1:{PORT}/transcriber.html")
    page.wait_for_function("window.__ready === true", timeout=15000)
    check("page loads and module script executes", True)

    # 1. UI renders
    check("title renders", page.inner_text("h1") == "Video Transcriber")
    check("transcribe button starts disabled", page.is_disabled("#go"))

    # 2. Timestamp formatting
    cases = [(0, "00:00:00,000"), (2.374, "00:00:02,374"), (61.5, "00:01:01,500"),
             (3723.004, "01:02:03,004"), (-5, "00:00:00,000")]
    for secs, want in cases:
        got = page.evaluate("s => window.__fmt(s)", secs)
        check(f"fmt({secs}) == {want}", got == want, f"got {got}")

    # 3. File selection updates UI
    page.set_input_files("#file", os.path.join(DIR, "test_video.mp4"))
    page.wait_for_function("document.getElementById('go').disabled === false", timeout=5000)
    check("file selection enables transcribe", not page.is_disabled("#go"))
    check("file name shown in dropzone", "test_video.mp4" in page.inner_text("#drop"),
          page.inner_text("#drop").replace("\n", " | "))

    # 4. Audio decoding on a real video container (webm, since this Chromium build
    #    ships without the proprietary AAC/H.264 codecs that real Chrome includes)
    page.set_input_files("#file", os.path.join(DIR, "test_video.webm"))
    res = page.evaluate("""async () => {
        const f = document.getElementById('file').files[0];
        const audio = await window.__decodeToMono16k(f);
        let peak = 0;
        for (let i = 0; i < audio.length; i++) peak = Math.max(peak, Math.abs(audio[i]));
        return { length: audio.length, seconds: audio.length / 16000, peak,
                 type: audio.constructor.name };
    }""")
    check("decodes mp4 audio to Float32Array", res["type"] == "Float32Array", res["type"])
    check("decoded at 16 kHz mono, ~38 s", 36 < res["seconds"] < 40,
          f"{res['seconds']:.2f}s, {res['length']} samples")
    check("decoded audio contains real signal", res["peak"] > 0.01, f"peak={res['peak']:.3f}")

    # 4b. Undecodable container yields a specific, actionable message rather than a raw
    #     EncodingError. Exercised here via the mp4 this Chromium cannot decode.
    page.set_input_files("#file", os.path.join(DIR, "test_video.mp4"))
    msg = page.evaluate("""async () => { try {
        await window.__decodeToMono16k(document.getElementById('file').files[0]);
        return 'DECODED';
    } catch (e) { return e.message; } }""")
    check("undecodable file gives actionable error, not EncodingError",
          "could not decode" in msg and "AAC" in msg and "ffmpeg" in msg, msg[:150])

    # 5. Engine-load failure path shows a helpful message (CDN is blocked in this sandbox)
    page.set_input_files("#file", os.path.join(DIR, "test_video.webm"))
    page.click("#go")
    page.wait_for_function(
        "document.getElementById('status').classList.contains('err')", timeout=90000)
    status = page.inner_text("#status")
    check("CDN failure surfaces a clear, actionable error",
          "speech engine" in status and "internet" in status, status[:130])
    check("button re-enabled after failure", not page.is_disabled("#go"))

    # 6. Output stage: text/SRT generation and the download buttons. Driven through the
    #    test hook so it does not depend on a real transcription run.
    page.set_input_files("#file", os.path.join(DIR, "test_video.mp4"))
    page.evaluate("""() => window.__test.setChunks([
        {start: 2.374, end: 8.204, text: ' Hello, is anyone home?'},
        {start: 61.5,  end: 65.0,  text: ' Package delivered.'},
    ])""")
    txt = page.evaluate("() => window.__test.toText()")
    srt = page.evaluate("() => window.__test.toSrt()")
    check("txt lines are timestamped and trimmed",
          txt.splitlines()[0] == "[00:00:02] Hello, is anyone home?", repr(txt.splitlines()[0]))
    check("srt block is well formed",
          srt.startswith("1\n00:00:02,374 --> 00:00:08,204\nHello, is anyone home?"), repr(srt[:60]))
    check("srt numbering increments",
          "\n2\n00:01:01,500 --> 00:01:05,000\n" in srt, repr(srt[-70:]))
    check("clipboard API is available (page is a secure context)",
          page.evaluate("() => window.isSecureContext && !!navigator.clipboard?.writeText"))

    for btn, ext in [("#dlTxt", ".txt"), ("#dlSrt", ".srt")]:
        with page.expect_download(timeout=10000) as dl_info:
            page.click(btn)
        dl = dl_info.value
        check(f"{btn} saves as <video name>{ext}",
              dl.suggested_filename == "test_video" + ext, dl.suggested_filename)

    # 7. No unexpected JS errors beyond the expected network failure
    unexpected = [e for e in console_errors
                  if "jsdelivr" not in e and "Failed to fetch" not in e
                  and "ERR_" not in e and "net::" not in e
                  and "favicon" not in e and "404" not in e]
    check("no unexpected JS errors", not unexpected, str(unexpected)[:200])

    browser.close()

httpd.shutdown()
print("\n" + ("ALL CHECKS PASSED" if not failures else f"FAILURES: {failures}"))
sys.exit(1 if failures else 0)
