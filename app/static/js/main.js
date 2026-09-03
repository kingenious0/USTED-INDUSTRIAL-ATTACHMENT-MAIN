// U-IAP Client Interactions (Vanilla JS per PRD Section 4)

document.addEventListener('DOMContentLoaded', () => {
  // 1. Auto-expanding Textareas (PRD Section 21: Expandable space without cramped paper lines)
  const autoExpand = (el) => {
    el.style.height = 'auto';
    el.style.height = (el.scrollHeight + 4) + 'px';
  };

  const expandables = document.querySelectorAll('.textarea-expandable');
  expandables.forEach((textarea) => {
    // Initial size adjustment
    autoExpand(textarea);
    textarea.addEventListener('input', () => autoExpand(textarea));
  });

  // 2. Modal Controller (for Confirmation Dialogs like Lock Week)
  window.openModal = (modalId) => {
    const modal = document.getElementById(modalId);
    if (modal) {
      modal.classList.add('show');
    }
  };

  window.closeModal = (modalId) => {
    const modal = document.getElementById(modalId);
    if (modal) {
      modal.classList.remove('show');
    }
  };

  // Close modal when clicking outside of modal-card
  document.querySelectorAll('.modal-backdrop').forEach((backdrop) => {
    backdrop.addEventListener('click', (e) => {
      if (e.target === backdrop) {
        backdrop.classList.remove('show');
      }
    });
  });

  // 3. Flash message auto-dismissal helper
  document.querySelectorAll('.flash-alert').forEach((alert) => {
    const closeBtn = alert.querySelector('.alert-close');
    if (closeBtn) {
      closeBtn.addEventListener('click', () => {
        alert.remove();
      });
    }
  });

  // 4. File input preview / file size warning
  const fileInput = document.querySelector('input[type="file"][name="acceptance_scan"]');
  if (fileInput) {
    fileInput.addEventListener('change', (e) => {
      const file = e.target.files[0];
      if (file) {
        const maxSize = 10 * 1024 * 1024; // 10MB
        if (file.size > maxSize) {
          alert('Warning: Selected file exceeds the 10 MB limit. Please choose a smaller scanned file or compress it.');
          fileInput.value = '';
        }
      }
    });
  }
});
