/* Task Board frontend.
 *
 * One file, no framework. Structure:
 *   1. config + tiny helpers
 *   2. API calls
 *   3. rendering
 *   4. drag and drop
 *   5. modal (create / edit)
 *   6. boot
 */

/* ---------------------------------------------------------------- 1. config */

const API_BASE = "http://127.0.0.1:8000";

// The board's columns, in display order. `key` matches the API's status value.
const COLUMNS = [
  { key: "todo", label: "ToDo" },
  { key: "in_progress", label: "In Progress" },
  { key: "done", label: "Done" },
];

const PRIORITY_LABELS = { low: "Low", medium: "Medium", high: "High" };

// Everything currently on the board, kept so drag-and-drop and the edit modal
// can work without re-fetching a single task.
let tasks = [];

const el = {
  board: document.getElementById("board"),
  status: document.getElementById("board-status"),
  toast: document.getElementById("toast"),
  newTaskButton: document.getElementById("new-task-button"),
  backdrop: document.getElementById("modal-backdrop"),
  modalTitle: document.getElementById("modal-title"),
  form: document.getElementById("task-form"),
  formError: document.getElementById("form-error"),
  close: document.getElementById("modal-close"),
  cancel: document.getElementById("modal-cancel"),
};

/** Escape text before putting it in innerHTML. Task titles are user input. */
function escapeHtml(value) {
  return String(value ?? "").replace(
    /[&<>"']/g,
    (char) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[char]
  );
}

function setStatus(message, isError = false) {
  el.status.textContent = message;
  el.status.classList.toggle("is-error", isError);
}

let toastTimer = null;
function showToast(message, isError = false) {
  el.toast.textContent = message;
  el.toast.classList.toggle("is-error", isError);
  el.toast.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => {
    el.toast.hidden = true;
  }, 3200);
}

/* ------------------------------------------------------------------- 2. API */

/** Turn a FastAPI error body into one readable sentence. */
function describeApiError(status, body) {
  const detail = body && body.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail.length) {
    // 422 validation errors: [{loc: ["body","title"], msg: "..."}]
    return detail
      .map((item) => {
        const field = Array.isArray(item.loc) ? item.loc[item.loc.length - 1] : "";
        return field ? `${field}: ${item.msg}` : item.msg;
      })
      .join("; ");
  }
  return `Request failed (HTTP ${status}).`;
}

/**
 * Call the API and return the parsed body.
 * Throws an Error with a readable message for any non-2xx response so callers
 * only need one catch block.
 */
async function apiRequest(path, options = {}) {
  let response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      headers: { "Content-Type": "application/json" },
      ...options,
    });
  } catch (networkError) {
    throw new Error(
      "Cannot reach the API. Is the backend running on http://127.0.0.1:8000 ?"
    );
  }

  if (response.status === 204) return null;

  let body = null;
  try {
    body = await response.json();
  } catch (parseError) {
    body = null;
  }

  if (!response.ok) {
    throw new Error(describeApiError(response.status, body));
  }
  return body;
}

