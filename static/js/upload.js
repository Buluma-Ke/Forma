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

document.getElementById('uploadForm').addEventListener('submit', () => {
  document.getElementById('submitBtn').textContent = 'Extracting...';
  document.getElementById('submitBtn').style.opacity = '0.7';
});