// U-IAP Client Interactions (Vanilla JavaScript)

document.addEventListener('DOMContentLoaded', () => {
  // 1. Mobile Navigation Drawer / Dropdown Toggle
  const navToggle = document.getElementById('navToggle');
  const navMenu = document.getElementById('navMenu');

  if (navToggle && navMenu) {
    navToggle.addEventListener('click', (e) => {
      e.stopPropagation();
      const isExpanded = navToggle.getAttribute('aria-expanded') === 'true';
      navToggle.setAttribute('aria-expanded', !isExpanded);
      navMenu.classList.toggle('is-open');
    });

    // Close menu when clicking outside
    document.addEventListener('click', (e) => {
      if (!navMenu.contains(e.target) && !navToggle.contains(e.target)) {
        navMenu.classList.remove('is-open');
        navToggle.setAttribute('aria-expanded', 'false');
      }
    });

    // Close on Escape key
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && navMenu.classList.contains('is-open')) {
        navMenu.classList.remove('is-open');
        navToggle.setAttribute('aria-expanded', 'false');
      }
    });
  }

  // 2. Auto-expanding Textareas (Expandable space for comprehensive daily logging)
  const autoExpand = (el) => {
    el.style.height = 'auto';
    el.style.height = (el.scrollHeight + 4) + 'px';
  };

  const expandables = document.querySelectorAll('.textarea-expandable');
  expandables.forEach((textarea) => {
    autoExpand(textarea);
    textarea.addEventListener('input', () => autoExpand(textarea));
  });

  // 3. Modal Controller (for Weekly Lock and Document Actions)
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

  document.querySelectorAll('.modal-backdrop').forEach((backdrop) => {
    backdrop.addEventListener('click', (e) => {
      if (e.target === backdrop) {
        backdrop.classList.remove('show');
      }
    });
  });

  // 4. Flash message dismissals
  document.querySelectorAll('.flash-alert').forEach((alert) => {
    const closeBtn = alert.querySelector('.alert-close');
    if (closeBtn) {
      closeBtn.addEventListener('click', () => {
        alert.remove();
      });
    }
  });

  // 5. File input size check (10MB max)
  const fileInput = document.querySelector('input[type="file"][name="acceptance_scan"]');
  if (fileInput) {
    fileInput.addEventListener('change', (e) => {
      const file = e.target.files[0];
      if (file) {
        const maxSize = 10 * 1024 * 1024;
        if (file.size > maxSize) {
          alert('Warning: The selected file exceeds the 10 MB limit. Please select a compressed PDF or image file.');
          fileInput.value = '';
        }
      }
    });
  }
});