const api = {
  listTasks: () => apiRequest("/tasks"),
  createTask: (payload) =>
    apiRequest("/tasks", { method: "POST", body: JSON.stringify(payload) }),
  updateTask: (id, payload) =>
    apiRequest(`/tasks/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  deleteTask: (id) => apiRequest(`/tasks/${id}`, { method: "DELETE" }),
};

/* ------------------------------------------------------------- 3. rendering */

function cardHtml(task) {
  const description = task.description
    ? escapeHtml(task.description)
    : "No description";

  return `
    <article class="card" draggable="true" data-id="${task.id}">
      <h3 class="card-title">${escapeHtml(task.title)}</h3>
      <p class="card-description">${description}</p>
      <div class="card-meta">
        <div class="card-badges">
          <span class="pill pill-${task.priority}">${PRIORITY_LABELS[task.priority]}</span>
          ${task.assignee ? `<span class="card-assignee">${escapeHtml(task.assignee)}</span>` : ""}
        </div>
        <div class="card-actions">
          <button class="button button-small" data-action="edit" data-id="${task.id}">Edit</button>
          <button class="button button-small button-danger" data-action="delete" data-id="${task.id}">Delete</button>
        </div>
      </div>
    </article>
  `;
}

function columnHtml(column, columnTasks) {
  const cards = columnTasks.length
    ? columnTasks.map(cardHtml).join("")
    : `<p class="column-empty">Nothing here yet.</p>`;

  return `
    <section class="column" data-status="${column.key}">
      <div class="column-header">
        <h2 class="column-title">${column.label}</h2>
        <span class="column-count">${columnTasks.length}</span>
      </div>
      ${cards}
    </section>
  `;
}

/** Repaint the whole board from the in-memory `tasks` array. */
function render() {
  el.board.innerHTML = COLUMNS.map((column) =>
    columnHtml(
      column,
      tasks.filter((task) => task.status === column.key)
    )
  ).join("");
}

/** Fetch tasks and repaint, handling loading / empty / error states. */
async function refresh() {
  setStatus("Loading tasks…");
  try {
    tasks = await api.listTasks();
    render();
    setStatus(
      tasks.length ? "" : "No tasks yet. Use “New Task” to create the first one."
    );
  } catch (error) {
    tasks = [];
    render();
    setStatus(error.message, true);
  }
}

/* ------------------------------------------------------- 4. drag and drop */

let draggedTaskId = null;

function onDragStart(event) {
  const card = event.target.closest(".card");
  if (!card) return;
  draggedTaskId = card.dataset.id;
  card.classList.add("is-dragging");
  event.dataTransfer.effectAllowed = "move";
  // Firefox needs data set on the transfer object for the drop to fire.
  event.dataTransfer.setData("text/plain", draggedTaskId);
}

function onDragEnd(event) {
  const card = event.target.closest(".card");
  if (card) card.classList.remove("is-dragging");
  draggedTaskId = null;
  document
    .querySelectorAll(".column.is-drop-target")
    .forEach((column) => column.classList.remove("is-drop-target"));
}

function onDragOver(event) {
  const column = event.target.closest(".column");
  if (!column) return;
  event.preventDefault(); // required for the drop event to fire
  column.classList.add("is-drop-target");
}

function onDragLeave(event) {
  const column = event.target.closest(".column");
  if (column && !column.contains(event.relatedTarget)) {
    column.classList.remove("is-drop-target");
  }
}

async function onDrop(event) {
  const column = event.target.closest(".column");
  if (!column || !draggedTaskId) return;
  event.preventDefault();
  column.classList.remove("is-drop-target");

  const taskId = draggedTaskId;
  const newStatus = column.dataset.status;
  const task = tasks.find((candidate) => candidate.id === taskId);
  if (!task || task.status === newStatus) return;

  try {
    // The backend rejects illegal transitions (e.g. todo -> done), so let it
    // decide and only repaint on success.
    const updated = await api.updateTask(taskId, { status: newStatus });
    tasks = tasks.map((candidate) => (candidate.id === taskId ? updated : candidate));
    render();
    setStatus("");
  } catch (error) {
    showToast(error.message, true);
    render(); // snap the card back to where it actually is
  }
}

/* -------------------------------------------------------------- 5. modal */

// null while creating, otherwise the id of the task being edited.
let editingTaskId = null;

function showFormError(message) {
  el.formError.textContent = message;
  el.formError.hidden = false;
}

function openModal(task = null) {
  editingTaskId = task ? task.id : null;
  el.modalTitle.textContent = task ? "Edit Task" : "New Task";
  el.formError.hidden = true;

  el.form.reset();
  el.form.title.value = task ? task.title : "";
  el.form.description.value = task && task.description ? task.description : "";
  el.form.status.value = task ? task.status : "todo";
  el.form.priority.value = task ? task.priority : "medium";
  el.form.assignee.value = task && task.assignee ? task.assignee : "";

  el.backdrop.hidden = false;
  el.form.title.focus();
}

function closeModal() {
  el.backdrop.hidden = true;
  editingTaskId = null;
}

/** Read the form into an API payload, omitting fields the user left blank. */
function readForm() {
  const payload = {
    title: el.form.title.value.trim(),
    status: el.form.status.value,
    priority: el.form.priority.value,
  };

  const description = el.form.description.value.trim();
  const assignee = el.form.assignee.value.trim();
  payload.description = description || null;
  payload.assignee = assignee || null;

  return payload;
}

async function onSubmit(event) {
  event.preventDefault();
  el.formError.hidden = true;

  const payload = readForm();
  if (!payload.title) {
    showFormError("Title is required.");
    return;
  }

  try {
    if (editingTaskId) {
      await api.updateTask(editingTaskId, payload);
      showToast("Task updated.");
    } else {
      await api.createTask(payload);
      showToast("Task created.");
    }
    closeModal();
    await refresh();
  } catch (error) {
    // Keep the modal open so the user does not lose what they typed.
    showFormError(error.message);
  }
}

async function onBoardClick(event) {
  const button = event.target.closest("button[data-action]");
  if (!button) return;

  const task = tasks.find((candidate) => candidate.id === button.dataset.id);
  if (!task) return;

  if (button.dataset.action === "edit") {
    openModal(task);
    return;
  }

  if (button.dataset.action === "delete") {
    if (!window.confirm(`Delete “${task.title}”?`)) return;
    try {
      await api.deleteTask(task.id);
      showToast("Task deleted.");
      await refresh();
    } catch (error) {
      showToast(error.message, true);
    }
  }
}

/* --------------------------------------------------------------- 6. boot */

el.newTaskButton.addEventListener("click", () => openModal());
el.close.addEventListener("click", closeModal);
el.cancel.addEventListener("click", closeModal);
el.form.addEventListener("submit", onSubmit);

// Clicking the dimmed area (but not the dialog) closes the modal.
el.backdrop.addEventListener("click", (event) => {
  if (event.target === el.backdrop) closeModal();
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && !el.backdrop.hidden) closeModal();
});

el.board.addEventListener("click", onBoardClick);
el.board.addEventListener("dragstart", onDragStart);
el.board.addEventListener("dragend", onDragEnd);
el.board.addEventListener("dragover", onDragOver);
el.board.addEventListener("dragleave", onDragLeave);
el.board.addEventListener("drop", onDrop);

refresh();
