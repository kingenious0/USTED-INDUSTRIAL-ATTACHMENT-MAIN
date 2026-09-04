// U-IAP Client Interactions & Offline-Resilient Auto-Saving (Vanilla JavaScript)

document.addEventListener('DOMContentLoaded', () => {
  // 1. Mobile Navigation Sidebar Drawer Controller (< 1024px)
  const sidebar = document.getElementById('appSidebar');
  const sidebarToggles = document.querySelectorAll('.sidebar-toggle-btn, .header-toggle-sidebar, #sidebarToggle');
  const sidebarClose = document.getElementById('sidebarClose');
  const sidebarBackdrop = document.getElementById('sidebarBackdrop');

  const openSidebar = () => {
    if (sidebar) {
      sidebar.classList.add('sidebar-open');
      if (sidebarBackdrop) sidebarBackdrop.classList.add('active');
      sidebarToggles.forEach(btn => btn.setAttribute('aria-expanded', 'true'));
      document.body.style.overflow = 'hidden'; // prevent background scrolling while drawer is open
    }
  };

  const closeSidebar = () => {
    if (sidebar) {
      sidebar.classList.remove('sidebar-open');
      if (sidebarBackdrop) sidebarBackdrop.classList.remove('active');
      sidebarToggles.forEach(btn => btn.setAttribute('aria-expanded', 'false'));
      document.body.style.overflow = '';
    }
  };

  sidebarToggles.forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      openSidebar();
    });
  });

  if (sidebarClose) {
    sidebarClose.addEventListener('click', closeSidebar);
  }

  if (sidebarBackdrop) {
    sidebarBackdrop.addEventListener('click', closeSidebar);
  }

  // Close sidebar on Escape key
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && sidebar && sidebar.classList.contains('sidebar-open')) {
      closeSidebar();
    }
  });

  // 2. Auto-expanding Textareas
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
      document.body.style.overflow = 'hidden';
    }
  };

  window.closeModal = (modalId) => {
    const modal = document.getElementById(modalId);
    if (modal) {
      modal.classList.remove('show');
      document.body.style.overflow = '';
    }
  };

  document.querySelectorAll('.modal-backdrop').forEach((backdrop) => {
    backdrop.addEventListener('click', (e) => {
      if (e.target === backdrop) {
        backdrop.classList.remove('show');
        document.body.style.overflow = '';
      }
    });
  });

  // 4. Flash Message Dismissals
  document.querySelectorAll('.flash-alert').forEach((alert) => {
    const closeBtn = alert.querySelector('.alert-close');
    if (closeBtn) {
      closeBtn.addEventListener('click', () => {
        alert.remove();
      });
    }
  });

  // 5. Client-Side Auto-Save to localStorage for eLogSheet (Pipeline 3)
  const activityForms = document.querySelectorAll('.daily-activity-form');
  activityForms.forEach((form) => {
    const entryId = form.getAttribute('data-entry-id');
    if (!entryId) return;

    const storageKey = `uiap_draft_entry_${entryId}`;
    const badge = form.querySelector('.autosave-badge') || document.getElementById('autoSaveBadge');

    // Restore draft if present and inputs are empty
    try {
      const savedData = localStorage.getItem(storageKey);
      if (savedData) {
        const parsed = JSON.parse(savedData);
        const tasksField = form.querySelector('[name="key_tasks"]');
        const skillsField = form.querySelector('[name="skills_demonstrated"]');
        const remarksField = form.querySelector('[name="remarks"]');
        const startField = form.querySelector('[name="start_time"]');
        const endField = form.querySelector('[name="end_time"]');

        // Only restore if current form values are blank
        if (tasksField && !tasksField.value.trim() && parsed.key_tasks) {
          tasksField.value = parsed.key_tasks;
          autoExpand(tasksField);
        }
        if (skillsField && !skillsField.value.trim() && parsed.skills_demonstrated) {
          skillsField.value = parsed.skills_demonstrated;
          autoExpand(skillsField);
        }
        if (remarksField && !remarksField.value.trim() && parsed.remarks) {
          remarksField.value = parsed.remarks;
        }
        if (startField && parsed.start_time) startField.value = parsed.start_time;
        if (endField && parsed.end_time) endField.value = parsed.end_time;

        if (badge && (parsed.key_tasks || parsed.skills_demonstrated)) {
          badge.textContent = `Restored draft from ${new Date(parsed.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
          badge.style.display = 'inline-flex';
        }
      }
    } catch (err) {
      console.warn('Could not read draft from localStorage:', err);
    }

    // Debounced Auto-save to localStorage
    let saveTimeout = null;
    const triggerAutoSave = () => {
      clearTimeout(saveTimeout);
      saveTimeout = setTimeout(() => {
        try {
          const tasksField = form.querySelector('[name="key_tasks"]');
          const skillsField = form.querySelector('[name="skills_demonstrated"]');
          const remarksField = form.querySelector('[name="remarks"]');
          const startField = form.querySelector('[name="start_time"]');
          const endField = form.querySelector('[name="end_time"]');

          const payload = {
            key_tasks: tasksField ? tasksField.value : '',
            skills_demonstrated: skillsField ? skillsField.value : '',
            remarks: remarksField ? remarksField.value : '',
            start_time: startField ? startField.value : '',
            end_time: endField ? endField.value : '',
            timestamp: new Date().toISOString()
          };

          localStorage.setItem(storageKey, JSON.stringify(payload));
          if (badge) {
            badge.textContent = `Draft saved ${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
            badge.style.display = 'inline-flex';
          }
        } catch (err) {
          console.warn('Draft auto-save failed:', err);
        }
      }, 500);
    };

    form.querySelectorAll('input, textarea').forEach((input) => {
      input.addEventListener('input', triggerAutoSave);
    });

    // Clear saved draft on form submit
    form.addEventListener('submit', () => {
      try {
        localStorage.removeItem(storageKey);
      } catch (err) {
        // ignore
      }
    });
  });

  // 6. Acceptance Form Scan File Validation (Max 5MB per PRD Pipeline 2)
  const fileInput = document.querySelector('input[type="file"][name="acceptance_scan"]');
  if (fileInput) {
    fileInput.addEventListener('change', (e) => {
      const file = e.target.files[0];
      if (file) {
        const maxSize = 5 * 1024 * 1024; // 5 MB
        const allowedExts = ['pdf', 'png', 'jpg', 'jpeg'];
        const ext = file.name.split('.').pop().toLowerCase();

        if (!allowedExts.includes(ext)) {
          alert(`Invalid file format ".${ext}". Permitted formats: PDF, PNG, JPG, JPEG.`);
          fileInput.value = '';
          return;
        }

        if (file.size > maxSize) {
          alert(`File size (${(file.size / (1024 * 1024)).toFixed(1)} MB) exceeds the maximum allowed 5 MB limit. Please compress your document.`);
          fileInput.value = '';
          return;
        }
      }
    });
  }

  // 7. Weekday Pills Quick Filter for Mobile Viewport
  const weekdayPills = document.querySelectorAll('.weekday-pill');
  const dayCards = document.querySelectorAll('.daily-card');
  if (weekdayPills.length > 0 && dayCards.length > 0) {
    weekdayPills.forEach((pill) => {
      pill.addEventListener('click', (e) => {
        e.preventDefault();
        const selectedDay = pill.getAttribute('data-day');

        weekdayPills.forEach((p) => p.classList.remove('active'));
        pill.classList.add('active');

        dayCards.forEach((card) => {
          if (selectedDay === 'all' || card.getAttribute('data-day') === selectedDay) {
            card.style.display = '';
          } else {
            card.style.display = 'none';
          }
        });
      });
    });
  }
});

// 8. User Profile Dropdown Controller (Top Navigation Header)
window.toggleUserDropdown = function(event) {
  if (event) event.stopPropagation();
  const menu = document.getElementById('userDropdownMenu');
  const btn = document.getElementById('userMenuBtn');
  if (!menu) return;
  const isHidden = menu.style.display === 'none' || !menu.style.display;
  menu.style.display = isHidden ? 'block' : 'none';
  if (btn) btn.setAttribute('aria-expanded', isHidden ? 'true' : 'false');
};

document.addEventListener('click', function(e) {
  const menu = document.getElementById('userDropdownMenu');
  const btn = document.getElementById('userMenuBtn');
  if (menu && menu.style.display === 'block') {
    if (!menu.contains(e.target) && (!btn || !btn.contains(e.target))) {
      menu.style.display = 'none';
      if (btn) btn.setAttribute('aria-expanded', 'false');
    }
  }
});

