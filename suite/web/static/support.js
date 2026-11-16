"use strict";

(() => {
  const status = document.querySelector("#copy-status");
  document.querySelectorAll("[data-copy-target]").forEach((button) => button.addEventListener("click", async () => {
    const key = document.getElementById(button.dataset.copyTarget);
    button.disabled = true;
    try {
      await navigator.clipboard.writeText(key.value);
      status.textContent = button.dataset.copyMessage;
    } catch {
      key.focus();
      key.select();
      status.textContent = "Não foi possível copiar automaticamente. O texto está selecionado para você copiar.";
    } finally {
      button.disabled = false;
    }
  }));
})();
