// Skill Swap Management System - SQL Query Console JavaScript

let sqlEditor = null;
const HISTORY_KEY = "skillswap_sql_history";

document.addEventListener("DOMContentLoaded", function () {
  const textarea = document.getElementById("sqlQueryEditor");
  if (!textarea) return;

  // Initialize CodeMirror 5
  sqlEditor = CodeMirror.fromTextArea(textarea, {
    mode: "text/x-mysql",
    lineNumbers: true,
    theme: "default",
    indentWithTabs: true,
    smartIndent: true,
    matchBrackets: true,
    autofocus: true,
    extraKeys: {
      "Ctrl-Enter": function () {
        runQuery();
      },
      "Cmd-Enter": function () {
        runQuery();
      }
    }
  });

  // Query Execution Button
  const runBtn = document.getElementById("btnRunQuery");
  if (runBtn) {
    runBtn.addEventListener("click", runQuery);
  }

  // Clear Editor Button
  const clearBtn = document.getElementById("btnClearQuery");
  if (clearBtn) {
    clearBtn.addEventListener("click", function () {
      sqlEditor.setValue("");
      sqlEditor.focus();
    });
  }

  // Sample Queries Dropdown
  const sampleSelect = document.getElementById("sampleQueriesSelect");
  if (sampleSelect) {
    sampleSelect.addEventListener("change", function () {
      const selectedSql = this.value;
      if (selectedSql) {
        sqlEditor.setValue(selectedSql);
        sqlEditor.focus();
      }
    });
  }

  // Write Mode Toggle Logic (Admin only)
  const writeModeSwitch = document.getElementById("writeModeSwitch");
  if (writeModeSwitch) {
    writeModeSwitch.addEventListener("change", function () {
      if (this.checked) {
        const confirmWrite = confirm(
          "WARNING: Write Mode allows INSERT, UPDATE, and DELETE operations which will modify the database. Do you wish to continue?"
        );
        if (!confirmWrite) {
          this.checked = false;
        } else {
          document.getElementById("writeModeBadge").className = "badge bg-danger ms-2";
          document.getElementById("writeModeBadge").textContent = "Write Mode (Active)";
        }
      } else {
        document.getElementById("writeModeBadge").className = "badge bg-success ms-2";
        document.getElementById("writeModeBadge").textContent = "Safe Mode (Read-Only)";
      }
    });
  }

  // Schema Explorer: Table click inserts SELECT * FROM `table` LIMIT 10;
  document.querySelectorAll(".schema-table-insert").forEach(function (el) {
    el.addEventListener("click", function (e) {
      e.stopPropagation();
      const tableName = this.getAttribute("data-table");
      const query = `SELECT * FROM \`${tableName}\` LIMIT 10;`;
      sqlEditor.setValue(query);
      sqlEditor.focus();
    });
  });

  // Export to CSV Button
  const exportBtn = document.getElementById("btnExportCSV");
  if (exportBtn) {
    exportBtn.addEventListener("click", exportActiveTableToCSV);
  }

  // Reset Database Button (Admin only)
  const resetBtn = document.getElementById("btnResetDatabase");
  if (resetBtn) {
    resetBtn.addEventListener("click", handleResetDatabase);
  }

  // Clear History Button
  const clearHistoryBtn = document.getElementById("btnClearHistory");
  if (clearHistoryBtn) {
    clearHistoryBtn.addEventListener("click", function () {
      localStorage.removeItem(HISTORY_KEY);
      renderHistory();
    });
  }

  // Load Initial History
  renderHistory();
});

// Run Query via AJAX
function runQuery() {
  if (!sqlEditor) return;
  const sql = sqlEditor.getValue().trim();
  if (!sql) {
    alert("Please enter a SQL query to execute.");
    return;
  }

  const writeModeSwitch = document.getElementById("writeModeSwitch");
  const writeMode = writeModeSwitch ? writeModeSwitch.checked : false;

  const runBtn = document.getElementById("btnRunQuery");
  const spinner = document.getElementById("runSpinner");
  const resultsContainer = document.getElementById("queryResultsContainer");

  if (runBtn) runBtn.disabled = true;
  if (spinner) spinner.classList.remove("d-none");

  // Save to history
  saveQueryToHistory(sql);

  fetch("/sql/run", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      sql: sql,
      write_mode: writeMode
    })
  })
    .then((res) => res.json())
    .then((data) => {
      renderResults(data);
    })
    .catch((err) => {
      renderResults({
        success: false,
        error: "Network / Connection error: " + err.message
      });
    })
    .finally(() => {
      if (runBtn) runBtn.disabled = false;
      if (spinner) spinner.classList.add("d-none");
      renderHistory();
    });
}

