/**
 * DCM System - Draggable Elements Controller (Signatures & Headers)
 * Enables smooth, free repositioning of signature groups and official letterhead blocks
 * (Ministry logo/name & Kingdom header) using mouse/touch across all PDF/print views.
 * Preserves 100% position fidelity when printed or exported as PDF.
 */

(function () {
    'use strict';

    // Candidate selectors for signature and official letterhead blocks across templates
    const DEFAULT_DRAGGABLE_SELECTORS = [
        '.sig-draggable',
        '.header-draggable',
        // Official Letterhead (Logo, Ministry, Kingdom Motto)
        '.doc-header-left',
        '.doc-header-right',
        '.royal-header',
        '.kingdom-header',
        '.header-section > .header-left',
        '.header-section > .header-right',
        '.header-layout .header-center',
        // Official Signatures
        '.roster-sig-col',
        '.sig-box',
        '.sig-block',
        '.signature-box',
        '.d1-bottom-section > div',
        '.e1-bottom-section > div:nth-child(2)',
        '.bottom-section .bottom-right',
        '.vehicle-signatures-box',
        'table.sign-table td'
    ];

    let activeDrag = null;

    /**
     * Check if the element belongs to official document letterhead.
     */
    function isHeaderElement(el) {
        if (!el) return false;
        if (el.classList.contains('header-draggable') ||
            el.classList.contains('doc-header-left') ||
            el.classList.contains('doc-header-right') ||
            el.classList.contains('royal-header') ||
            el.classList.contains('kingdom-header')) {
            return true;
        }
        if (el.closest('.doc-header') || el.closest('.royal-header') || el.closest('.header-section') || el.closest('.header-table')) {
            return true;
        }
        const text = el.textContent || '';
        return text.includes('ព្រះរាជាណាចក្រកម្ពុជា') ||
               text.includes('ក្រសួងកសិកម្ម') ||
               text.includes('មន្ទីរកសិកម្ម');
    }

    /**
     * Determine the effective zoom/scale factor applied to the target element.
     */
    function getZoomScale(el) {
        if (typeof window.currentZoom === 'number' && window.currentZoom > 0) {
            return window.currentZoom;
        }

        let scale = 1.0;
        let curr = el;
        while (curr && curr !== document.body && curr !== document.documentElement) {
            const cs = window.getComputedStyle(curr);
            if (cs.zoom && cs.zoom !== '1' && cs.zoom !== 'normal') {
                const z = parseFloat(cs.zoom);
                if (!isNaN(z) && z > 0) scale *= z;
            }
            if (cs.transform && cs.transform !== 'none') {
                const match = cs.transform.match(/matrix\(([^,]+),\s*[^,]+,\s*[^,]+,\s*([^,]+)/);
                if (match) {
                    const sx = parseFloat(match[1]);
                    if (!isNaN(sx) && sx > 0) scale *= sx;
                }
            }
            curr = curr.parentElement;
        }

        return scale || 1.0;
    }

    /**
     * Initialize dragging on a specific target element.
     */
    function initDraggableElement(el) {
        if (!el || el.dataset.sigDraggableInitialized === 'true') return;

        // If target is a table cell (TD), make sure position:relative works safely
        // by applying drag to its inner wrapper if available or creating one
        if (el.tagName === 'TD') {
            if (el.children.length === 1 && el.children[0].tagName === 'DIV') {
                initDraggableElement(el.children[0]);
                el.dataset.sigDraggableInitialized = 'true';
                return;
            } else if (el.children.length > 1) {
                // Wrap inner children in a draggable div
                const wrapper = document.createElement('div');
                wrapper.className = isHeaderElement(el) ? 'header-draggable sig-draggable' : 'sig-draggable';
                while (el.firstChild) {
                    wrapper.appendChild(el.firstChild);
                }
                el.appendChild(wrapper);
                initDraggableElement(wrapper);
                el.dataset.sigDraggableInitialized = 'true';
                return;
            }
        }

        el.dataset.sigDraggableInitialized = 'true';

        // Add class and tooltip
        el.classList.add('sig-draggable');
        if (isHeaderElement(el)) {
            el.classList.add('header-draggable');
        }

        if (!el.getAttribute('title')) {
            if (isHeaderElement(el)) {
                el.setAttribute('title', 'ចុចចាប់រំកិលក្បាលលិខិតដោយសេរី (ចុច ២ដង ដើម្បីកំណត់ឡើងវិញ)');
            } else {
                el.setAttribute('title', 'ចុចចាប់រំកិលហត្ថលេខាដោយសេរី (ចុច ២ដង ដើម្បីកំណត់ឡើងវិញ)');
            }
        }

        // Initialize stored position
        if (!el.dataset.sigX) el.dataset.sigX = '0';
        if (!el.dataset.sigY) el.dataset.sigY = '0';

        // Mouse down
        el.addEventListener('mousedown', function (e) {
            // Ignore clicks on buttons, links, inputs, selects
            if (['BUTTON', 'A', 'INPUT', 'SELECT', 'TEXTAREA'].includes(e.target.tagName)) return;
            if (e.button !== 0) return; // Only primary mouse button

            startDrag(el, e.clientX, e.clientY);
            e.preventDefault();
        });

        // Touch start for mobile/tablet devices
        el.addEventListener('touchstart', function (e) {
            if (['BUTTON', 'A', 'INPUT', 'SELECT', 'TEXTAREA'].includes(e.target.tagName)) return;
            if (e.touches.length === 1) {
                const t = e.touches[0];
                startDrag(el, t.clientX, t.clientY);
            }
        }, { passive: true });

        // Double click to reset this specific element
        el.addEventListener('dblclick', function (e) {
            e.preventDefault();
            e.stopPropagation();
            resetSingleDraggable(el);
        });
    }

    function startDrag(el, clientX, clientY) {
        const scale = getZoomScale(el);
        const currentX = parseFloat(el.dataset.sigX || '0') || 0;
        const currentY = parseFloat(el.dataset.sigY || '0') || 0;

        activeDrag = {
            el: el,
            startX: clientX,
            startY: clientY,
            initialX: currentX,
            initialY: currentY,
            scale: scale,
            moved: false
        };

        el.classList.add('sig-dragging');
        if (el.classList.contains('header-draggable')) {
            el.classList.add('header-dragging');
        }
        document.body.style.userSelect = 'none';
    }

    function onPointerMove(clientX, clientY) {
        if (!activeDrag) return;

        const dx = (clientX - activeDrag.startX) / activeDrag.scale;
        const dy = (clientY - activeDrag.startY) / activeDrag.scale;

        const newX = activeDrag.initialX + dx;
        const newY = activeDrag.initialY + dy;

        activeDrag.el.style.position = 'relative';
        activeDrag.el.style.left = `${newX}px`;
        activeDrag.el.style.top = `${newY}px`;

        activeDrag.el.dataset.sigX = newX.toFixed(2);
        activeDrag.el.dataset.sigY = newY.toFixed(2);
        activeDrag.moved = true;
    }

    function stopDrag() {
        if (!activeDrag) return;

        activeDrag.el.classList.remove('sig-dragging');
        activeDrag.el.classList.remove('header-dragging');
        document.body.style.userSelect = '';
        activeDrag = null;
    }

    // Window-level mouse & touch listeners
    window.addEventListener('mousemove', function (e) {
        if (activeDrag) {
            onPointerMove(e.clientX, e.clientY);
        }
    });

    window.addEventListener('mouseup', function () {
        stopDrag();
    });

    window.addEventListener('touchmove', function (e) {
        if (activeDrag && e.touches.length === 1) {
            const t = e.touches[0];
            onPointerMove(t.clientX, t.clientY);
        }
    }, { passive: true });

    window.addEventListener('touchend', function () {
        stopDrag();
    });

    window.addEventListener('touchcancel', function () {
        stopDrag();
    });

    /**
     * Reset a single draggable block back to origin.
     */
    function resetSingleDraggable(el) {
        if (!el) return;
        el.classList.add('sig-resetting');
        el.style.left = '0px';
        el.style.top = '0px';
        el.dataset.sigX = '0';
        el.dataset.sigY = '0';

        setTimeout(() => {
            el.classList.remove('sig-resetting');
        }, 260);
    }

    /**
     * Reset all draggable elements (both signatures and headers) on current document.
     */
    window.resetAllDraggables = function () {
        const elements = document.querySelectorAll('.sig-draggable, .header-draggable');
        elements.forEach(el => resetSingleDraggable(el));
    };

    // Alias for backward compatibility
    window.resetAllSignatures = window.resetAllDraggables;

    /**
     * Reset only headers
     */
    window.resetAllHeaders = function () {
        const elements = document.querySelectorAll('.header-draggable');
        elements.forEach(el => resetSingleDraggable(el));
    };

    /**
     * Scan the DOM and bind all draggable signature and header elements.
     */
    function scanAndBindDraggables() {
        DEFAULT_DRAGGABLE_SELECTORS.forEach(selector => {
            try {
                const found = document.querySelectorAll(selector);
                found.forEach(el => {
                    // Filter out empty spacers
                    if (el.children.length === 0 && !el.textContent.trim()) return;
                    initDraggableElement(el);
                });
            } catch (err) {
                console.warn('[sig_draggable] Selector error for:', selector, err);
            }
        });

        // Automatically bind any reset buttons
        const resetBtns = document.querySelectorAll('.btn-reset-sig, [data-action="reset-signatures"], [data-action="reset-draggables"]');
        resetBtns.forEach(btn => {
            if (!btn.dataset.sigResetBound) {
                btn.dataset.sigResetBound = 'true';
                btn.addEventListener('click', function (e) {
                    e.preventDefault();
                    window.resetAllDraggables();
                });
            }
        });
    }

    // Auto run on load and DOM changes
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', scanAndBindDraggables);
    } else {
        scanAndBindDraggables();
    }

    // Expose scanner so templates can re-trigger if DOM changes dynamically
    window.initDraggableSignatures = scanAndBindDraggables;
    window.initDraggableElements = scanAndBindDraggables;
})();
