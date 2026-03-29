// Drop zone
const dropZone = document.getElementById('dropZone');
const fileInput = document.getElementById('id_image');
const filePreview = document.getElementById('filePreview');
const fileName = document.getElementById('fileName');

dropZone.addEventListener('dragover', e => {
  e.preventDefault();
  dropZone.classList.add('dragover');
});

dropZone.addEventListener('dragleave', () => {
  dropZone.classList.remove('dragover');
});

dropZone.addEventListener('drop', e => {
  e.preventDefault();
  dropZone.classList.remove('dragover');
  if (e.dataTransfer.files[0]) {
    fileInput.files = e.dataTransfer.files;
    showFile(e.dataTransfer.files[0].name);
  }
});

fileInput.addEventListener('change', () => {
  if (fileInput.files[0]) showFile(fileInput.files[0].name);
});

function showFile(name) {
  fileName.textContent = name;
  filePreview.classList.add('show');
}

function removeFile() {
  fileInput.value = '';
  filePreview.classList.remove('show');
}

// Loading spinner
document.getElementById('uploadForm').addEventListener('submit', () => {
  document.getElementById('spinnerOverlay').classList.add('show');
});

// Highlight edited cells
function highlightEdited(input) {
  input.classList.add('edited');
}

// Add row
function addRow() {
  const table = document.getElementById('previewTable');
  const numCols = table.rows[0] ? table.rows[0].cells.length - 1 : 1;
  const rowIndex = table.rows.length;
  const tr = document.createElement('tr');
  for (let c = 0; c < numCols; c++) {
    const td = document.createElement('td');
    const input = document.createElement('input');
    input.type = 'text';
    input.name = `cell_${rowIndex}_${c}`;
    input.setAttribute('form', 'downloadForm');
    input.addEventListener('input', () => highlightEdited(input));
    td.appendChild(input);
    tr.appendChild(td);
  }
  // delete button cell
  const deleteTd = document.createElement('td');
  const deleteBtn = document.createElement('button');
  deleteBtn.type = 'button';
  deleteBtn.className = 'row-delete';
  deleteBtn.textContent = '×';
  deleteBtn.onclick = function() { deleteRow(this); };
  deleteTd.appendChild(deleteBtn);
  tr.appendChild(deleteTd);
  table.appendChild(tr);
  renameInputs();
}

// Add column
function addCol() {
  const table = document.getElementById('previewTable');
  Array.from(table.rows).forEach((row, r) => {
    const td = document.createElement('td');
    const input = document.createElement('input');
    input.type = 'text';
    input.name = `cell_${r}_${row.cells.length - 1}`;
    input.setAttribute('form', 'downloadForm');
    input.addEventListener('input', () => highlightEdited(input));
    td.appendChild(input);
    // insert before the delete button cell
    row.insertBefore(td, row.cells[row.cells.length - 1]);
  });
  renameInputs();
}


// Delete first row
function deleteFirstRow() {
  const table = document.getElementById('previewTable');
  if (table.rows.length > 1) {
    table.deleteRow(0);
    renameInputs();
  }
}

// Delete first column
function deleteFirstCol() {
  const table = document.getElementById('previewTable');
  Array.from(table.rows).forEach(row => {
    if (row.cells.length > 2) {
      row.deleteCell(0);
    }
  });
  renameInputs();
}



// Delete last row
function deleteLastRow() {
  const table = document.getElementById('previewTable');
  if (table.rows.length > 1) {
    table.deleteRow(table.rows.length - 1);
    renameInputs();
  }
}

// Delete last column
function deleteLastCol() {
  const table = document.getElementById('previewTable');
  Array.from(table.rows).forEach(row => {
    if (row.cells.length > 2) {
      row.deleteCell(row.cells.length - 2);
    }
  });
  renameInputs();
}

// Delete specific row
function deleteRow(btn) {
  const row = btn.closest('tr');
  row.parentNode.removeChild(row);
  renameInputs();
}

// Rename all inputs after structural changes
function renameInputs() {
  const table = document.getElementById('previewTable');
  Array.from(table.rows).forEach((row, r) => {
    const inputs = row.querySelectorAll('input');
    inputs.forEach((input, c) => {
      input.name = `cell_${r}_${c}`;
    });
  });
}