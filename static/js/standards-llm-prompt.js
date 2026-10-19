function initStandardsLlmPrompt(options) {
    if (!document.getElementById("llmPromptStyles")) {
        const style = document.createElement("style");
        style.id = "llmPromptStyles";
        style.textContent = `
            .llm-prompt-overlay {
                position: fixed;
                inset: 0;
                z-index: 11000;
                display: flex;
                align-items: flex-start;
                justify-content: center;
                padding: 4vh 1rem 2rem;
                background: rgba(15, 23, 42, 0.55);
                overflow-y: auto;
            }
            .llm-prompt-overlay[hidden] {
                display: none !important;
            }
            .llm-prompt-dialog {
                width: min(760px, 100%);
                background: #ffffff;
                border-radius: 12px;
                box-shadow: 0 20px 50px rgba(0, 0, 0, 0.25);
                padding: 1.5rem;
            }
            .llm-prompt-header {
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 1rem;
                margin-bottom: 0.75rem;
            }
            .llm-prompt-header h2 {
                margin: 0;
                font-size: 1.25rem;
                color: #111827;
            }
            .llm-prompt-close {
                border: none;
                background: transparent;
                font-size: 1.75rem;
                line-height: 1;
                cursor: pointer;
                color: #4b5563;
                padding: 0 0.25rem;
            }
            .llm-prompt-lead,
            .llm-prompt-status {
                margin: 0 0 1rem;
                color: #374151;
                font-size: 0.9rem;
                line-height: 1.45;
            }
            .llm-prompt-dialog label {
                font-size: 0.875rem;
                font-weight: 600;
                color: #111827;
                margin-bottom: 0.85rem;
            }
            .llm-prompt-dialog label:not(.filter-toggle) {
                display: block;
            }
            .llm-prompt-dialog label[hidden] {
                display: none !important;
            }
            .llm-prompt-dialog textarea {
                display: block;
                width: 100%;
                margin-top: 0.4rem;
                padding: 0.65rem 0.75rem;
                border: 1px solid #d1d5db;
                border-radius: 8px;
                font: inherit;
                font-weight: 400;
                resize: vertical;
                box-sizing: border-box;
            }
            .llm-prompt-output {
                min-height: 220px;
                max-height: 40vh;
                font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
                font-size: 0.8rem;
                line-height: 1.4;
            }
            .llm-prompt-actions {
                display: flex;
                gap: 0.75rem;
                align-items: center;
                margin-bottom: 0.75rem;
            }
            .llm-prompt-result[hidden] {
                display: none !important;
            }
            .llm-prompt-status.error {
                color: #b91c1c;
            }
            #llmPromptGenerate,
            #llmPromptGenerate:hover,
            #llmPromptGenerate:focus {
                background: #16a34a;
                color: #ffffff;
            }
            #llmPromptGenerate:hover {
                background: #15803d;
            }
            .llm-prompt-download {
                display: inline-block;
                background: #16a34a;
                color: #ffffff;
                font-weight: 600;
                text-decoration: none;
                padding: 0.5rem 1rem;
                border-radius: 6px;
            }
            .llm-prompt-download:hover {
                background: #15803d;
                color: #ffffff;
            }
            .llm-prompt-download[hidden] {
                display: none !important;
            }
        `;
        document.head.appendChild(style);
    }

    const button = document.getElementById(options.buttonId || "createLlmPromptBtn");
    if (!button || button.dataset.llmPromptReady === "true") {
        return;
    }
    button.dataset.llmPromptReady = "true";

    const pageFilter = options.kpiFilterId
        ? document.getElementById(options.kpiFilterId)
        : null;
    const includePublications = Boolean(options.includePublications);

    const overlay = document.createElement("div");
    overlay.className = "llm-prompt-overlay";
    overlay.hidden = true;
    overlay.innerHTML = `
        <div class="llm-prompt-dialog" role="dialog" aria-modal="true" aria-labelledby="llmPromptTitle">
            <div class="llm-prompt-header">
                <h2 id="llmPromptTitle">Create LLM Prompt</h2>
                <button type="button" class="llm-prompt-close" aria-label="Close">&times;</button>
            </div>
            <p class="llm-prompt-lead">Builds a prompt from the data on this page and the standards-development context file. Copy it into your LLM. Leave the question blank if you want a context pack you can question in the chat.</p>
            <label>Question
                <textarea id="llmPromptQuestion" rows="4" placeholder="What do you want to ask?"></textarea>
            </label>
            <label class="filter-toggle">
                <div class="toggle-switch">
                    <input type="checkbox" id="llmPromptKpiOnly">
                    <span class="toggle-slider"></span>
                </div>
                <span class="toggle-label">Show KPIs Only</span>
            </label>
            <label class="filter-toggle" id="llmPromptPublicationsLabel" hidden>
                <div class="toggle-switch">
                    <input type="checkbox" id="llmPromptPublications">
                    <span class="toggle-slider"></span>
                </div>
                <span class="toggle-label">Include all publication titles</span>
            </label>
            <div class="llm-prompt-actions">
                <button type="button" class="wa-button" id="llmPromptGenerate">Create prompt</button>
            </div>
            <p class="llm-prompt-status" id="llmPromptStatus" role="status"></p>
            <div class="llm-prompt-result" id="llmPromptResult" hidden>
                <label>Prompt
                    <textarea class="llm-prompt-output" id="llmPromptOutput" readonly></textarea>
                </label>
                <div class="llm-prompt-actions">
                    <button type="button" class="wa-button" id="llmPromptCopy">Copy prompt</button>
                    <a class="llm-prompt-download" id="llmPromptDownload" href="#" hidden>Download prompt and screenshots (.zip)</a>
                </div>
            </div>
        </div>
    `;
    document.body.appendChild(overlay);

    const dialog = overlay.querySelector(".llm-prompt-dialog");
    const closeButton = overlay.querySelector(".llm-prompt-close");
    const question = overlay.querySelector("#llmPromptQuestion");
    const kpiInput = overlay.querySelector("#llmPromptKpiOnly");
    const publicationsLabel = overlay.querySelector("#llmPromptPublicationsLabel");
    const publicationsInput = overlay.querySelector("#llmPromptPublications");
    const generateButton = overlay.querySelector("#llmPromptGenerate");
    const status = overlay.querySelector("#llmPromptStatus");
    const result = overlay.querySelector("#llmPromptResult");
    const output = overlay.querySelector("#llmPromptOutput");
    const downloadLink = overlay.querySelector("#llmPromptDownload");
    const copyButton = overlay.querySelector("#llmPromptCopy");

    if (includePublications) {
        publicationsLabel.hidden = false;
    }

    function syncKpiFromPage() {
        if (pageFilter) {
            kpiInput.checked = pageFilter.checked;
        }
    }

    function openDialog() {
        syncKpiFromPage();
        status.textContent = "";
        status.classList.remove("error");
        overlay.hidden = false;
        question.focus();
    }

    function closeDialog() {
        overlay.hidden = true;
        button.focus();
    }

    button.addEventListener("click", openDialog);
    closeButton.addEventListener("click", closeDialog);
    overlay.addEventListener("click", function (event) {
        if (event.target === overlay) {
            closeDialog();
        }
    });
    dialog.addEventListener("click", function (event) {
        event.stopPropagation();
    });
    document.addEventListener("keydown", function (event) {
        if (event.key === "Escape" && !overlay.hidden) {
            closeDialog();
        }
    });

    if (pageFilter) {
        pageFilter.addEventListener("change", syncKpiFromPage);
        kpiInput.addEventListener("change", function () {
            if (pageFilter.checked !== kpiInput.checked) {
                pageFilter.checked = kpiInput.checked;
                pageFilter.dispatchEvent(new Event("change"));
            }
        });
    }

    generateButton.addEventListener("click", async function () {
        generateButton.disabled = true;
        generateButton.textContent = "Creating...";
        status.textContent = "";
        status.classList.remove("error");
        let captureWarning = "";
        let chartImages = [];
        try {
            if (typeof options.captureImages === "function") {
                generateButton.textContent = "Capturing charts...";
                try {
                    chartImages = await options.captureImages(function (current, total) {
                        generateButton.textContent = "Capturing charts " + current + "/" + total + "...";
                    });
                } catch (captureError) {
                    captureWarning = "Chart images could not be captured.";
                    chartImages = [];
                }
                generateButton.textContent = "Creating...";
            }
            const response = await fetch("/api/standards-development/llm-prompt", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    scope: options.scope,
                    question: question.value,
                    kpi_only: kpiInput.checked,
                    include_publications: includePublications && publicationsInput.checked,
                    charts: chartImages
                })
            });
            const data = await response.json();
            if (!response.ok) {
                const detail = data && data.detail;
                throw new Error(typeof detail === "string" ? detail : "Failed to create the prompt");
            }
            output.value = data.prompt || "";
            if (data.download_url) {
                downloadLink.href = data.download_url;
                downloadLink.hidden = false;
                if (!data.image_count) {
                    downloadLink.textContent = "Download prompt (.zip)";
                } else if (data.image_kind === "charts") {
                    downloadLink.textContent = "Download prompt and charts (.zip)";
                } else {
                    downloadLink.textContent = "Download prompt and screenshots (.zip)";
                }
            } else {
                downloadLink.hidden = true;
            }
            result.hidden = false;
            status.textContent = captureWarning ? "Prompt ready. " + captureWarning : "Prompt ready.";
            if (captureWarning) {
                status.classList.add("error");
            }
            copyButton.textContent = "Copy prompt";
        } catch (error) {
            status.textContent = error.message || "Failed to create the prompt";
            status.classList.add("error");
        } finally {
            generateButton.disabled = false;
            generateButton.textContent = "Create prompt";
        }
    });

    copyButton.addEventListener("click", async function () {
        const text = output.value;
        if (!text) {
            return;
        }
        try {
            await navigator.clipboard.writeText(text);
            copyButton.textContent = "Copied";
        } catch (error) {
            output.focus();
            output.select();
            const copied = document.execCommand("copy");
            copyButton.textContent = copied ? "Copied" : "Select the prompt and copy it";
        }
    });
}
