const dropArea = document.getElementById('drop-area');
const fileInput = document.getElementById('fileElem');
const uploadButton = document.getElementById('upload-button');
const previewArea = document.getElementById('preview-area');
const fileInfo = document.getElementById('file-info');
const previewImage = document.getElementById('preview-image');

// Prevent default drag behaviors
['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
    dropArea.addEventListener(eventName, preventDefaults, false);
    document.body.addEventListener(eventName, preventDefaults, false);
});

// Highlight drop area when item is dragged over it
['dragenter', 'dragover'].forEach(eventName => {
    dropArea.addEventListener(eventName, () => dropArea.classList.add('hover'), false);
});
['dragleave', 'drop'].forEach(eventName => {
    dropArea.addEventListener(eventName, () => dropArea.classList.remove('hover'), false);
});

// Handle dropped files
dropArea.addEventListener('drop', handleDrop, false);

function preventDefaults(e) {
    e.preventDefault();
    e.stopPropagation();
}

function handleDrop(e) {
    const dt = e.dataTransfer;
    const files = dt.files;
    handleFiles(files);
}

function handleFiles(files) {
    if (files.length > 0) {
        fileInput.files = files;
        displayPreview(files[0]);
    }
}

// Open file selector when drag area is clicked
dropArea.addEventListener('click', () => {
    fileInput.click();
});

// Show preview and file details after file selection
fileInput.addEventListener('change', () => {
    if (fileInput.files.length > 0) {
        displayPreview(fileInput.files[0]);
    }
});

function displayPreview(file) {
    dropArea.style.display = 'none';

    fileInfo.textContent = `File: ${file.name}, Size: ${Math.round(file.size / 1024)} KB`;

    const reader = new FileReader();
    reader.onload = (e) => {
        previewImage.src = e.target.result;
    };
    reader.readAsDataURL(file);

    previewArea.style.display = 'block';
}
