"use strict";

(() => {
  const workspace = document.querySelector("#qr-workspace");
  const form = document.querySelector("#qr-form");
  const text = document.querySelector("#qr-text");
  const caption = document.querySelector("#qr-caption");
  const controls = document.querySelector("#qr-controls");
  const generate = document.querySelector("#generate-qr");
  const clear = document.querySelector("#clear-qr");
  const error = document.querySelector("#qr-error");
  const status = document.querySelector("#qr-status");
  const result = document.querySelector("#qr-result");
  const preview = document.querySelector("#qr-preview");
  const download = document.querySelector("#download-qr");
  const maxBytes = Number(workspace.dataset.maxTextBytes);
  let objectUrl = null;

  function discardResult() {
    result.hidden = true;
    preview.removeAttribute("src");
    download.removeAttribute("href");
    if (objectUrl) URL.revokeObjectURL(objectUrl);
    objectUrl = null;
  }

  function updateCount() {
    const bytes = new TextEncoder().encode(text.value).length;
    text.setCustomValidity(bytes > maxBytes ? `O conteúdo excede ${maxBytes} bytes em UTF-8.` : "");
    document.querySelector("#qr-count").textContent = `${bytes} / ${maxBytes} bytes`;
  }

  function edited() {
    discardResult();
    error.hidden = true;
    status.textContent = "";
    updateCount();
  }
  text.addEventListener("input", edited);
  caption.addEventListener("input", edited);
  clear.addEventListener("click", () => {
    form.reset();
    edited();
    text.focus();
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (generate.disabled) return;
    updateCount();
    if (!form.reportValidity()) return;
    discardResult();
    error.hidden = true;
    controls.disabled = generate.disabled = clear.disabled = true;
    workspace.setAttribute("aria-busy", "true");
    status.textContent = "Gerando QR Code…";
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 30000);
    let ready = false;
    try {
      const response = await fetch("/api/qr-code", {
        method: "POST", headers: {"Content-Type": "application/json"},
        body: JSON.stringify({text: text.value, caption: caption.value}), signal: controller.signal,
      });
      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(typeof data.detail === "string" ? data.detail : "Não foi possível gerar o QR Code.");
      }
      if (response.headers.get("content-type") !== "image/png") throw new Error("O servidor retornou um formato inesperado.");
      objectUrl = URL.createObjectURL(await response.blob());
      preview.src = objectUrl;
      download.href = objectUrl;
      result.hidden = false;
      ready = true;
      status.textContent = "Pronto para baixar.";
    } catch (failure) {
      discardResult();
      error.textContent = failure.name === "AbortError" ? "O servidor demorou para responder. Tente novamente." :
        failure instanceof TypeError ? "Não foi possível conectar ao servidor. Confira se a suíte está aberta e tente novamente." : failure.message;
      error.hidden = false;
      status.textContent = "";
    } finally {
      clearTimeout(timeout);
      controls.disabled = generate.disabled = clear.disabled = false;
      workspace.removeAttribute("aria-busy");
      if (ready) document.querySelector("#qr-result-title").focus();
    }
  });
  window.addEventListener("pagehide", discardResult);
  updateCount();
})();
