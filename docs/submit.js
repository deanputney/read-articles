// Shared article-submission logic for the Read Articles Podcast site.
// Used by both submit.html (full form + token settings) and index.html
// (compact quick-submit box shown only when a token is saved).
//
// A GitHub fine-grained token (Contents: Read and write) is stored only in
// this browser's localStorage and sent only to GitHub's dispatch API, which
// triggers the process-article workflow.

const RA = {
    OWNER: "deanputney",
    REPO: "read-articles",
    TOKEN_KEY: "ra_github_token",

    VOICES: [
        { value: "af_bella", label: "af_bella (American female)" },
        { value: "af_sarah", label: "af_sarah (American female)" },
        { value: "af_nova", label: "af_nova (American female)" },
        { value: "am_santa", label: "am_santa (American male)" },
        { value: "am_adam", label: "am_adam (American male)" },
        { value: "am_echo", label: "am_echo (American male)" },
        { value: "bf_alice", label: "bf_alice (British female)" },
        { value: "bf_emma", label: "bf_emma (British female)" },
        { value: "bm_daniel", label: "bm_daniel (British male)" },
        { value: "bm_george", label: "bm_george (British male)" }
    ],

    getToken() {
        return localStorage.getItem(this.TOKEN_KEY);
    },

    setToken(token) {
        localStorage.setItem(this.TOKEN_KEY, token);
    },

    clearToken() {
        localStorage.removeItem(this.TOKEN_KEY);
    },

    // Fire a repository_dispatch event. Returns { ok, status, message }.
    async dispatch(url, voice) {
        const token = this.getToken();
        if (!token) return { ok: false, status: 0, message: "No token saved." };
        try {
            const resp = await fetch(
                `https://api.github.com/repos/${this.OWNER}/${this.REPO}/dispatches`,
                {
                    method: "POST",
                    headers: {
                        "Accept": "application/vnd.github+json",
                        "Authorization": `Bearer ${token}`,
                        "X-GitHub-Api-Version": "2022-11-28"
                    },
                    body: JSON.stringify({
                        event_type: "new-article",
                        client_payload: { url, voice }
                    })
                }
            );
            if (resp.status === 204) {
                return { ok: true, status: 204, message: "Submitted! The Action is running — check the Actions tab in a few minutes." };
            }
            if (resp.status === 401 || resp.status === 403) {
                return { ok: false, status: resp.status, message: "GitHub rejected the token (401/403). Check it grants this repo 'Contents: Read and write' and hasn't expired." };
            }
            if (resp.status === 404) {
                return { ok: false, status: 404, message: "Repository not found (404). The token may lack access to this repo." };
            }
            let detail = "";
            try { detail = (await resp.json()).message || ""; } catch (_) {}
            return { ok: false, status: resp.status, message: `Unexpected response ${resp.status}. ${detail}` };
        } catch (err) {
            return { ok: false, status: 0, message: `Request failed: ${err.message}` };
        }
    },

    // Render a compact submission box into the given container element.
    // If no token is saved, render only a subtle link to the full submit page.
    initQuickSubmit(containerId) {
        const c = document.getElementById(containerId);
        if (!c) return;
        c.innerHTML = "";

        if (!this.getToken()) {
            const a = document.createElement("a");
            a.href = "submit.html";
            a.textContent = "+ Submit an article";
            a.style.cssText = "font-size:14px;color:#888;text-decoration:none;";
            c.appendChild(a);
            return;
        }

        const box = document.createElement("div");
        box.style.cssText = "background:#fff;border:1px solid #ddd;border-radius:8px;padding:16px;margin-bottom:28px;";

        const row = document.createElement("div");
        row.style.cssText = "display:flex;gap:8px;flex-wrap:wrap;align-items:center;";

        const urlInput = document.createElement("input");
        urlInput.type = "url";
        urlInput.placeholder = "https://example.com/some-article";
        urlInput.required = true;
        urlInput.style.cssText = "flex:1 1 260px;padding:9px;font-size:15px;border:1px solid #ccc;border-radius:6px;";

        const voiceSelect = document.createElement("select");
        voiceSelect.style.cssText = "padding:9px;font-size:15px;border:1px solid #ccc;border-radius:6px;";
        this.VOICES.forEach(v => {
            const opt = document.createElement("option");
            opt.value = v.value;
            opt.textContent = v.value;
            voiceSelect.appendChild(opt);
        });

        const btn = document.createElement("button");
        btn.textContent = "Submit";
        btn.style.cssText = "padding:9px 16px;font-size:15px;border:none;border-radius:6px;background:#007bff;color:#fff;cursor:pointer;";

        const settingsLink = document.createElement("a");
        settingsLink.href = "submit.html";
        settingsLink.textContent = "⚙";
        settingsLink.title = "Manage access token";
        settingsLink.style.cssText = "color:#888;text-decoration:none;font-size:18px;";

        row.append(urlInput, voiceSelect, btn, settingsLink);
        box.appendChild(row);

        const status = document.createElement("div");
        status.style.cssText = "margin-top:10px;font-size:14px;display:none;";
        box.appendChild(status);

        const setStatus = (msg, ok) => {
            status.textContent = msg;
            status.style.display = "block";
            status.style.color = ok ? "#1a7f37" : "#b3261e";
        };

        const submit = async () => {
            const url = urlInput.value.trim();
            if (!url) { setStatus("Enter a URL first.", false); return; }
            btn.disabled = true;
            btn.style.background = "#9bc4ef";
            setStatus("Sending…", true);
            const result = await this.dispatch(url, voiceSelect.value);
            setStatus(result.message, result.ok);
            if (result.ok) urlInput.value = "";
            btn.disabled = false;
            btn.style.background = "#007bff";
        };

        btn.addEventListener("click", submit);
        urlInput.addEventListener("keydown", (e) => {
            if (e.key === "Enter") { e.preventDefault(); submit(); }
        });

        c.appendChild(box);
    }
};
