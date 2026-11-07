
const fileInput = document.getElementById("blueprint");
const dropzone = document.getElementById("dropzone");
const fileInfo = document.getElementById("file-info");
const reviewButton = document.getElementById("review-button");
const message = document.getElementById("upload-message");
const connectionStatus = document.getElementById("connection-status");
const drawingCount = document.getElementById("drawing-count");

const MAX_SIZE = 10 * 1024 * 1024;
const allowedExtensions = ["pdf"];

let selectedFile = null;

async function checkBackend() {
  try {
    const response = await fetch("/health");

    if (!response.ok) {
      throw new Error("Health check failed");
    }

    const data = await response.json();

    connectionStatus.textContent =
      data.status === "healthy" ? "Backend connected" : "Unexpected response";
  } catch {
    connectionStatus.textContent = "Backend unavailable";
  }
}

function showMessage(text, type = "") {
  message.textContent = text;
  message.className = `message ${type}`.trim();
}

function clearSelection() {
  selectedFile = null;
  reviewButton.disabled = true;
  fileInput.value = "";
  drawingCount.textContent = "00";
}

function handleFile(file) {
  clearSelection();
  showMessage("");

  if (!file) {
    fileInfo.textContent = "No drawing selected";
    return;
  }

  const parts = file.name.split(".");
  const extension = parts.length > 1
    ? parts.pop().toLowerCase()
    : "";

  if (!allowedExtensions.includes(extension)) {
    fileInfo.textContent = "No drawing selected";
    showMessage("Unsupported file type. Choose PDF, PNG or JPG.", "error");
    return;
  }

  if (file.size === 0) {
    fileInfo.textContent = "No drawing selected";
    showMessage("This file is empty. Choose another file.", "error");
    return;
  }

  if (file.size > MAX_SIZE) {
    fileInfo.textContent = "No drawing selected";
    showMessage("The file exceeds the 10 MB limit.", "error");
    return;
  }

  selectedFile = file;
  fileInfo.textContent =
    `${file.name} · ${(file.size / 1024).toFixed(1)} KB`;

  reviewButton.disabled = false;
  drawingCount.textContent = "01";

  showMessage("File selected locally. It has not been uploaded.", "success");
}

fileInput.addEventListener("change", () => {
  handleFile(fileInput.files[0]);
});

dropzone.addEventListener("dragover", (event) => {
  event.preventDefault();
  dropzone.classList.add("dragover");
});

dropzone.addEventListener("dragleave", () => {
  dropzone.classList.remove("dragover");
});

dropzone.addEventListener("drop", (event) => {
  event.preventDefault();
  dropzone.classList.remove("dragover");

  const file = event.dataTransfer.files[0];

  if (!file) return;

  handleFile(file);
});

reviewButton.addEventListener("click", () => {
  if (!selectedFile) return;
  
const analysisResult = document.getElementById("analysis-result");

reviewButton.addEventListener("click", async () => {
  if (!selectedFile) return;

  const fileToUpload = selectedFile;
  const formData = new FormData();
  formData.append("file", fileToUpload);

  reviewButton.disabled = true;
  reviewButton.textContent = "Uploading PDF...";
  analysisResult.hidden = true;
  analysisResult.replaceChildren();

  showMessage("Sending PDF to the Python backend...");

  try {
    const response = await fetch("/api/upload", {
      method: "POST",
      body: formData
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || "The upload failed.");
    }

    const heading = document.createElement("h3");
    heading.textContent = "PDF processing result";

    const status = document.createElement("p");
    status.className = "result-status";
    status.textContent =
      data.extraction_status === "text_extracted"
        ? "Text extraction successful"
        : "No embedded text found";

    const summary = document.createElement("p");
    summary.textContent =
      `File: ${data.filename} | Pages: ${data.page_count} | ` +
      `Characters: ${data.characters_extracted}`;

    const explanation = document.createElement("p");
    explanation.textContent = data.message;

    analysisResult.append(
      heading,
      status,
      summary,
      explanation
    );

    if (data.extracted_text) {
      const label = document.createElement("h3");
      label.textContent = "Extracted drawing text";

      const output = document.createElement("pre");
      output.textContent = data.extracted_text;

      analysisResult.append(label, output);
    }

    analysisResult.hidden = false;
    showMessage("The backend processed your PDF.", "success");

  } catch (error) {
    showMessage(
      error.message || "Unable to contact the backend.",
      "error"
    );
  } finally {
    reviewButton.textContent = "Upload and extract text";
    reviewButton.disabled = !selectedFile;
  }
});

reviewButton.textContent = "Upload and extract text";


  showMessage(
    "Interface test passed. Actual upload and drawing analysis " +
    "will be implemented in the next stage.",
    "success"
  );
});

checkBackend();