// Render Results Section
function renderResults(data) {
  const container = document.getElementById("queryResultsContainer");
  const exportBtn = document.getElementById("btnExportCSV");
  if (!container) return;

  container.innerHTML = "";

  if (!data.success) {
    if (exportBtn) exportBtn.disabled = true;
    const alertBox = document.createElement("div");
    alertBox.className = "alert alert-danger shadow-sm border-danger-subtle";
    alertBox.innerHTML = `
      <div class="d-flex align-items-center">
        <i class="bi bi-exclamation-triangle-fill fs-4 me-3"></i>
        <div>
          <h6 class="alert-heading fw-bold mb-1">Execution Error</h6>
          <div>${escapeHtml(data.error || "An unknown error occurred.")}</div>
          ${data.statement ? `<pre class="mt-2 p-2 bg-dark text-light rounded small mb-0"><code>${escapeHtml(data.statement)}</code></pre>` : ""}
        </div>
      </div>
    `;
    container.appendChild(alertBox);
    return;
  }

  const results = data.results || [];
  if (results.length === 0) {
    container.innerHTML = `<div class="alert alert-info">Query executed successfully with no output.</div>`;
    if (exportBtn) exportBtn.disabled = true;
    return;
  }

  let hasSelectTable = false;

  results.forEach((res, idx) => {
    const card = document.createElement("div");
    card.className = "card mb-4 shadow-sm";

    // Card Header
    const cardHeader = document.createElement("div");
    cardHeader.className = "card-header bg-light d-flex justify-content-between align-items-center py-2";

    let badgeHtml = "";
    if (res.type === "select") {
      hasSelectTable = true;
      badgeHtml = `
        <span class="badge bg-primary me-2"><i class="bi bi-table me-1"></i> SELECT</span>
        <span class="badge bg-secondary me-2">${res.row_count} rows</span>
        <span class="badge bg-light text-dark border">${res.execution_time_ms} ms</span>
      `;
    } else {
      badgeHtml = `
        <span class="badge bg-success me-2"><i class="bi bi-pencil-square me-1"></i> DML</span>
        <span class="badge bg-secondary me-2">${res.affected_rows} affected</span>
        <span class="badge bg-light text-dark border">${res.execution_time_ms} ms</span>
      `;
    }

    cardHeader.innerHTML = `
      <div class="small text-truncate me-2" style="max-width: 65%;">
        <strong>Statement #${idx + 1}:</strong> <code>${escapeHtml(res.statement)}</code>
      </div>
      <div>${badgeHtml}</div>
    `;
    card.appendChild(cardHeader);

    // Card Body
    const cardBody = document.createElement("div");
    cardBody.className = "card-body p-0";

    if (res.type === "select") {
      if (res.columns.length === 0 || res.rows.length === 0) {
        cardBody.innerHTML = `
          <div class="p-3 text-center text-muted">
            <i class="bi bi-inbox fs-3 d-block mb-1"></i> Empty set (0 rows returned)
          </div>
        `;
      } else {
        let tableHtml = `<div class="sql-result-table-wrap"><table class="table table-hover table-striped table-bordered table-sm mb-0 result-table"><thead><tr>`;
        tableHtml += `<th class="text-center" style="width: 45px;">#</th>`;
        res.columns.forEach((col) => {
          tableHtml += `<th>${escapeHtml(col)}</th>`;
        });
        tableHtml += `</tr></thead><tbody>`;

        res.rows.forEach((row, rowIdx) => {
          tableHtml += `<tr><td class="text-center text-muted small">${rowIdx + 1}</td>`;
          row.forEach((val) => {
            if (val === null) {
              tableHtml += `<td><span class="null-cell">NULL</span></td>`;
            } else {
              tableHtml += `<td>${escapeHtml(String(val))}</td>`;
            }
          });
          tableHtml += `</tr>`;
        });

        tableHtml += `</tbody></table></div>`;
        if (res.capped) {
          tableHtml += `<div class="p-2 bg-warning-subtle text-warning-emphasis small text-center"><i class="bi bi-info-circle me-1"></i> Output capped at 1000 rows.</div>`;
        }
        cardBody.innerHTML = tableHtml;
      }
    } else {
      cardBody.innerHTML = `
        <div class="p-3">
          <div class="alert alert-success mb-0 d-flex align-items-center">
            <i class="bi bi-check-circle-fill fs-4 me-3"></i>
            <div>
              <strong>Success!</strong> ${res.affected_rows} row(s) affected.
              ${res.last_insert_id ? `<span class="ms-2 badge bg-dark">Last Insert ID: ${res.last_insert_id}</span>` : ""}
            </div>
          </div>
        </div>
      `;
    }

    card.appendChild(cardBody);
    container.appendChild(card);
  });

  if (exportBtn) {
    exportBtn.disabled = !hasSelectTable;
  }
}

