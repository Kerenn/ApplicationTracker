document.addEventListener("DOMContentLoaded", () => {
  const syncStageSelect = (statusSelect, useFirstMatch = false) => {
    const stageSelect = document.getElementById(statusSelect.dataset.stageTarget);
    if (!stageSelect) return;

    const status = statusSelect.value;
    let selectedStillValid = false;
    let firstMatch = null;
    for (const option of stageSelect.options) {
      const optionStatus = option.dataset.status;
      if (!optionStatus) continue;
      const matches = optionStatus === status;
      option.hidden = !matches;
      option.disabled = !matches;
      if (matches && !firstMatch) firstMatch = option;
      if (matches && option.selected) selectedStillValid = true;
    }
    if (!selectedStillValid && useFirstMatch && firstMatch) {
      firstMatch.selected = true;
    }
  };

  for (const statusSelect of document.querySelectorAll("[data-status-select]")) {
    syncStageSelect(statusSelect, true);
    statusSelect.addEventListener("change", () => syncStageSelect(statusSelect, true));
  }

  for (const form of document.querySelectorAll("form[data-confirm]")) {
    form.addEventListener("submit", (event) => {
      if (!window.confirm(form.dataset.confirm)) event.preventDefault();
    });
  }

  let draggedCard = null;
  for (const card of document.querySelectorAll("[data-application-id][draggable='true']")) {
    card.addEventListener("dragstart", (event) => {
      draggedCard = card;
      card.classList.add("dragging");
      event.dataTransfer.effectAllowed = "move";
      event.dataTransfer.setData("text/plain", card.dataset.applicationId);
    });
    card.addEventListener("dragend", () => {
      draggedCard = null;
      card.classList.remove("dragging");
    });
  }

  for (const column of document.querySelectorAll("[data-board-status]")) {
    column.addEventListener("dragover", (event) => {
      event.preventDefault();
      column.classList.add("drag-over");
      event.dataTransfer.dropEffect = "move";
    });
    column.addEventListener("dragleave", (event) => {
      if (!column.contains(event.relatedTarget)) column.classList.remove("drag-over");
    });
    column.addEventListener("drop", (event) => {
      event.preventDefault();
      column.classList.remove("drag-over");
      const applicationId = event.dataTransfer.getData("text/plain");
      if (!applicationId || !draggedCard) return;
      draggedCard.classList.add("saving");

      const form = document.createElement("form");
      form.method = "post";
      form.action = `/applications/${applicationId}/quick-status`;
      for (const [name, value] of Object.entries({
        status: column.dataset.boardStatus,
        return_to: "/board",
      })) {
        const input = document.createElement("input");
        input.type = "hidden";
        input.name = name;
        input.value = value;
        form.appendChild(input);
      }
      document.body.appendChild(form);
      form.submit();
    });
  }
});
