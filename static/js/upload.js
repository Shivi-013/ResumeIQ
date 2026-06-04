(function () {
  const dropZone    = document.getElementById('dropZone');
  const fileInput   = document.getElementById('resumeInput');
  const dropDefault = document.getElementById('dropDefault');
  const dropSelected= document.getElementById('dropSelected');
  const fileNameEl  = document.getElementById('selectedFileName');
  const fileError   = document.getElementById('fileError');
  const jdTextarea  = document.getElementById('jobDescription');
  const charCount   = document.getElementById('charCount');
  const jdError     = document.getElementById('jdError');
  const form        = document.getElementById('analyzeForm');
  const submitBtn   = document.getElementById('submitBtn');
  const btnText     = document.getElementById('btnText');
  const btnLoading  = document.getElementById('btnLoading');

  const MAX_SIZE = 5 * 1024 * 1024;

  // ── File selection ──
  function showFile(file) {
    fileError.classList.add('hidden');
    if (!file) return;
    if (file.type !== 'application/pdf' && !file.name.toLowerCase().endsWith('.pdf')) {
      fileError.textContent = 'Only PDF files are accepted.';
      fileError.classList.remove('hidden');
      resetDropZone();
      return;
    }
    if (file.size > MAX_SIZE) {
      fileError.textContent = 'File exceeds 5 MB limit.';
      fileError.classList.remove('hidden');
      resetDropZone();
      return;
    }
    fileNameEl.textContent = file.name;
    dropDefault.classList.add('hidden');
    dropSelected.classList.remove('hidden');
  }

  function resetDropZone() {
    dropDefault.classList.remove('hidden');
    dropSelected.classList.add('hidden');
    fileInput.value = '';
  }

  fileInput.addEventListener('change', () => {
    if (fileInput.files.length) showFile(fileInput.files[0]);
  });

  // ── Drag & drop ──
  dropZone.addEventListener('dragover', e => {
    e.preventDefault();
    dropZone.classList.add('drop-over');
  });
  ['dragleave', 'dragend'].forEach(ev =>
    dropZone.addEventListener(ev, () => dropZone.classList.remove('drop-over'))
  );
  dropZone.addEventListener('drop', e => {
    e.preventDefault();
    dropZone.classList.remove('drop-over');
    const dt = e.dataTransfer;
    if (dt.files.length) {
      fileInput.files = dt.files;  // works in modern browsers
      showFile(dt.files[0]);
    }
  });

  // ── Character counter ──
  if (jdTextarea) {
    jdTextarea.addEventListener('input', () => {
      charCount.textContent = jdTextarea.value.length;
      if (jdTextarea.value.length >= 4800) {
        charCount.classList.add('text-red-400');
      } else {
        charCount.classList.remove('text-red-400');
      }
    });
  }

  // ── Form validation & loading state ──
  if (form) {
    form.addEventListener('submit', e => {
      let valid = true;

      // File check
      if (!fileInput.files.length || !fileInput.files[0]) {
        fileError.textContent = 'Please select a PDF resume.';
        fileError.classList.remove('hidden');
        valid = false;
      }

      // JD check
      const jd = jdTextarea ? jdTextarea.value.trim() : '';
      if (jd.length < 100) {
        jdError.textContent = 'Job description must be at least 100 characters.';
        jdError.classList.remove('hidden');
        valid = false;
      } else {
        jdError.classList.add('hidden');
      }

      if (!valid) { e.preventDefault(); return; }

      // Show loading state
      btnText.classList.add('hidden');
      btnLoading.classList.remove('hidden');
      submitBtn.disabled = true;
    });
  }
})();
