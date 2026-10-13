/**
 * DCM System - Universal Dynamic Table Row Height & Interactive Column Width (w) Customizer
 * 
 * Features:
 *  1. Interactive Excel-Style Column Drag Resizing with live guideline & mm/px tooltip.
 *  2. Auto-Fit Row Height to fill the page down to the footer automatically.
 *  3. Manual Row Height Adjustment (+ / - / Slider / Presets), scope to Full or Per-Page.
 *  4. Continuation Header (Page 2+) customizable toggle (Show / Hide) per-page and globally.
 *  5. Context-aware document keying in localStorage (e.g. e1, e2, m0, m1, d1, retirement, etc.).
 *  6. 100% Print/PDF parity across screen preview and browser print.
 *  7. Standard Margin Guideline toggle (M shortcut) and Draggable resets.
 */

(function () {
    'use strict';

    /**
     * Determine document context key for isolated localStorage memory
     */
    function getDocKey() {
        if (window.DMS_CUSTOMIZER_KEY) return String(window.DMS_CUSTOMIZER_KEY).toLowerCase();
        const path = (window.location.pathname || '').toLowerCase();
        if (path.includes('/e2')) return 'e2';
        if (path.includes('/e1')) return 'e1';
        if (path.includes('/m0')) return 'm0';
        if (path.includes('/m1')) return 'm1';
        if (path.includes('/retirement')) return 'retirement';
        if (path.includes('/d1')) return 'd1';
        if (path.includes('/promotion/master')) return 'prom_master';
        if (path.includes('/medals/master')) return 'medals_master';
        if (path.includes('/status-report')) return 'status_report';
        if (path.includes('/score-bulletin')) return 'score_bulletin';
        if (path.includes('/attendance')) return 'attendance';
        return path.replace(/[^a-z0-9_]/g, '_').replace(/^_+|_+$/g, '') || 'default';
    }

    const DOC_KEY = getDocKey();

    // Storage keys (Preserving legacy keys for e2 and other documents)
    const STORAGE_KEY_COL_WIDTHS         = DOC_KEY === 'e2' ? 'dms_e2_col_widths_v2' : `dms_${DOC_KEY}_col_widths_v1`;
    const STORAGE_KEY_GLOBAL_ROW_HEIGHT  = DOC_KEY === 'e2' ? 'dms_e2_row_height_global_v3' : `dms_${DOC_KEY}_row_height_global_v1`;
    const STORAGE_KEY_PAGE_ROW_HEIGHTS   = DOC_KEY === 'e2' ? 'dms_e2_row_height_pages_v3' : `dms_${DOC_KEY}_row_height_pages_v1`;
    const STORAGE_KEY_GLOBAL_CONT_HEADER = DOC_KEY === 'e2' ? 'dms_e2_cont_header_global_v1' : `dms_${DOC_KEY}_cont_header_global_v1`;
    const STORAGE_KEY_PAGE_CONT_HEADERS  = DOC_KEY === 'e2' ? 'dms_e2_cont_header_pages_v1' : `dms_${DOC_KEY}_cont_header_pages_v1`;

    let isResizingCol = false;
    let currentColIdx = -1;
    let startX = 0;
    let startWidthCurrent = 0;
    let startWidthNext = 0;
    let currentTable = null;
    let guideline = null;
    let tooltip = null;
    let originalColWidths = [];

    function getCustomizableTables() {
        const selector = 'table.customizable-table, table.e2-table, table.e1-table, table.m0-table, table.m1-table, table.retirement-table, table.d1-table, table.formal-table, table.table-print, table.roster-table, table.seniority-tbl, .a4-page table';
        const found = document.querySelectorAll(selector);
        const valid = [];
        found.forEach(t => {
            if (t.querySelector('thead th') && !valid.includes(t)) {
                valid.push(t);
            }
        });
        return valid;
    }

    function getDynamicStyleEl() {
        let el = document.getElementById('dynamic-table-custom-styles');
        if (!el) {
            el = document.createElement('style');
            el.id = 'dynamic-table-custom-styles';
            document.head.appendChild(el);
        }
        return el;
    }

    /**
     * 1. COLUMN WIDTH RESIZER
     */
    function initColumnResizers() {
        const tables = getCustomizableTables();
        if (!tables.length) return;

        const firstHeaderRow = tables[0].querySelector('thead tr');
        if (firstHeaderRow && originalColWidths.length === 0) {
            const ths = firstHeaderRow.querySelectorAll('th');
            ths.forEach(th => {
                originalColWidths.push(th.style.width || th.getAttribute('style') || '');
            });
        }

        if (!guideline) {
            guideline = document.createElement('div');
            guideline.className = 'col-resize-guideline';
            document.body.appendChild(guideline);
        }
        if (!tooltip) {
            tooltip = document.createElement('div');
            tooltip.className = 'col-resize-tooltip';
            document.body.appendChild(tooltip);
        }

        tables.forEach(table => {
            const ths = table.querySelectorAll('thead th');
            ths.forEach((th, idx) => {
                if (idx === ths.length - 1) return;

                const existing = th.querySelector('.col-resizer');
                if (existing) existing.remove();

                const resizer = document.createElement('span');
                resizer.className = 'col-resizer';
                resizer.dataset.colIdx = idx;
                resizer.title = 'ទាញដើម្បីកែសម្រួលទទឹង (w) ឬចុច ២ដងដើម្បីកំណត់ដើម';

                resizer.addEventListener('mousedown', onResizerMouseDown);
                resizer.addEventListener('dblclick', onResizerDoubleClick);
                th.appendChild(resizer);
            });
        });

        applySavedColumnWidths();
    }

    function onResizerMouseDown(e) {
        e.preventDefault();
        e.stopPropagation();

        const resizer = e.target;
        currentColIdx = parseInt(resizer.dataset.colIdx, 10);
        const thCurrent = resizer.parentElement;
        const thNext = thCurrent.nextElementSibling;
        if (!thNext) return;

        currentTable = thCurrent.closest('table');
        isResizingCol = true;
        startX = e.clientX;

        startWidthCurrent = thCurrent.getBoundingClientRect().width;
        startWidthNext = thNext.getBoundingClientRect().width;

        resizer.classList.add('is-resizing');
        document.body.style.cursor = 'col-resize';
        document.body.style.userSelect = 'none';

        guideline.style.left = e.clientX + 'px';
        guideline.style.display = 'block';

        updateTooltip(e.clientX, e.clientY, startWidthCurrent);

        document.addEventListener('mousemove', onResizerMouseMove);
        document.addEventListener('mouseup', onResizerMouseUp);
    }

    function onResizerMouseMove(e) {
        if (!isResizingCol || !currentTable) return;

        const deltaX = e.clientX - startX;
        const minPx = 18;

        let newCurrentPx = startWidthCurrent + deltaX;
        let newNextPx = startWidthNext - deltaX;

        if (newCurrentPx < minPx) {
            newCurrentPx = minPx;
            newNextPx = (startWidthCurrent + startWidthNext) - minPx;
        } else if (newNextPx < minPx) {
            newNextPx = minPx;
            newCurrentPx = (startWidthCurrent + startWidthNext) - minPx;
        }

        const tableWidth = currentTable.getBoundingClientRect().width;
        const currentPct = ((newCurrentPx / tableWidth) * 100).toFixed(2) + '%';
        const nextPct = ((newNextPx / tableWidth) * 100).toFixed(2) + '%';

        syncColumnWidths(currentColIdx, currentPct, currentColIdx + 1, nextPct);

        guideline.style.left = e.clientX + 'px';
        updateTooltip(e.clientX, e.clientY, newCurrentPx, currentPct);
    }

    function onResizerMouseUp(e) {
        if (!isResizingCol) return;
        isResizingCol = false;

        document.querySelectorAll('.col-resizer.is-resizing').forEach(el => el.classList.remove('is-resizing'));
        document.body.style.cursor = '';
        document.body.style.userSelect = '';

        if (guideline) guideline.style.display = 'none';
        if (tooltip) tooltip.style.display = 'none';

        document.removeEventListener('mousemove', onResizerMouseMove);
        document.removeEventListener('mouseup', onResizerMouseUp);

        saveCurrentColumnWidths();
    }

    function onResizerDoubleClick(e) {
        e.preventDefault();
        e.stopPropagation();
        const colIdx = parseInt(e.target.dataset.colIdx, 10);
        if (originalColWidths[colIdx] && originalColWidths[colIdx + 1]) {
            syncColumnWidths(colIdx, originalColWidths[colIdx], colIdx + 1, originalColWidths[colIdx + 1]);
            saveCurrentColumnWidths();
            showToast(`បានកំណត់ទទឹងក្រឡាទី ${colIdx + 1} ទៅដើមវិញ!`);
        }
    }

    function updateTooltip(x, y, pxVal, pctVal) {
        if (!tooltip) return;
        const mmVal = Math.round((pxVal / (96 / 25.4)) * 10) / 10;
        const pctText = pctVal || '';
        tooltip.innerHTML = `<strong>ទទឹង (w):</strong> ${Math.round(pxVal)}px (${mmVal}mm) ${pctText}`;
        tooltip.style.left = (x + 12) + 'px';
        tooltip.style.top = (y - 30) + 'px';
        tooltip.style.display = 'block';
    }

    function syncColumnWidths(idx1, w1, idx2, w2) {
        const tables = getCustomizableTables();
        tables.forEach(tbl => {
            const ths = tbl.querySelectorAll('thead th');
            if (ths[idx1]) ths[idx1].style.width = w1;
            if (ths[idx2]) ths[idx2].style.width = w2;
        });
    }

    function saveCurrentColumnWidths() {
        const tables = getCustomizableTables();
        if (!tables.length) return;
        const widths = [];
        tables[0].querySelectorAll('thead th').forEach(th => {
            widths.push(th.style.width || '');
        });
        try {
            localStorage.setItem(STORAGE_KEY_COL_WIDTHS, JSON.stringify(widths));
        } catch (err) {}
    }

    function applySavedColumnWidths() {
        try {
            const raw = localStorage.getItem(STORAGE_KEY_COL_WIDTHS);
            if (!raw) return;
            const widths = JSON.parse(raw);
            if (!Array.isArray(widths) || !widths.length) return;

            const tables = getCustomizableTables();
            tables.forEach(tbl => {
                const ths = tbl.querySelectorAll('thead th');
                ths.forEach((th, idx) => {
                    if (widths[idx]) {
                        th.style.width = widths[idx];
                    }
                });
            });
        } catch (err) {}
    }

    window.resetAllColumnWidths = function () {
        try {
            localStorage.removeItem(STORAGE_KEY_COL_WIDTHS);
        } catch (err) {}

        const tables = getCustomizableTables();
        tables.forEach(tbl => {
            const ths = tbl.querySelectorAll('thead th');
            ths.forEach((th, idx) => {
                if (originalColWidths[idx]) {
                    th.style.width = originalColWidths[idx];
                } else {
                    th.style.width = '';
                }
            });
        });
        showToast('បានកំណត់ទទឹងក្រឡាទាំងអស់ទៅដើមវិញរួចរាល់!');
        window.closeAllToolbarDropdowns();
    };

    /**
     * 2. ROW HEIGHT CONTROLLERS (Full Document & Individual Pages)
     */
    let activeRowTarget = 'all';
    let globalRowHeight = 22.5;
    let pageRowHeights = {};

    function getEffectivePageHeight(pageNum) {
        const pKey = String(pageNum);
        if (pageRowHeights[pKey] !== undefined && pageRowHeights[pKey] !== null) {
            return parseFloat(pageRowHeights[pKey]);
        }
        return globalRowHeight;
    }

    function renderDynamicStyles() {
        const styleEl = getDynamicStyleEl();

        const targetTableTrs = `
            table.customizable-table tbody tr,
            table.e2-table tbody tr,
            table.e1-table tbody tr,
            table.m0-table tbody tr,
            table.m1-table tbody tr,
            table.retirement-table tbody tr,
            table.d1-table tbody tr,
            table.formal-table tbody tr,
            table.table-print tbody tr,
            table.roster-table tbody tr,
            table.seniority-tbl tbody tr,
            .a4-page table tbody tr
        `;

        const targetTableTds = `
            table.customizable-table tbody td,
            table.e2-table tbody td,
            table.e1-table tbody td,
            table.m0-table tbody td,
            table.m1-table tbody td,
            table.retirement-table tbody td,
            table.d1-table tbody td,
            table.formal-table tbody td,
            table.table-print tbody td,
            table.roster-table tbody td,
            table.seniority-tbl tbody td,
            .a4-page table tbody td
        `;

        const calcPad = (h) => {
            if (h <= 18) return 0;
            if (h <= 20) return 1;
            if (h <= 23) return 1.5;
            return Math.max(2, Math.round((h - 18) / 2));
        };
        const calcLh = (h) => {
            if (h <= 18) return '1.02';
            if (h <= 20) return '1.06';
            if (h <= 22) return '1.10';
            return '1.16';
        };
        const calcFs = (h) => {
            if (h <= 18) return '6.5pt';
            if (h <= 20) return '6.8pt';
            if (h >= 26) return '7.5pt';
            return '7.0pt';
        };

        const globalPad = calcPad(globalRowHeight);
        const globalLh = calcLh(globalRowHeight);
        const globalFs = calcFs(globalRowHeight);

        let css = `
            @page {
                size: A4 landscape !important;
                margin: 0 !important;
            }
            /* Global Row Height */
            ${targetTableTrs} {
                height: ${globalRowHeight}px !important;
            }
            ${targetTableTds} {
                height: ${globalRowHeight}px !important;
                min-height: ${globalRowHeight}px !important;
                padding-top: ${globalPad}px !important;
                padding-bottom: ${globalPad}px !important;
                line-height: ${globalLh} !important;
                font-size: ${globalFs} !important;
            }
            ${targetTableTds}.cell-show-full,
            ${targetTableTds}.cell-nowrap {
                line-height: ${globalLh} !important;
                font-size: ${globalFs} !important;
            }
            @media print {
                ${targetTableTrs} {
                    height: ${globalRowHeight}px !important;
                }
                ${targetTableTds} {
                    height: ${globalRowHeight}px !important;
                    min-height: ${globalRowHeight}px !important;
                    padding-top: ${globalPad}px !important;
                    padding-bottom: ${globalPad}px !important;
                    line-height: ${globalLh} !important;
                    font-size: ${globalFs} !important;
                }
                ${targetTableTds}.cell-show-full,
                ${targetTableTds}.cell-nowrap {
                    line-height: ${globalLh} !important;
                    font-size: ${globalFs} !important;
                }
            }
        `;

        for (const [pNum, hVal] of Object.entries(pageRowHeights)) {
            const hNum = parseFloat(hVal);
            if (!isNaN(hNum) && hNum >= 16) {
                const pad = calcPad(hNum);
                const lh = calcLh(hNum);
                const fs = calcFs(hNum);
                css += `
                    /* Page ${pNum} Custom Override */
                    .a4-page[data-page-num="${pNum}"] table tbody tr {
                        height: ${hNum}px !important;
                    }
                    .a4-page[data-page-num="${pNum}"] table tbody td {
                        height: ${hNum}px !important;
                        min-height: ${hNum}px !important;
                        padding-top: ${pad}px !important;
                        padding-bottom: ${pad}px !important;
                        line-height: ${lh} !important;
                        font-size: ${fs} !important;
                    }
                    .a4-page[data-page-num="${pNum}"] table tbody td.cell-show-full,
                    .a4-page[data-page-num="${pNum}"] table tbody td.cell-nowrap {
                        line-height: ${lh} !important;
                        font-size: ${fs} !important;
                    }
                    @media print {
                        .a4-page[data-page-num="${pNum}"] table tbody tr {
                            height: ${hNum}px !important;
                        }
                        .a4-page[data-page-num="${pNum}"] table tbody td {
                            height: ${hNum}px !important;
                            min-height: ${hNum}px !important;
                            padding-top: ${pad}px !important;
                            padding-bottom: ${pad}px !important;
                            line-height: ${lh} !important;
                            font-size: ${fs} !important;
                        }
                        .a4-page[data-page-num="${pNum}"] table tbody td.cell-show-full,
                        .a4-page[data-page-num="${pNum}"] table tbody td.cell-nowrap {
                            line-height: ${lh} !important;
                            font-size: ${fs} !important;
                        }
                    }
                `;
            }
        }

        styleEl.innerHTML = css;
        updateUI();
    }

    function saveRowHeightState() {
        try {
            localStorage.setItem(STORAGE_KEY_GLOBAL_ROW_HEIGHT, globalRowHeight);
            localStorage.setItem(STORAGE_KEY_PAGE_ROW_HEIGHTS, JSON.stringify(pageRowHeights));
        } catch (err) {}
    }

    function updateUI() {
        document.querySelectorAll('.btn-target-opt').forEach(btn => {
            const tgt = btn.dataset.target;
            const match = (tgt === String(activeRowTarget));
            btn.classList.toggle('active', match);
        });

        let currentH = globalRowHeight;
        if (activeRowTarget !== 'all') {
            currentH = getEffectivePageHeight(activeRowTarget);
        }

        const badge = document.getElementById('rowHeightValBadge');
        if (badge) {
            badge.textContent = `${currentH}px`;
        }

        const slider = document.getElementById('rowHeightSlider');
        if (slider) {
            slider.value = currentH;
        }

        const targetLabel = document.getElementById('sliderTargetLabel');
        if (targetLabel) {
            targetLabel.textContent = activeRowTarget === 'all' ? 'កម្ពស់ (គ្រប់ទំព័រ):' : `កម្ពស់ (ទំព័រទី ${activeRowTarget}):`;
        }

        const autoFitLabel = document.getElementById('autoFitBtnLabel');
        if (autoFitLabel) {
            autoFitLabel.textContent = activeRowTarget === 'all' ? 'ស្វ័យប្រវត្តគ្រប់ទំព័រ (Auto-Fit Full)' : `ស្វ័យប្រវត្តទំព័រទី ${activeRowTarget} (Auto-Fit Page ${activeRowTarget})`;
        }

        document.querySelectorAll('.btn-preset').forEach(btn => {
            const match = btn.textContent.includes(`${currentH}px`) || (currentH >= 22 && currentH <= 23 && btn.textContent.includes('ស្តង់ដា'));
            btn.classList.toggle('active', match);
        });

        document.querySelectorAll('.a4-page').forEach(pageEl => {
            const pNum = pageEl.dataset.pageNum;
            if (!pNum) return;
            const pBadge = document.getElementById(`pageBadge_${pNum}`);
            if (pBadge) {
                const effH = getEffectivePageHeight(pNum);
                pBadge.textContent = `${effH}px`;
            }
        });
    }

    window.setRowHeightTarget = function (target) {
        activeRowTarget = target === 'all' ? 'all' : parseInt(target, 10);
        updateUI();
    };

    window.setCustomRowHeight = function (valPx, target = null, save = true) {
        const val = parseFloat(valPx);
        if (isNaN(val) || val < 16 || val > 45) return;

        const effectiveTarget = target !== null ? target : activeRowTarget;

        if (effectiveTarget === 'all') {
            globalRowHeight = val;
            // Clear per-page overrides so that global applies cleanly to all pages
            pageRowHeights = {};
            try {
                localStorage.setItem(STORAGE_KEY_PAGE_ROW_HEIGHTS, '{}');
            } catch (err) {}
        } else {
            pageRowHeights[String(effectiveTarget)] = val;
        }

        renderDynamicStyles();
        if (save) saveRowHeightState();
    };

    window.adjustRowHeightStep = function (step) {
        let currentH = (activeRowTarget === 'all') ? globalRowHeight : getEffectivePageHeight(activeRowTarget);
        const next = Math.max(16, Math.min(38, Math.round((currentH + step) * 2) / 2));
        window.setCustomRowHeight(next);
    };

    window.adjustPageRowHeightStep = function (pageNum, step) {
        const currentH = getEffectivePageHeight(pageNum);
        const next = Math.max(16, Math.min(38, Math.round((currentH + step) * 2) / 2));
        window.setCustomRowHeight(next, pageNum);
    };

    window.autoFitSinglePage = function (pageNum, showToastMsg = true) {
        const pNum = parseInt(pageNum, 10);
        const pageEl = document.querySelector(`.a4-page[data-page-num="${pNum}"]`);
        if (!pageEl) return;

        const wrapper = pageEl.querySelector('.page-content-wrapper') || pageEl;
        const footer = pageEl.querySelector('.page-footer-number');
        const tbody = pageEl.querySelector('table tbody');
        if (!wrapper || !tbody) return;

        const rows = tbody.querySelectorAll('tr');
        if (!rows.length) return;

        const pageRect = pageEl.getBoundingClientRect();
        const footerHeight = footer ? footer.offsetHeight + 38 : 52;
        const targetBottom = pageRect.bottom - footerHeight;

        // Find actual bottom of content inside wrapper (not stretched flex wrapper height)
        const lastChild = wrapper.lastElementChild;
        const contentBottom = lastChild ? lastChild.getBoundingClientRect().bottom : pageRect.bottom;

        const remainingGap = targetBottom - contentBottom;
        const currentBase = getEffectivePageHeight(pNum);

        if (remainingGap > 6) {
            const extraPerCell = Math.floor((remainingGap * 0.80) / rows.length);
            const newHeight = Math.min(36, Math.round((currentBase + extraPerCell) * 2) / 2);
            window.setCustomRowHeight(newHeight, pNum);
            if (showToastMsg) {
                showToast(`បានកំណត់កម្ពស់ជួរស្វ័យប្រវត្តទំព័រទី ${pNum} (${newHeight}px) ជោគជ័យ!`);
            }
        } else if (remainingGap < -4) {
            const reducePerCell = Math.ceil((Math.abs(remainingGap) + 4) / rows.length);
            const newHeight = Math.max(16, Math.round((currentBase - reducePerCell) * 2) / 2);
            window.setCustomRowHeight(newHeight, pNum);
            if (showToastMsg) {
                showToast(`បានបង្រួមកម្ពស់ជួរស្វ័យប្រវត្តទំព័រទី ${pNum} (${newHeight}px) ជោគជ័យ!`);
            }
        } else {
            if (showToastMsg) showToast(`ទំព័រទី ${pNum} បានពេញគម្លាតស្តង់ដារួចហើយ!`);
        }
    };

    window.autoFitAllPages = function () {
        const pages = document.querySelectorAll('.a4-page');
        if (!pages.length) return;
        pages.forEach(p => {
            const pNum = p.dataset.pageNum;
            if (pNum) {
                window.autoFitSinglePage(pNum, false);
            }
        });
        showToast('បានកែសម្រួលកម្ពស់ជួរស្វ័យប្រវត្តគ្រប់ទំព័រ (Full) ជោគជ័យ!');
        window.closeAllToolbarDropdowns();
    };

    window.autoFitCurrentTarget = function () {
        if (activeRowTarget === 'all') {
            window.autoFitAllPages();
        } else {
            window.autoFitSinglePage(activeRowTarget, true);
        }
    };

    window.autoFitRowHeight = function () {
        window.autoFitCurrentTarget();
    };

    window.resetRowHeight = function () {
        try {
            localStorage.removeItem(STORAGE_KEY_GLOBAL_ROW_HEIGHT);
            localStorage.removeItem(STORAGE_KEY_PAGE_ROW_HEIGHTS);
        } catch (err) {}

        globalRowHeight = 22.5;
        pageRowHeights = {};
        activeRowTarget = 'all';

        renderDynamicStyles();
        showToast('បានកំណត់កម្ពស់ជួរដេកគ្រប់ទំព័រទៅស្តង់ដាដើមវិញរួចរាល់!');
    };

    window.resetSinglePageRowHeight = function (pageNum) {
        const pKey = String(pageNum);
        if (pageRowHeights[pKey] !== undefined) {
            delete pageRowHeights[pKey];
            saveRowHeightState();
            renderDynamicStyles();
            showToast(`បានកំណត់ទំព័រទី ${pageNum} ទៅកម្ពស់ស្តង់ដាវិញរួចរាល់!`);
        }
    };


    /**
     * 3. CONTINUATION HEADER (PAGE 2+) CUSTOMIZER (SHOW / HIDE)
     */
    let globalContHeaderVisible = true;
    let pageContHeaderOverrides = {};

    function isContHeaderVisible(pageNum) {
        const pKey = String(pageNum);
        if (pageContHeaderOverrides[pKey] !== undefined && pageContHeaderOverrides[pKey] !== null) {
            return !!pageContHeaderOverrides[pKey];
        }
        return globalContHeaderVisible;
    }

    function applyContHeaderVisibility() {
        const contHeaders = document.querySelectorAll('.page-continuation-header');
        if (!contHeaders.length) return;

        let anyVisible = false;

        contHeaders.forEach(hdr => {
            const pageEl = hdr.closest('.a4-page');
            const pNum = pageEl ? pageEl.dataset.pageNum : null;
            if (!pNum) return;

            const visible = isContHeaderVisible(pNum);
            if (visible) {
                hdr.classList.remove('dms-hidden');
                pageEl.classList.remove('hide-cont-header');
                anyVisible = true;
            } else {
                hdr.classList.add('dms-hidden');
                pageEl.classList.add('hide-cont-header');
            }

            const pageBtn = document.getElementById(`btnPageContHeader_${pNum}`);
            if (pageBtn) {
                if (visible) {
                    pageBtn.classList.remove('is-hidden');
                    pageBtn.innerHTML = '<i class="fa-solid fa-heading"></i> <span>ក្បាលទំព័រ: បង្ហាញ</span>';
                    pageBtn.title = `ចុចដើម្បីលាក់ក្បាលទំព័របន្តសម្រាប់ទំព័រទី ${pNum}`;
                } else {
                    pageBtn.classList.add('is-hidden');
                    pageBtn.innerHTML = '<i class="fa-solid fa-eye-slash"></i> <span>ក្បាលទំព័រ: លាក់</span>';
                    pageBtn.title = `ចុចដើម្បីបង្ហាញក្បាលទំព័របន្តសម្រាប់ទំព័រទី ${pNum}`;
                }
            }
        });

        const tbBtn = document.getElementById('btnToggleContHeader');
        const tbLbl = document.getElementById('contHeaderBtnText');
        if (tbBtn) {
            if (!anyVisible) {
                tbBtn.classList.add('is-hidden');
                if (tbLbl) tbLbl.textContent = 'ក្បាលទំព័រ 2+: លាក់';
                tbBtn.title = 'ក្បាលទំព័របន្តកំពុងត្រូវលាក់ (ចុចដើម្បីបង្ហាញ)';
            } else {
                tbBtn.classList.remove('is-hidden');
                if (tbLbl) tbLbl.textContent = 'ក្បាលទំព័រ 2+: បង្ហាញ';
                tbBtn.title = 'ក្បាលទំព័របន្តកំពុងបង្ហាញ (ចុចដើម្បីលាក់)';
            }
        }
    }

    window.toggleAllContinuationHeaders = function () {
        let hasVisible = false;
        document.querySelectorAll('.page-continuation-header').forEach(hdr => {
            const pageEl = hdr.closest('.a4-page');
            const pNum = pageEl ? pageEl.dataset.pageNum : null;
            if (pNum && isContHeaderVisible(pNum)) {
                hasVisible = true;
            }
        });

        globalContHeaderVisible = !hasVisible;
        pageContHeaderOverrides = {};

        try {
            localStorage.setItem(STORAGE_KEY_GLOBAL_CONT_HEADER, globalContHeaderVisible ? 'show' : 'hide');
            localStorage.removeItem(STORAGE_KEY_PAGE_CONT_HEADERS);
        } catch (err) {}

        applyContHeaderVisibility();

        const stateStr = globalContHeaderVisible ? 'បង្ហាញ' : 'លាក់';
        showToast(`បាន${stateStr}ក្បាលទំព័របន្ត គ្រប់ទំព័រ (ទំព័រទី២ឡើងទៅ) រួចរាល់!`);
    };

    window.toggleSinglePageContHeader = function (pageNum) {
        const pNum = parseInt(pageNum, 10);
        const curVisible = isContHeaderVisible(pNum);
        const nextVisible = !curVisible;

        pageContHeaderOverrides[String(pNum)] = nextVisible;

        try {
            localStorage.setItem(STORAGE_KEY_PAGE_CONT_HEADERS, JSON.stringify(pageContHeaderOverrides));
        } catch (err) {}

        applyContHeaderVisibility();

        const stateStr = nextVisible ? 'បង្ហាញ' : 'លាក់';
        showToast(`បាន${stateStr}ក្បាលទំព័របន្ត ទំព័រទី ${pNum} រួចរាល់!`);
    };

    /**
     * 4. MARGIN GUIDELINES & DRAGGABLE RESETS
     */
    if (typeof window.toggleMargins !== 'function') {
        window.toggleMargins = function (forceState) {
            const isShown = typeof forceState === 'boolean' ? !forceState : document.body.classList.contains('show-margins');
            const nextState = !isShown;
            document.body.classList.toggle('show-margins', nextState);
            document.querySelectorAll('.a4-page, .page, .page-sheet').forEach(p => p.classList.toggle('show-margins', nextState));
            document.querySelectorAll('.btn-toggle-margins').forEach(b => b.classList.toggle('active', nextState));
            if (typeof showToast === 'function') {
                showToast(nextState ? 'បានបង្ហាញបន្ទាត់គម្លាតស្តង់ដា (M)' : 'បានលាក់បន្ទាត់គម្លាតស្តង់ដា (M)');
            }
        };
    }

    window.resetAllDraggables = function () {
        if (window.resetDraggablePositions) {
            window.resetDraggablePositions();
        } else {
            document.querySelectorAll('.header-draggable, .sig-draggable').forEach(el => {
                el.style.transform = '';
                el.style.position = '';
                el.style.top = '';
                el.style.left = '';
            });
            showToast('បានកំណត់ទីតាំងដើមរួចរាល់!');
        }
    };

    /**
     * 5. DROPDOWN & CENTERED MODAL FORMS (លោតចំកណ្តាលអេក្រង់)
     */
    function getModalBackdrop() {
        let bd = document.getElementById('toolbarModalBackdrop');
        if (!bd) {
            bd = document.createElement('div');
            bd.id = 'toolbarModalBackdrop';
            bd.className = 'toolbar-modal-backdrop';
            bd.onclick = function () {
                window.closeAllToolbarDropdowns();
            };
            document.body.appendChild(bd);
        }
        return bd;
    }

    function ensureModalControls(modalEl) {
        if (!modalEl) return;
        if (modalEl.parentElement !== document.body) {
            document.body.appendChild(modalEl);
        }
        // Inject Close Button into .dropdown-header if missing
        const header = modalEl.querySelector('.dropdown-header');
        if (header && !header.querySelector('.btn-close-modal')) {
            const originalHtml = header.innerHTML;
            header.innerHTML = `
                <div class="dropdown-header-title">${originalHtml}</div>
                <button type="button" class="btn-close-modal" onclick="window.closeAllToolbarDropdowns()" title="បិទផ្ទាំង (Esc)">&times;</button>
            `;
        }
        // Inject Done button into footer if missing
        if (!modalEl.querySelector('.dropdown-footer-actions')) {
            const footer = document.createElement('div');
            footer.className = 'dropdown-footer-actions';
            footer.innerHTML = `
                <button type="button" class="btn-done-modal" onclick="window.closeAllToolbarDropdowns()">
                    <i class="fa-solid fa-check"></i> <span>រួចរាល់ (Done)</span>
                </button>
            `;
            modalEl.appendChild(footer);
        }
    }

    window.toggleRowHeightMenu = function (e) {
        if (e) e.stopPropagation();
        const dd = document.getElementById('rowHeightDropdown');
        const isShown = dd && dd.classList.contains('show');
        window.closeAllToolbarDropdowns();
        if (!isShown && dd) {
            ensureModalControls(dd);
            dd.classList.add('show');
            const bd = getModalBackdrop();
            bd.classList.add('show');
        }
    };

    window.toggleColWidthMenu = function (e) {
        if (e) e.stopPropagation();
        const dd = document.getElementById('colWidthDropdown');
        const isShown = dd && dd.classList.contains('show');
        window.closeAllToolbarDropdowns();
        if (!isShown && dd) {
            ensureModalControls(dd);
            dd.classList.add('show');
            const bd = getModalBackdrop();
            bd.classList.add('show');
        }
    };

    window.closeAllToolbarDropdowns = function () {
        document.querySelectorAll('.toolbar-dropdown-menu.show').forEach(el => el.classList.remove('show'));
        const bd = document.getElementById('toolbarModalBackdrop');
        if (bd) bd.classList.remove('show');
    };

    document.addEventListener('click', function (e) {
        const openMenu = document.querySelector('.toolbar-dropdown-menu.show');
        if (openMenu && !openMenu.contains(e.target) && !e.target.closest('#btnRowHeightMenu') && !e.target.closest('#btnColWidthMenu')) {
            window.closeAllToolbarDropdowns();
        }
    });

    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape') {
            window.closeAllToolbarDropdowns();
        }
    });

    /**
     * 6. TOAST NOTIFICATION
     */
    function showToast(msg) {
        let toast = document.getElementById('dms-action-toast');
        if (!toast) {
            toast = document.createElement('div');
            toast.id = 'dms-action-toast';
            toast.className = 'dms-toast-notice';
            document.body.appendChild(toast);
        }
        toast.textContent = msg;
        toast.classList.add('show');
        clearTimeout(toast._timer);
        toast._timer = setTimeout(() => {
            toast.classList.remove('show');
        }, 2800);
    }

    /**
     * 7. RESTORE SAVED STATE ON DOM READY
     */
    function onInit() {
        initColumnResizers();

        try {
            const savedGlobal = localStorage.getItem(STORAGE_KEY_GLOBAL_ROW_HEIGHT);
            if (savedGlobal) {
                globalRowHeight = parseFloat(savedGlobal) || 22.5;
            }
            const savedPages = localStorage.getItem(STORAGE_KEY_PAGE_ROW_HEIGHTS);
            if (savedPages) {
                pageRowHeights = JSON.parse(savedPages) || {};
            }
            const savedContGlobal = localStorage.getItem(STORAGE_KEY_GLOBAL_CONT_HEADER);
            if (savedContGlobal) {
                globalContHeaderVisible = (savedContGlobal !== 'hide');
            }
            const savedContPages = localStorage.getItem(STORAGE_KEY_PAGE_CONT_HEADERS);
            if (savedContPages) {
                pageContHeaderOverrides = JSON.parse(savedContPages) || {};
            }
        } catch (err) {}

        renderDynamicStyles();
        applyContHeaderVisibility();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', onInit);
    } else {
        onInit();
    }
})();
