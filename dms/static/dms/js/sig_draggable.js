/**
 * DCM System - Interactive Draggable Elements, Margin Resizer & Print Page Range Controller
 * Features:
 *  1. Free positioning of signature groups & official letterhead blocks.
 *  2. Interactive draggable margin guides with handles (■) to adjust/tune (សេរ៉េ) margins live.
 *  3. Page selection & page range controls to print specific pages (ពីទំព័រមួយ ទៅលេខរៀងណាមួយ).
 *  4. Precision anchoring for running page numbers.
 * Preserves 100% position fidelity when printed or exported as PDF.
 */

(function () {
    'use strict';

    const PX_PER_MM = 96 / 25.4; // 1mm = 3.779527559px at 96 DPI

    function pxToMm(px) {
        return Math.max(0, Math.round((px / PX_PER_MM) * 10) / 10);
    }

    function mmToPx(mm) {
        return mm * PX_PER_MM;
    }

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

    let activeSigDrag = null;
    let activeMarginDrag = null;
    let isMarginsVisible = false;

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

    /* ========================================================================= */
    /* 1. SIGNATURE & HEADER DRAG ENGINE                                         */
    /* ========================================================================= */

    function initDraggableElement(el) {
        if (!el || el.dataset.sigDraggableInitialized === 'true') return;

        if (el.tagName === 'TD') {
            if (el.children.length === 1 && el.children[0].tagName === 'DIV') {
                initDraggableElement(el.children[0]);
                el.dataset.sigDraggableInitialized = 'true';
                return;
            } else if (el.children.length > 1) {
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

        if (!el.dataset.sigX) el.dataset.sigX = '0';
        if (!el.dataset.sigY) el.dataset.sigY = '0';

        el.addEventListener('mousedown', function (e) {
            if (['BUTTON', 'A', 'INPUT', 'SELECT', 'TEXTAREA'].includes(e.target.tagName)) return;
            if (e.target.closest('.margin-handle') || e.target.closest('.margin-edge') || e.target.closest('.page-print-indicator')) return;
            if (e.button !== 0) return;

            startSigDrag(el, e.clientX, e.clientY);
            e.preventDefault();
        });

        el.addEventListener('touchstart', function (e) {
            if (['BUTTON', 'A', 'INPUT', 'SELECT', 'TEXTAREA'].includes(e.target.tagName)) return;
            if (e.target.closest('.margin-handle') || e.target.closest('.margin-edge') || e.target.closest('.page-print-indicator')) return;
            if (e.touches.length === 1) {
                const t = e.touches[0];
                startSigDrag(el, t.clientX, t.clientY);
            }
        }, { passive: true });

        el.addEventListener('dblclick', function (e) {
            e.preventDefault();
            e.stopPropagation();
            resetSingleDraggable(el);
        });
    }

    function createCoordTooltip(el) {
        let tip = el.querySelector('.sig-coord-tooltip');
        if (!tip) {
            tip = document.createElement('div');
            tip.className = 'sig-coord-tooltip';
            el.appendChild(tip);
        }
        return tip;
    }

    function startSigDrag(el, clientX, clientY) {
        const scale = getZoomScale(el);
        const currentX = parseFloat(el.dataset.sigX || '0') || 0;
        const currentY = parseFloat(el.dataset.sigY || '0') || 0;

        activeSigDrag = {
            el: el,
            startX: clientX,
            startY: clientY,
            initialX: currentX,
            initialY: currentY,
            scale: scale,
            moved: false,
            tooltip: createCoordTooltip(el)
        };

        el.classList.add('sig-dragging');
        if (el.classList.contains('header-draggable')) {
            el.classList.add('header-dragging');
        }
        document.body.classList.add('sig-active-drag');
        document.body.style.userSelect = 'none';

        updateSigTooltip(currentX, currentY);
    }

    function updateSigTooltip(x, y) {
        if (activeSigDrag && activeSigDrag.tooltip) {
            const xStr = (x >= 0 ? '+' : '') + Math.round(x);
            const yStr = (y >= 0 ? '+' : '') + Math.round(y);
            activeSigDrag.tooltip.textContent = `X: ${xStr}px | Y: ${yStr}px`;
        }
    }

    function onSigPointerMove(clientX, clientY) {
        if (!activeSigDrag) return;

        const dx = (clientX - activeSigDrag.startX) / activeSigDrag.scale;
        const dy = (clientY - activeSigDrag.startY) / activeSigDrag.scale;

        const newX = activeSigDrag.initialX + dx;
        const newY = activeSigDrag.initialY + dy;

        activeSigDrag.el.style.position = 'relative';
        activeSigDrag.el.style.left = `${newX}px`;
        activeSigDrag.el.style.top = `${newY}px`;

        activeSigDrag.el.dataset.sigX = newX.toFixed(2);
        activeSigDrag.el.dataset.sigY = newY.toFixed(2);
        activeSigDrag.moved = true;

        updateSigTooltip(newX, newY);
    }

    function stopSigDrag() {
        if (!activeSigDrag) return;

        activeSigDrag.el.classList.remove('sig-dragging');
        activeSigDrag.el.classList.remove('header-dragging');
        if (activeSigDrag.tooltip) {
            activeSigDrag.tooltip.remove();
        }
        document.body.classList.remove('sig-active-drag');
        document.body.style.userSelect = '';
        activeSigDrag = null;
    }

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

    /* ========================================================================= */
    /* 2. INTERACTIVE PAGE MARGIN RESIZER ENGINE (Show & Tune Margins)           */
    /* ========================================================================= */

    function getStorageKey() {
        return 'dms_margins_' + window.location.pathname;
    }

    function getPageContainers() {
        let pages = document.querySelectorAll('.a4-page, .page, .page-sheet, .doc-border-frame, .print-container');
        if (pages.length === 0) {
            const fallback = document.querySelector('.container, #print-area, body > div:not(.no-print):not(.preview-toolbar)');
            if (fallback) pages = [fallback];
        }
        return Array.from(pages);
    }

    function getTargetContainerForMargins(pageEl) {
        const frame = pageEl.querySelector('.doc-border-frame');
        return frame || pageEl;
    }

    function getContainerPaddings(targetEl) {
        const cs = window.getComputedStyle(targetEl);
        return {
            top: parseFloat(cs.paddingTop) || mmToPx(10),
            bottom: parseFloat(cs.paddingBottom) || mmToPx(10),
            left: parseFloat(cs.paddingLeft) || mmToPx(12),
            right: parseFloat(cs.paddingRight) || mmToPx(12)
        };
    }

    function savePageMargins(paddings) {
        try {
            localStorage.setItem(getStorageKey(), JSON.stringify(paddings));
        } catch (e) {}
    }

    function loadSavedMargins() {
        try {
            const val = localStorage.getItem(getStorageKey());
            return val ? JSON.parse(val) : null;
        } catch (e) {
            return null;
        }
    }

    function createLiveMarginTooltip() {
        let tip = document.getElementById('dms-live-margin-tooltip');
        if (!tip) {
            tip = document.createElement('div');
            tip.id = 'dms-live-margin-tooltip';
            tip.className = 'margin-live-tooltip';
            document.body.appendChild(tip);
        }
        return tip;
    }

    function updateLiveMarginTooltip(topPx, bottomPx, leftPx, rightPx) {
        const tip = createLiveMarginTooltip();
        const topMm = pxToMm(topPx);
        const btmMm = pxToMm(bottomPx);
        const lftMm = pxToMm(leftPx);
        const rgtMm = pxToMm(rightPx);
        tip.innerHTML = `
            <span>📐 <strong>សេរ៉េគម្លាតទំព័រ៖</strong></span>
            <span>លើ: <strong>${topMm}mm</strong></span>
            <span>|</span>
            <span>ក្រោម: <strong>${btmMm}mm</strong></span>
            <span>|</span>
            <span>ឆ្វេង: <strong>${lftMm}mm</strong></span>
            <span>|</span>
            <span>ស្តាំ: <strong>${rgtMm}mm</strong></span>
        `;
    }

    function removeLiveMarginTooltip() {
        const tip = document.getElementById('dms-live-margin-tooltip');
        if (tip) tip.remove();
    }

    function syncMarginFramePosition(pageEl, paddings) {
        const guide = pageEl.querySelector('.page-margin-guide');
        if (!guide) return;
        const frame = guide.querySelector('.page-margin-frame');
        if (!frame) return;

        frame.style.top = `${paddings.top}px`;
        frame.style.bottom = `${paddings.bottom}px`;
        frame.style.left = `${paddings.left}px`;
        frame.style.right = `${paddings.right}px`;

        const badgeText = frame.querySelector('.margin-badge-text');
        if (badgeText) {
            badgeText.textContent = `លើ: ${pxToMm(paddings.top)}mm | ក្រោម: ${pxToMm(paddings.bottom)}mm | ឆ្វេង: ${pxToMm(paddings.left)}mm | ស្តាំ: ${pxToMm(paddings.right)}mm`;
        }
    }

    function applyPaddingsToAllPages(paddings) {
        const pages = getPageContainers();
        pages.forEach(page => {
            const target = getTargetContainerForMargins(page);
            target.style.paddingTop = `${paddings.top}px`;
            target.style.paddingBottom = `${paddings.bottom}px`;
            target.style.paddingLeft = `${paddings.left}px`;
            target.style.paddingRight = `${paddings.right}px`;

            syncMarginFramePosition(page, paddings);
        });
    }

    function startMarginDrag(e, handleType, pageEl) {
        e.preventDefault();
        e.stopPropagation();

        const targetEl = getTargetContainerForMargins(pageEl);
        const currentPaddings = getContainerPaddings(targetEl);
        const scale = getZoomScale(pageEl);

        const clientX = e.clientX || (e.touches && e.touches[0] ? e.touches[0].clientX : 0);
        const clientY = e.clientY || (e.touches && e.touches[0] ? e.touches[0].clientY : 0);

        activeMarginDrag = {
            pageEl: pageEl,
            targetEl: targetEl,
            handleType: handleType,
            startX: clientX,
            startY: clientY,
            initialTop: currentPaddings.top,
            initialBottom: currentPaddings.bottom,
            initialLeft: currentPaddings.left,
            initialRight: currentPaddings.right,
            scale: scale
        };

        document.body.classList.add('margin-active-resizing');
        document.body.style.userSelect = 'none';

        if (e.target.classList.contains('margin-handle')) {
            e.target.classList.add('active');
            activeMarginDrag.activeHandleEl = e.target;
        }

        updateLiveMarginTooltip(currentPaddings.top, currentPaddings.bottom, currentPaddings.left, currentPaddings.right);
    }

    function onMarginPointerMove(clientX, clientY) {
        if (!activeMarginDrag) return;

        const dx = (clientX - activeMarginDrag.startX) / activeMarginDrag.scale;
        const dy = (clientY - activeMarginDrag.startY) / activeMarginDrag.scale;

        const MIN_PX = mmToPx(3);
        const MIN_BOTTOM_PX = mmToPx(8); // Safe clearance so tables never overlap page footer numbers
        const MAX_PX = mmToPx(55);

        let newTop = activeMarginDrag.initialTop;
        let newBottom = activeMarginDrag.initialBottom;
        let newLeft = activeMarginDrag.initialLeft;
        let newRight = activeMarginDrag.initialRight;

        const type = activeMarginDrag.handleType;

        if (type === 'top' || type === 'tl' || type === 'tr') {
            newTop = Math.max(MIN_PX, Math.min(MAX_PX, activeMarginDrag.initialTop + dy));
        }
        if (type === 'bottom' || type === 'bl' || type === 'br') {
            newBottom = Math.max(MIN_BOTTOM_PX, Math.min(MAX_PX, activeMarginDrag.initialBottom - dy));
        }

        if (type === 'left' || type === 'tl' || type === 'bl') {
            newLeft = Math.max(MIN_PX, Math.min(MAX_PX, activeMarginDrag.initialLeft + dx));
        }
        if (type === 'right' || type === 'tr' || type === 'br') {
            newRight = Math.max(MIN_PX, Math.min(MAX_PX, activeMarginDrag.initialRight - dx));
        }

        const newPaddings = {
            top: Math.round(newTop),
            bottom: Math.round(newBottom),
            left: Math.round(newLeft),
            right: Math.round(newRight)
        };

        applyPaddingsToAllPages(newPaddings);
        updateLiveMarginTooltip(newPaddings.top, newPaddings.bottom, newPaddings.left, newPaddings.right);
    }

    function stopMarginDrag() {
        if (!activeMarginDrag) return;

        const targetEl = activeMarginDrag.targetEl;
        const finalPaddings = getContainerPaddings(targetEl);
        savePageMargins(finalPaddings);

        if (activeMarginDrag.activeHandleEl) {
            activeMarginDrag.activeHandleEl.classList.remove('active');
        }

        document.body.classList.remove('margin-active-resizing');
        document.body.style.userSelect = '';
        removeLiveMarginTooltip();
        activeMarginDrag = null;
    }

    function injectMarginGuides() {
        const pages = getPageContainers();
        const savedMargins = loadSavedMargins();

        pages.forEach(page => {
            const targetEl = getTargetContainerForMargins(page);

            if (!targetEl.dataset.defaultPaddingTop) {
                const initPaddings = getContainerPaddings(targetEl);
                targetEl.dataset.defaultPaddingTop = initPaddings.top;
                targetEl.dataset.defaultPaddingBottom = initPaddings.bottom;
                targetEl.dataset.defaultPaddingLeft = initPaddings.left;
                targetEl.dataset.defaultPaddingRight = initPaddings.right;
            }

            if (savedMargins) {
                targetEl.style.paddingTop = `${savedMargins.top}px`;
                targetEl.style.paddingBottom = `${savedMargins.bottom}px`;
                targetEl.style.paddingLeft = `${savedMargins.left}px`;
                targetEl.style.paddingRight = `${savedMargins.right}px`;
            }

            let guide = page.querySelector('.page-margin-guide');
            if (!guide) {
                guide = document.createElement('div');
                guide.className = 'page-margin-guide';
                guide.innerHTML = `
                    <div class="page-margin-frame">
                        <!-- 4 Draggable Border Edges -->
                        <div class="margin-edge margin-edge-top" data-edge="top" title="ចុចទាញដើម្បីសេរ៉េគម្លាតខាងលើ (Top Margin)"></div>
                        <div class="margin-edge margin-edge-bottom" data-edge="bottom" title="ចុចទាញដើម្បីសេរ៉េគម្លាតខាងក្រោម (Bottom Margin)"></div>
                        <div class="margin-edge margin-edge-left" data-edge="left" title="ចុចទាញដើម្បីសេរ៉េគម្លាតខាងឆ្វេង (Left Margin)"></div>
                        <div class="margin-edge margin-edge-right" data-edge="right" title="ចុចទាញដើម្បីសេរ៉េគម្លាតខាងស្តាំ (Right Margin)"></div>

                        <!-- Top Interactive Handles (■) -->
                        <div class="margin-handle" data-handle="tl" style="top: 0; left: 0;" title="ទាញជ្រុងលើ-ឆ្វេង"></div>
                        <div class="margin-handle" data-handle="top" style="top: 0; left: 12.5%;" title="ទាញគម្លាតលើ"></div>
                        <div class="margin-handle" data-handle="top" style="top: 0; left: 25%;" title="ទាញគម្លាតលើ"></div>
                        <div class="margin-handle" data-handle="top" style="top: 0; left: 37.5%;" title="ទាញគម្លាតលើ"></div>
                        <div class="margin-handle" data-handle="top" style="top: 0; left: 50%;" title="ទាញគម្លាតលើ"></div>
                        <div class="margin-handle" data-handle="top" style="top: 0; left: 62.5%;" title="ទាញគម្លាតលើ"></div>
                        <div class="margin-handle" data-handle="top" style="top: 0; left: 75%;" title="ទាញគម្លាតលើ"></div>
                        <div class="margin-handle" data-handle="top" style="top: 0; left: 87.5%;" title="ទាញគម្លាតលើ"></div>
                        <div class="margin-handle" data-handle="tr" style="top: 0; left: 100%;" title="ទាញជ្រុងលើ-ស្តាំ"></div>

                        <!-- Right Interactive Handles (■) -->
                        <div class="margin-handle" data-handle="right" style="top: 25%; left: 100%;" title="ទាញគម្លាតស្តាំ"></div>
                        <div class="margin-handle" data-handle="right" style="top: 50%; left: 100%;" title="ទាញគម្លាតស្តាំ"></div>
                        <div class="margin-handle" data-handle="right" style="top: 75%; left: 100%;" title="ទាញគម្លាតស្តាំ"></div>

                        <!-- Bottom Interactive Handles (■) -->
                        <div class="margin-handle" data-handle="bl" style="top: 100%; left: 0;" title="ទាញជ្រុងក្រោម-ឆ្វេង"></div>
                        <div class="margin-handle" data-handle="bottom" style="top: 100%; left: 12.5%;" title="ទាញគម្លាតក្រោម"></div>
                        <div class="margin-handle" data-handle="bottom" style="top: 100%; left: 25%;" title="ទាញគម្លាតក្រោម"></div>
                        <div class="margin-handle" data-handle="bottom" style="top: 100%; left: 37.5%;" title="ទាញគម្លាតក្រោម"></div>
                        <div class="margin-handle" data-handle="bottom" style="top: 100%; left: 50%;" title="ទាញគម្លាតក្រោម"></div>
                        <div class="margin-handle" data-handle="bottom" style="top: 100%; left: 62.5%;" title="ទាញគម្លាតក្រោម"></div>
                        <div class="margin-handle" data-handle="bottom" style="top: 100%; left: 75%;" title="ទាញគម្លាតក្រោម"></div>
                        <div class="margin-handle" data-handle="bottom" style="top: 100%; left: 87.5%;" title="ទាញគម្លាតក្រោម"></div>
                        <div class="margin-handle" data-handle="br" style="top: 100%; left: 100%;" title="ទាញជ្រុងក្រោម-ស្តាំ"></div>

                        <!-- Left Interactive Handles (■) -->
                        <div class="margin-handle" data-handle="left" style="top: 25%; left: 0;" title="ទាញគម្លាតឆ្វេង"></div>
                        <div class="margin-handle" data-handle="left" style="top: 50%; left: 0;" title="ទាញគម្លាតឆ្វេង"></div>
                        <div class="margin-handle" data-handle="left" style="top: 75%; left: 0;" title="ទាញគម្លាតឆ្វេង"></div>

                        <!-- Center Midline Guide -->
                        <div class="page-margin-centerline"></div>

                        <!-- Margin Dimension Badge -->
                        <div class="page-margin-badge">
                            <span>📐</span>
                            <span class="margin-badge-text"></span>
                        </div>
                    </div>
                `;
                page.appendChild(guide);

                const handlesAndEdges = guide.querySelectorAll('.margin-handle, .margin-edge');
                handlesAndEdges.forEach(el => {
                    const type = el.dataset.handle || el.dataset.edge;

                    el.addEventListener('mousedown', function (e) {
                        if (e.button !== 0) return;
                        startMarginDrag(e, type, page);
                    });

                    el.addEventListener('touchstart', function (e) {
                        if (e.touches.length === 1) {
                            startMarginDrag(e, type, page);
                        }
                    }, { passive: false });

                    el.addEventListener('dblclick', function (e) {
                        e.preventDefault();
                        e.stopPropagation();
                        window.resetAllMargins();
                    });
                });
            }

            const currentPaddings = getContainerPaddings(targetEl);
            syncMarginFramePosition(page, currentPaddings);
        });
    }

    window.resetAllMargins = function () {
        const pages = getPageContainers();
        pages.forEach(page => {
            const targetEl = getTargetContainerForMargins(page);
            if (targetEl.dataset.defaultPaddingTop) {
                const defPaddings = {
                    top: parseFloat(targetEl.dataset.defaultPaddingTop),
                    bottom: parseFloat(targetEl.dataset.defaultPaddingBottom),
                    left: parseFloat(targetEl.dataset.defaultPaddingLeft),
                    right: parseFloat(targetEl.dataset.defaultPaddingRight)
                };
                targetEl.style.paddingTop = '';
                targetEl.style.paddingBottom = '';
                targetEl.style.paddingLeft = '';
                targetEl.style.paddingRight = '';
                syncMarginFramePosition(page, defPaddings);
            }
        });

        try {
            localStorage.removeItem(getStorageKey());
        } catch (e) {}
    };

    window.resetAllDraggables = function () {
        const elements = document.querySelectorAll('.sig-draggable, .header-draggable');
        elements.forEach(el => resetSingleDraggable(el));
        window.resetAllMargins();
    };

    window.resetAllSignatures = window.resetAllDraggables;
    window.resetAllHeaders = function () {
        const elements = document.querySelectorAll('.header-draggable');
        elements.forEach(el => resetSingleDraggable(el));
    };

    window.toggleMargins = function (forceState) {
        if (typeof forceState === 'boolean') {
            isMarginsVisible = forceState;
        } else {
            isMarginsVisible = !isMarginsVisible;
        }

        injectMarginGuides();

        if (isMarginsVisible) {
            document.body.classList.add('show-margins');
            try { localStorage.setItem('dms_show_margins', 'true'); } catch (e) {}
        } else {
            document.body.classList.remove('show-margins');
            try { localStorage.setItem('dms_show_margins', 'false'); } catch (e) {}
        }

        const btns = document.querySelectorAll('.btn-toggle-margins, [data-action="toggle-margins"]');
        btns.forEach(btn => {
            if (isMarginsVisible) {
                btn.classList.add('active');
                const textSpan = btn.querySelector('span, .margin-btn-text');
                if (textSpan) textSpan.textContent = 'បន្ទាត់គម្លាត៖ បង្ហាញ';
            } else {
                btn.classList.remove('active');
                const textSpan = btn.querySelector('span, .margin-btn-text');
                if (textSpan) textSpan.textContent = 'បន្ទាត់គម្លាត៖ លាក់';
            }
        });
    };

    window.showMargins = function () { window.toggleMargins(true); };
    window.hideMargins = function () { window.toggleMargins(false); };

    /* ========================================================================= */
    /* 3. PRINT PAGE RANGE & SELECTIVE PRINTING CONTROLLER ENGINE                */
    /* ========================================================================= */

    let pageInclusionMap = []; // Array of boolean: true = included in print, false = excluded

    function getPrintablePages() {
        let pages = document.querySelectorAll('.a4-page, .page, .page-sheet, .doc-border-frame, section.roster-page-item');
        if (pages.length === 0) {
            const fallback = document.querySelector('.container, #print-area, body > div:not(.no-print):not(.preview-toolbar)');
            if (fallback) pages = [fallback];
        }
        return Array.from(pages);
    }

    function updatePagePrintExclusionUI() {
        const pages = getPrintablePages();
        let includedCount = 0;

        pages.forEach((page, idx) => {
            const isIncluded = pageInclusionMap[idx] !== false;
            if (isIncluded) {
                page.classList.remove('page-print-excluded');
                includedCount++;
            } else {
                page.classList.add('page-print-excluded');
            }

            const chk = page.querySelector('.page-print-indicator input[type="checkbox"]');
            if (chk) {
                chk.checked = isIncluded;
            }
        });

        // Update badge summary
        const badge = document.getElementById('range-summary-badge');
        if (badge) {
            badge.textContent = `(បោះពុម្ព ${includedCount}/${pages.length} ទំព័រ)`;
        }
    }

    window.togglePagePrintInclusion = function (pageIndex) {
        if (typeof pageIndex === 'number' && pageIndex >= 0 && pageIndex < pageInclusionMap.length) {
            pageInclusionMap[pageIndex] = !pageInclusionMap[pageIndex];
            updatePagePrintExclusionUI();

            // Set select to 'custom'
            const selectEl = document.getElementById('print-page-select');
            if (selectEl) {
                selectEl.value = 'custom';
                const container = document.getElementById('range-inputs-container');
                if (container) container.style.display = 'inline-flex';
            }
        }
    };

    window.handlePageSelectChange = function (val) {
        const pages = getPrintablePages();
        const total = pages.length;
        const container = document.getElementById('range-inputs-container');
        const fromInput = document.getElementById('range-from-page');
        const toInput = document.getElementById('range-to-page');

        if (val === 'all') {
            if (container) container.style.display = 'none';
            pageInclusionMap = new Array(total).fill(true);
            if (fromInput) fromInput.value = '1';
            if (toInput) toInput.value = total;
        } else if (val === 'custom') {
            if (container) container.style.display = 'inline-flex';
            window.applyPageRangeSelection();
            return;
        } else if (val.startsWith('page_')) {
            if (container) container.style.display = 'none';
            const targetIdx = parseInt(val.replace('page_', ''), 10) - 1;
            pageInclusionMap = new Array(total).fill(false);
            if (targetIdx >= 0 && targetIdx < total) {
                pageInclusionMap[targetIdx] = true;
                if (fromInput) fromInput.value = targetIdx + 1;
                if (toInput) toInput.value = targetIdx + 1;
            }
        }

        updatePagePrintExclusionUI();
    };

    window.applyPageRangeSelection = function () {
        const pages = getPrintablePages();
        const total = pages.length;
        const fromInput = document.getElementById('range-from-page');
        const toInput = document.getElementById('range-to-page');

        let fromPage = parseInt(fromInput?.value || '1', 10);
        let toPage = parseInt(toInput?.value || total, 10);

        if (isNaN(fromPage) || fromPage < 1) fromPage = 1;
        if (isNaN(toPage) || toPage > total) toPage = total;
        if (fromPage > toPage) fromPage = toPage;

        pageInclusionMap = new Array(total).fill(false);
        for (let i = fromPage - 1; i <= toPage - 1; i++) {
            if (i >= 0 && i < total) {
                pageInclusionMap[i] = true;
            }
        }

        updatePagePrintExclusionUI();
    };

    function initPagePrintRangeController() {
        const pages = getPrintablePages();
        const total = pages.length;

        pageInclusionMap = new Array(total).fill(true);

        // Inject Page indicators on each page
        pages.forEach((page, idx) => {
            page.style.position = 'relative';

            const footerNum = page.querySelector('.page-footer-number, .page-footer-center');
            if (footerNum) {
                footerNum.style.position = 'relative';
                footerNum.style.marginTop = '6px';
                footerNum.style.marginBottom = '2px';
                footerNum.style.textAlign = 'center';
            }

            if (total > 1 && !page.querySelector('.page-print-indicator')) {
                const indicator = document.createElement('div');
                indicator.className = 'page-print-indicator';
                indicator.title = `ចុចដើម្បីជ្រើសរើស ឬដកទំព័រទី ${idx + 1} ពីការបោះពុម្ព`;
                indicator.innerHTML = `
                    <label style="cursor: pointer; display: flex; align-items: center; gap: 5px; margin: 0;">
                        <input type="checkbox" checked onchange="window.togglePagePrintInclusion(${idx}); event.stopPropagation();">
                        <span>ទំព័រទី ${idx + 1}</span>
                    </label>
                `;
                page.appendChild(indicator);
            }
        });

        if (total <= 1) return;

        // Check if toolbar widget is already injected
        if (document.getElementById('print-page-range-widget')) return;

        let toolbarTarget = document.querySelector('.preview-toolbar-actions, .preview-toolbar, .no-print');
        if (!toolbarTarget) {
            toolbarTarget = document.createElement('div');
            toolbarTarget.className = 'no-print';
            toolbarTarget.style.cssText = 'position: fixed; top: 12px; left: 20px; z-index: 99999; display: flex; align-items: center; gap: 8px;';
            document.body.appendChild(toolbarTarget);
        }

        const widget = document.createElement('div');
        widget.id = 'print-page-range-widget';
        widget.className = 'print-page-range-widget';

        let optionsHtml = `
            <option value="all">គ្រប់ទំព័រ (១ ដល់ ${total})</option>
            <option value="custom">កំណត់ចន្លោះទំព័រ (Range)...</option>
        `;
        for (let i = 1; i <= total; i++) {
            optionsHtml += `<option value="page_${i}">តែទំព័រទី ${i}</option>`;
        }

        widget.innerHTML = `
            <div class="range-selector-group">
                <label for="print-page-select" class="range-label">
                    <i class="fa-solid fa-file-circle-check"></i> ទំព័របោះពុម្ព៖
                </label>
                <select id="print-page-select" class="range-select" onchange="window.handlePageSelectChange(this.value)">
                    ${optionsHtml}
                </select>
            </div>
            <div class="range-inputs-container" id="range-inputs-container" style="display: none;">
                <span class="range-text">ពីទំព័រ</span>
                <input type="number" id="range-from-page" class="range-input" min="1" max="${total}" value="1" oninput="window.applyPageRangeSelection()">
                <span class="range-text">ដល់</span>
                <input type="number" id="range-to-page" class="range-input" min="1" max="${total}" value="${total}" oninput="window.applyPageRangeSelection()">
            </div>
            <span class="range-badge" id="range-summary-badge">(សរុប ${total} ទំព័រ)</span>
        `;

        if (toolbarTarget.firstChild) {
            toolbarTarget.insertBefore(widget, toolbarTarget.firstChild);
        } else {
            toolbarTarget.appendChild(widget);
        }
    }

    /* ========================================================================= */
    /* 4. GLOBAL POINTER LISTENERS                                               */
    /* ========================================================================= */

    window.addEventListener('mousemove', function (e) {
        if (activeSigDrag) {
            onSigPointerMove(e.clientX, e.clientY);
        } else if (activeMarginDrag) {
            onMarginPointerMove(e.clientX, e.clientY);
        }
    });

    window.addEventListener('mouseup', function () {
        if (activeSigDrag) stopSigDrag();
        if (activeMarginDrag) stopMarginDrag();
    });

    window.addEventListener('touchmove', function (e) {
        if (activeSigDrag && e.touches.length === 1) {
            onSigPointerMove(e.touches[0].clientX, e.touches[0].clientY);
        } else if (activeMarginDrag && e.touches.length === 1) {
            e.preventDefault();
            onMarginPointerMove(e.touches[0].clientX, e.touches[0].clientY);
        }
    }, { passive: false });

    window.addEventListener('touchend', function () {
        if (activeSigDrag) stopSigDrag();
        if (activeMarginDrag) stopMarginDrag();
    });

    window.addEventListener('touchcancel', function () {
        if (activeSigDrag) stopSigDrag();
        if (activeMarginDrag) stopMarginDrag();
    });

    /* ========================================================================= */
    /* 5. SCAN AND INITIALIZE ALL ELEMENTS                                       */
    /* ========================================================================= */

    function scanAndBindDraggables() {
        DEFAULT_DRAGGABLE_SELECTORS.forEach(selector => {
            try {
                const found = document.querySelectorAll(selector);
                found.forEach(el => {
                    if (el.children.length === 0 && !el.textContent.trim()) return;
                    initDraggableElement(el);
                });
            } catch (err) {
                console.warn('[sig_draggable] Selector error for:', selector, err);
            }
        });

        // Bind reset buttons
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

        // Bind toggle margin buttons
        const marginBtns = document.querySelectorAll('.btn-toggle-margins, [data-action="toggle-margins"]');
        marginBtns.forEach(btn => {
            if (!btn.dataset.sigMarginBound) {
                btn.dataset.sigMarginBound = 'true';
                btn.addEventListener('click', function (e) {
                    e.preventDefault();
                    window.toggleMargins();
                });
            }
        });

        // Initialize margin guides on pages
        injectMarginGuides();

        // Initialize page range & selective print controller
        initPagePrintRangeController();

        // Check stored margin state
        try {
            const savedState = localStorage.getItem('dms_show_margins');
            if (savedState === 'true' || savedState === null) {
                window.toggleMargins(true);
            }
        } catch (e) {
            window.toggleMargins(true);
        }
    }

    // Keyboard shortcut (Press 'M' to toggle margins)
    document.addEventListener('keydown', function (e) {
        if (['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement?.tagName) || document.activeElement?.isContentEditable) {
            return;
        }
        if (e.key === 'm' || e.key === 'M') {
            if (!e.ctrlKey && !e.altKey && !e.metaKey) {
                e.preventDefault();
                window.toggleMargins();
            }
        }
    });

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', scanAndBindDraggables);
    } else {
        scanAndBindDraggables();
    }

    window.initDraggableSignatures = scanAndBindDraggables;
    window.initDraggableElements = scanAndBindDraggables;
    window.injectMarginGuides = injectMarginGuides;
    window.initPagePrintRangeController = initPagePrintRangeController;
})();