// Export active result table to CSV
function exportActiveTableToCSV() {
  const table = document.querySelector(".result-table");
  if (!table) {
    alert("No table results available to export.");
    return;
  }

  let csv = [];
  const rows = table.querySelectorAll("tr");

  for (let i = 0; i < rows.length; i++) {
    let row = [];
    const cols = rows[i].querySelectorAll("th, td");
    // Skip row number (first column)
    for (let j = 1; j < cols.length; j++) {
      let data = cols[j].innerText.replace(/"/g, '""');
      row.push('"' + data + '"');
    }
    csv.push(row.join(","));
  }

  const csvContent = "data:text/csv;charset=utf-8," + csv.join("\n");
  const encodedUri = encodeURI(csvContent);
  const link = document.createElement("a");
  link.setAttribute("href", encodedUri);
  link.setAttribute("download", `sql_result_${new Date().toISOString().slice(0, 19).replace(/[:T]/g, "_")}.csv`);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}

// Database Reset via AJAX
function handleResetDatabase() {
  const confirmed = confirm(
    "ARE YOU ABSOLUTELY SURE?\n\nThis will re-run schema.sql and seed.sql, completely resetting the database and all demonstration data."
  );
  if (!confirmed) return;

  const btn = document.getElementById("btnResetDatabase");
  if (btn) btn.disabled = true;

  fetch("/sql/reset", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    }
  })
    .then((res) => res.json())
    .then((data) => {
      if (data.success) {
        alert("Database successfully reset to initial schema and seed data!");
        window.location.reload();
      } else {
        alert("Failed to reset database: " + data.error);
      }
    })
    .catch((err) => {
      alert("Error contacting reset route: " + err.message);
    })
    .finally(() => {
      if (btn) btn.disabled = false;
    });
}

// Query History Helpers
function saveQueryToHistory(sql) {
  let history = getHistory();
  // Remove duplicate if already present
  history = history.filter((q) => q !== sql);
  history.unshift(sql);
  if (history.length > 20) history = history.slice(0, 20);
  localStorage.setItem(HISTORY_KEY, JSON.stringify(history));
}

function getHistory() {
  try {
    return JSON.parse(localStorage.getItem(HISTORY_KEY)) || [];
  } catch (e) {
    return [];
  }
}

function renderHistory() {
  const container = document.getElementById("queryHistoryList");
  if (!container) return;

  const history = getHistory();
  if (history.length === 0) {
    container.innerHTML = `<div class="p-2 text-muted small text-center">No queries run yet.</div>`;
    return;
  }

  container.innerHTML = "";
  history.forEach((query) => {
    const item = document.createElement("div");
    item.className = "history-item";
    item.title = query;
    item.textContent = query;
    item.addEventListener("click", function () {
      if (sqlEditor) {
        sqlEditor.setValue(query);
        sqlEditor.focus();
      }
    });
    container.appendChild(item);
  });
}

function escapeHtml(text) {
  if (!text) return "";
  const map = {
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#039;"
  };
  return String(text).replace(/[&<>"']/g, function (m) {
    return map[m];
  });
}
