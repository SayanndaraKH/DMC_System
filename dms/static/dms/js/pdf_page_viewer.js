/**
 * ==============================================================================
 * 📄 PDF Page Viewer & Extractor (ឧបករណ៍មើលទំព័រ PDF & បំបែក/រក្សាទុកជា File ថ្មី)
 * ------------------------------------------------------------------------------
 * Supports:
 * - Rendering all pages in a modern responsive thumbnail grid or continuous view
 * - Multi-page selection (individual checkbox, select all, range selection e.g. 1-3, 5)
 * - Single-click "Save this page as new PDF"
 * - Batch "Save selected pages as a new PDF file" (Client-side instant via pdf-lib)
 * - Save each selected page as individual separate PDF files
 * - Save extracted pages directly into an Officer's profile as a new reference attachment
 * ==============================================================================
 */

(function (window) {
    'use strict';

    class PdfPageViewer {
        constructor(config) {
            this.container = typeof config.container === 'string' ? document.getElementById(config.container) : config.container;
            this.toolbar = config.toolbar ? (typeof config.toolbar === 'string' ? document.getElementById(config.toolbar) : config.toolbar) : null;
            this.onSelectionChange = config.onSelectionChange || null;
            this.officerId = config.officerId || null;
            this.instanceName = config.instanceName || '__pdfViewerInstance';
            window[this.instanceName] = this;
            this.badgeId = config.badgeId || 'pdfSelectedCountBadge';
            this.saveBtnId = config.saveBtnId || 'pdfSaveSelectedBtn';
            this.eachBtnId = config.eachBtnId || 'pdfSaveEachBtn';
            this.idPrefix = config.idPrefix || 'pdfPage';
            this.pdfDoc = null;
            this.rawArrayBuffer = null;
            this.numPages = 0;
            this.selectedPages = new Set();
            this.currentTitle = config.title || 'document.pdf';
            this.renderScale = config.renderScale || 0.55;
            this.viewMode = 'grid'; // 'grid' | 'single' | 'list'
            this.currentPageIndex = 1;
            this.pageCanvases = {};
            this.isRendering = false;
            // Preview Modal states
            this.currentPreviewPage = 1;
            this.previewScale = 1.4;
            this.previewRotation = 0;
            this.previewBsModal = null;
        }

        /**
         * Initialize worker if not set, with multi-level fallback
         */
        async _ensureWorker() {
            if (typeof pdfjsLib === 'undefined') return;
            if (pdfjsLib.GlobalWorkerOptions.workerSrc) return;

            // Strategy 1: Attempt to load local worker via Blob URL (bypasses any origin/IP/port worker security restrictions)
            try {
                const localWorkerUrl = window.location.origin + '/static/dms/vendor/pdf.worker.min.js';
                const resp = await fetch(localWorkerUrl);
                if (resp.ok) {
                    const blob = await resp.blob();
                    pdfjsLib.GlobalWorkerOptions.workerSrc = URL.createObjectURL(blob);
                    return;
                }
            } catch (e) {
                console.warn("Could not prefetch worker as Blob:", e);
            }

            // Strategy 2: Relative local URL
            pdfjsLib.GlobalWorkerOptions.workerSrc = '/static/dms/vendor/pdf.worker.min.js';
        }

        /**
         * Load PDF from URL or ArrayBuffer or File
         */
        async load(source, title = 'document.pdf', officerId = null) {
            await this._ensureWorker();
            this.currentTitle = title;
            if (officerId) this.officerId = officerId;
            this.selectedPages.clear();

            if (!this.container) return;

            // Show loading state
            this.container.innerHTML = `
                <div class="text-center py-5 my-auto w-100">
                    <div class="spinner-border text-warning mb-3" style="width: 3rem; height: 3rem;" role="status"></div>
                    <div class="text-light fw-bold fs-6">កំពុងផ្ទុក និងដំណើរការទំព័រ PDF ទាំងអស់...</div>
                    <div class="text-white-50 fs-8 mt-1">រៀបចំតារាងទំព័រនីមួយៗ (Rendering Pages)</div>
                </div>
            `;

            try {
                if (typeof source === 'string') {
                    // Fetch ArrayBuffer from URL
                    const res = await fetch(source, { credentials: 'same-origin' });
                    if (!res.ok) throw new Error(`HTTP error ${res.status}`);
                    this.rawArrayBuffer = await res.arrayBuffer();
                } else if (source instanceof File || source instanceof Blob) {
                    this.rawArrayBuffer = await source.arrayBuffer();
                } else if (source instanceof ArrayBuffer) {
                    this.rawArrayBuffer = source;
                } else {
                    throw new Error('Unsupported source format');
                }

                // Resilient PDF document loading with automatic fallback
                let loadingTask;
                try {
                    loadingTask = pdfjsLib.getDocument({
                        data: this.rawArrayBuffer.slice(0),
                        cMapUrl: 'https://cdn.jsdelivr.net/npm/pdfjs-dist@3.11.174/cmaps/',
                        cMapPacked: true,
                    });
                    this.pdfDoc = await loadingTask.promise;
                } catch (firstErr) {
                    console.warn("Primary PDF loading failed, attempting CDN fallback worker:", firstErr);
                    try {
                        if (typeof pdfjsLib !== 'undefined') {
                            pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';
                        }
                        loadingTask = pdfjsLib.getDocument({
                            data: this.rawArrayBuffer.slice(0),
                        });
                        this.pdfDoc = await loadingTask.promise;
                    } catch (secondErr) {
                        console.error("Fallback PDF loading failed:", secondErr);
                        throw secondErr;
                    }
                }

                this.numPages = this.pdfDoc.numPages;

                this.renderGrid();
                this._updateToolbar();
                if (this.onSelectionChange) this.onSelectionChange(this.selectedPages, this.numPages);
            } catch (err) {
                console.error("PDF load error:", err);
                this.container.innerHTML = `
                    <div class="alert alert-danger bg-danger bg-opacity-10 border-0 rounded-4 text-center p-4 my-auto w-100" style="max-width: 500px;">
                        <i class="fa-solid fa-triangle-exclamation text-danger fa-2x mb-2"></i>
                        <h6 class="fw-bold text-danger">មិនអាចដំណើរការឯកសារ PDF បានឡើយ</h6>
                        <p class="text-muted small mb-0">${err.message || 'សូមពិនិត្យមើលប្រភេទឯកសារ ឬប្តូររបៀបមើល Browser View។'}</p>
                    </div>
                `;
            }
        }

        /**
         * Render the page-by-page grid layout
         */
        renderGrid() {
            if (!this.container || !this.pdfDoc) return;

            const inst = this.instanceName;
            const pfx = this.idPrefix;

            let html = `
                <div class="pdf-pages-grid-wrapper w-100 p-3">
                    <div class="row g-3 justify-content-center" id="${pfx}PagesGridRow">
            `;

            for (let i = 1; i <= this.numPages; i++) {
                const isChecked = this.selectedPages.has(i);
                html += `
                    <div class="col-6 col-sm-4 col-md-3 col-xl-2.4 pdf-page-col" data-page="${i}">
                        <div class="card h-100 border-0 shadow-sm rounded-3 overflow-hidden pdf-page-card ${isChecked ? 'selected' : ''}" 
                             id="${pfx}Card_${i}" 
                             ondblclick="window['${inst}'].previewPage(${i})">
                            <!-- Card Header Toolbar -->
                            <div class="card-header py-1.5 px-2 bg-light d-flex align-items-center justify-content-between border-bottom">
                                <div class="form-check m-0 d-flex align-items-center gap-1.5" onclick="event.stopPropagation()">
                                    <input class="form-check-input pdf-page-checkbox" type="checkbox" id="${pfx}Check_${i}" 
                                           ${isChecked ? 'checked' : ''} 
                                           onchange="window['${inst}'].togglePage(${i})">
                                    <label class="form-check-label fw-bold text-dark font-monospace fs-8" for="${pfx}Check_${i}">
                                        ទំព័រ ${i}
                                    </label>
                                </div>
                                <div class="d-flex align-items-center gap-1">
                                    <button type="button" class="btn btn-xs btn-outline-secondary rounded-circle p-1" 
                                            title="ចុចមើលទំព័រ ${i} នេះឱ្យធំ (View Page ${i})" 
                                            onclick="event.stopPropagation(); window['${inst}'].previewPage(${i})">
                                        <i class="fa-solid fa-eye text-primary" style="font-size: 11px;"></i>
                                    </button>
                                    <button type="button" class="btn btn-xs btn-outline-primary rounded-circle p-1" 
                                            title="រក្សាទុកតែទំព័រ ${i} នេះជា PDF ថ្មី (ជ្រើស Drive បាន)" 
                                            onclick="event.stopPropagation(); window['${inst}'].saveSinglePage(${i})">
                                        <i class="fa-solid fa-download" style="font-size: 10px;"></i>
                                    </button>
                                </div>
                            </div>
                            
                            <!-- Thumbnail Canvas Container -->
                            <div class="card-body p-2 d-flex flex-column align-items-center justify-content-center bg-white position-relative cursor-pointer" 
                                 style="min-height: 190px;"
                                 onclick="window['${inst}'].previewPage(${i})">
                                <div class="spinner-border spinner-border-sm text-secondary pdf-thumb-loader" id="${pfx}ThumbLoader_${i}"></div>
                                <canvas id="${pfx}Canvas_${i}" class="pdf-thumb-canvas shadow-xs rounded d-none" style="max-width: 100%; height: auto;"></canvas>
                                
                                <div class="pdf-card-overlay d-flex flex-column align-items-center gap-1.5">
                                    <button type="button" class="btn btn-sm btn-primary rounded-pill px-3 py-1 shadow-sm fs-8 fw-bold" 
                                            onclick="event.stopPropagation(); window['${inst}'].previewPage(${i})">
                                        <i class="fa-solid fa-eye me-1"></i> មើលទំព័រនេះ
                                    </button>
                                    <button type="button" class="btn btn-xs btn-light rounded-pill px-2.5 py-0.5 shadow-xs fs-9 text-dark border" 
                                            id="${pfx}OverlaySelectBtn_${i}"
                                            onclick="event.stopPropagation(); window['${inst}'].togglePage(${i})">
                                        <i class="fa-solid ${isChecked ? 'fa-square-check text-success' : 'fa-square'} me-1"></i> ${isChecked ? 'ដោះការជ្រើស' : 'ជ្រើសទំព័រនេះ'}
                                    </button>
                                </div>
                            </div>
                            
                            <!-- Card Footer -->
                            <div class="card-footer py-1 px-2 bg-white text-center border-top d-flex align-items-center justify-content-between">
                                <small class="text-muted fs-9">${i} នៃ ${this.numPages}</small>
                                <a href="javascript:void(0)" class="text-decoration-none fs-9 text-primary fw-semibold" 
                                   onclick="event.stopPropagation(); window['${inst}'].previewPage(${i})">
                                    <i class="fa-solid fa-magnifying-glass-plus me-0.5"></i> មើលធំ
                                </a>
                            </div>
                        </div>
                    </div>
                `;
            }

            html += `
                    </div>
                </div>
            `;

            this.container.innerHTML = html;
            window[this.instanceName] = this;

            // Render thumbnails progressively with requestAnimationFrame
            this._renderAllThumbnails();
        }

        /**
         * Render thumbnails progressively
         */
        async _renderAllThumbnails() {
            for (let pageNum = 1; pageNum <= this.numPages; pageNum++) {
                try {
                    await this._renderSingleThumbnail(pageNum);
                } catch (e) {
                    console.warn(`Render thumbnail failed for page ${pageNum}:`, e);
                }
            }
        }

        async _renderSingleThumbnail(pageNum) {
            if (!this.pdfDoc) return;
            const page = await this.pdfDoc.getPage(pageNum);
            const viewport = page.getViewport({ scale: this.renderScale });

            const canvas = document.getElementById(`${this.idPrefix}Canvas_${pageNum}`);
            const loader = document.getElementById(`${this.idPrefix}ThumbLoader_${pageNum}`);
            if (!canvas) return;

            const context = canvas.getContext('2d');
            canvas.height = viewport.height;
            canvas.width = viewport.width;

            await page.render({
                canvasContext: context,
                viewport: viewport
            }).promise;

            if (loader) loader.classList.add('d-none');
            canvas.classList.remove('d-none');
        }

        /**
         * Toggle selection for a page
         */
        togglePage(pageNum, event) {
            if (event && event.target && event.target.tagName === 'INPUT') {
                // Already handled by checkbox change
            }

            if (this.selectedPages.has(pageNum)) {
                this.selectedPages.delete(pageNum);
            } else {
                this.selectedPages.add(pageNum);
            }

            this._syncCardState(pageNum);
            this._updateToolbar();
            if (this.onSelectionChange) this.onSelectionChange(this.selectedPages, this.numPages);
        }

        _syncCardState(pageNum) {
            const card = document.getElementById(`${this.idPrefix}Card_${pageNum}`);
            const checkbox = document.getElementById(`${this.idPrefix}Check_${pageNum}`);
            const overlayBtn = document.getElementById(`${this.idPrefix}OverlaySelectBtn_${pageNum}`);
            const isSelected = this.selectedPages.has(pageNum);

            if (card) {
                if (isSelected) {
                    card.classList.add('selected');
                } else {
                    card.classList.remove('selected');
                }
            }
            if (checkbox) {
                checkbox.checked = isSelected;
            }
            if (overlayBtn) {
                overlayBtn.innerHTML = `<i class="fa-solid ${isSelected ? 'fa-square-check text-success' : 'fa-square'} me-1"></i> ${isSelected ? 'ដោះការជ្រើស' : 'ជ្រើសទំព័រនេះ'}`;
            }
        }

        /**
         * Select all pages
         */
        selectAll() {
            for (let i = 1; i <= this.numPages; i++) {
                this.selectedPages.add(i);
                this._syncCardState(i);
            }
            this._updateToolbar();
            if (this.onSelectionChange) this.onSelectionChange(this.selectedPages, this.numPages);
        }

        /**
         * Deselect all pages
         */
        deselectAll() {
            this.selectedPages.clear();
            for (let i = 1; i <= this.numPages; i++) {
                this._syncCardState(i);
            }
            this._updateToolbar();
            if (this.onSelectionChange) this.onSelectionChange(this.selectedPages, this.numPages);
        }

        /**
         * Select range e.g. "1-3, 5, 8-10"
         */
        selectRange(rangeStr) {
            if (!rangeStr || !rangeStr.trim()) return;
            const parts = rangeStr.split(/[,;\s]+/);
            for (const part of parts) {
                if (part.includes('-')) {
                    const [startStr, endStr] = part.split('-');
                    const start = parseInt(startStr, 10);
                    const end = parseInt(endStr, 10);
                    if (!isNaN(start) && !isNaN(end)) {
                        const min = Math.max(1, Math.min(start, end));
                        const max = Math.min(this.numPages, Math.max(start, end));
                        for (let i = min; i <= max; i++) {
                            this.selectedPages.add(i);
                            this._syncCardState(i);
                        }
                    }
                } else {
                    const p = parseInt(part, 10);
                    if (!isNaN(p) && p >= 1 && p <= this.numPages) {
                        this.selectedPages.add(p);
                        this._syncCardState(p);
                    }
                }
            }
            this._updateToolbar();
            if (this.onSelectionChange) this.onSelectionChange(this.selectedPages, this.numPages);
        }

        _updateToolbar() {
            const count = this.selectedPages.size;
            const badgeEl = document.getElementById(this.badgeId);
            if (badgeEl) {
                badgeEl.textContent = `${count} / ${this.numPages}`;
                if (count > 0) {
                    badgeEl.className = 'badge bg-success rounded-pill px-2.5 py-1 fs-8';
                } else {
                    badgeEl.className = 'badge bg-secondary rounded-pill px-2.5 py-1 fs-8';
                }
            }

            const extractBtn = document.getElementById(this.saveBtnId);
            if (extractBtn) {
                extractBtn.disabled = (count === 0);
            }

            const eachBtn = document.getElementById(this.eachBtnId);
            if (eachBtn) {
                eachBtn.disabled = (count === 0);
            }
        }

        /**
         * Save single page as new PDF (Shows Drive & Folder selection modal)
         */
        async saveSinglePage(pageNum) {
            const cleanBase = this.currentTitle.replace(/\.[^/.]+$/, "");
            const outName = `${cleanBase}_page_${pageNum}.pdf`;
            await this.promptSaveDialog([pageNum], outName);
        }

        /**
         * Save all selected pages as a new merged PDF (Freely choose Drive / Folder via Modal)
         */
        async saveSelectedPages(customName = null) {
            if (this.selectedPages.size === 0) {
                alert("⚠️ សូមជ្រើសរើសទំព័រយ៉ាងហោចណាស់ ១ ដើម្បីរក្សាទុកជា File ថ្មី!");
                return;
            }

            const sortedPages = Array.from(this.selectedPages).sort((a, b) => a - b);
            const cleanBase = this.currentTitle.replace(/\.[^/.]+$/, "");
            
            let defaultName = '';
            if (sortedPages.length === 1) {
                defaultName = `${cleanBase}_page_${sortedPages[0]}.pdf`;
            } else if (sortedPages.length === this.numPages) {
                defaultName = `${cleanBase}_all_pages.pdf`;
            } else {
                defaultName = `${cleanBase}_pages_${sortedPages.join('-')}.pdf`;
                if (defaultName.length > 60) {
                    defaultName = `${cleanBase}_selected_${sortedPages.length}_pages.pdf`;
                }
            }

            if (customName) {
                const finalFilename = customName.toLowerCase().endsWith('.pdf') ? customName : `${customName}.pdf`;
                await this.extractAndDownload(sortedPages, finalFilename);
                return;
            }

            await this.promptSaveDialog(sortedPages, defaultName);
        }

        /**
         * Prompt modal allowing User PC to choose Drive C, D, USB and Target/Source Folder
         */
        async promptSaveDialog(pagesArray, defaultName) {
            const modalEl = document.getElementById('saveAsPdfDialogModal');
            if (!modalEl || !window.bootstrap) {
                const promptName = prompt("សូមបញ្ចូលឈ្មោះ File PDF ថ្មី (File Name):", defaultName);
                if (!promptName || !promptName.trim()) return;
                const finalFilename = promptName.trim().toLowerCase().endsWith('.pdf') ? promptName.trim() : `${promptName.trim()}.pdf`;
                await this.extractAndDownload(pagesArray, finalFilename);
                return;
            }

            const inputEl = document.getElementById('saveAsPdfModalInput');
            const summaryEl = document.getElementById('saveAsPdfPagesSummary');
            const driveSelect = document.getElementById('modalDriveSelect');
            const folderInput = document.getElementById('modalTargetFolderInput');
            const sourceDisplay = document.getElementById('modalSourceFolderDisplay');
            const previewDisplay = document.getElementById('modalFullTargetPathPreview');
            const confirmBtn = document.getElementById('btnConfirmSaveAsPdf');

            // Auto source folder detection
            let sourceFolder = window.currentPdfSourceFolder;
            if (!sourceFolder || sourceFolder === 'ប្រព័ន្ធ DMS / ឯកសារយោងមន្ត្រី') {
                sourceFolder = localStorage.getItem('dms_pdf_last_source_folder') || 'D:\\Scan_PDF';
            }
            if (sourceDisplay) sourceDisplay.textContent = sourceFolder;

            // Load saved drive & folder or fallback to D: and source folder
            let savedDrive = localStorage.getItem('dms_pdf_last_drive') || 'D:';
            if (driveSelect) driveSelect.value = savedDrive;

            let savedFolder = localStorage.getItem('dms_pdf_last_folder') || sourceFolder;
            if (folderInput) folderInput.value = savedFolder;

            const cleanWithoutPdf = defaultName.replace(/\.pdf$/i, '');
            if (inputEl) inputEl.value = cleanWithoutPdf;
            if (summaryEl) summaryEl.textContent = `ទំព័រដែលបានជ្រើស៖ ${pagesArray.join(', ')} (សរុប ${pagesArray.length} ទំព័រ)`;

            // Real-time preview calculation
            const calcPreview = () => {
                let f = folderInput ? folderInput.value.trim() : 'D:\\Scan_PDF';
                let n = inputEl ? inputEl.value.trim() : cleanWithoutPdf;
                if (!n) n = cleanWithoutPdf;
                if (!n.toLowerCase().endsWith('.pdf')) n += '.pdf';
                
                if (f.endsWith('\\') || f.endsWith('/')) {
                    f = f.slice(0, -1);
                }
                const fullPath = f ? `${f}\\${n}` : n;
                if (previewDisplay) previewDisplay.textContent = fullPath;
                return { folder: f, filename: n, fullPath: fullPath };
            };

            calcPreview();

            const bsModal = bootstrap.Modal.getInstance(modalEl) || new bootstrap.Modal(modalEl);
            bsModal.show();

            return new Promise((resolve) => {
                // Replace button with fresh clone to purge stale event listeners
                const freshBtn = confirmBtn.cloneNode(true);
                confirmBtn.parentNode.replaceChild(freshBtn, confirmBtn);

                freshBtn.addEventListener('click', async () => {
                    const { folder, filename, fullPath } = calcPreview();
                    const chosenDrive = driveSelect ? driveSelect.value : 'D:';

                    // Persist in localStorage for future saves
                    localStorage.setItem('dms_pdf_last_drive', chosenDrive);
                    localStorage.setItem('dms_pdf_last_folder', folder);
                    localStorage.setItem('dms_pdf_last_source_folder', sourceFolder);

                    // Copy path to clipboard
                    if (navigator.clipboard && navigator.clipboard.writeText) {
                        navigator.clipboard.writeText(fullPath).catch(() => {});
                    }

                    bsModal.hide();
                    freshBtn.disabled = true;

                    try {
                        await this.extractAndDownload(pagesArray, filename, chosenDrive, folder);
                    } finally {
                        freshBtn.disabled = false;
                        resolve();
                    }
                });
            });
        }

        /**
         * Save each selected page as its own separate PDF file
         * (If supported, opens folder picker so user can pick any Drive C, D folder to store all files!)
         */
        async saveEachSelectedPageSeparately() {
            if (this.selectedPages.size === 0) {
                alert("⚠️ សូមជ្រើសរើសទំព័រយ៉ាងហោចណាស់ ១!");
                return;
            }

            const sortedPages = Array.from(this.selectedPages).sort((a, b) => a - b);
            const cleanBase = this.currentTitle.replace(/\.[^/.]+$/, "");

            // If Directory Picker is available, let user choose a Drive/Folder directly!
            if (window.isSecureContext && typeof window.showDirectoryPicker === 'function') {
                try {
                    const dirHandle = await window.showDirectoryPicker({
                        mode: 'readwrite'
                    });

                    const eachBtn = document.getElementById(this.eachBtnId);
                    const origHtml = eachBtn ? eachBtn.innerHTML : '';
                    if (eachBtn) {
                        eachBtn.disabled = true;
                        eachBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin me-1"></i> កំពុងរក្សាទុក...';
                    }

                    try {
                        for (let i = 0; i < sortedPages.length; i++) {
                            const pageNum = sortedPages[i];
                            const outName = `${cleanBase}_page_${pageNum}.pdf`;
                            const blob = await this._generatePdfBlob([pageNum]);
                            const fileHandle = await dirHandle.getFileHandle(outName, { create: true });
                            const writable = await fileHandle.createWritable();
                            await writable.write(blob);
                            await writable.close();
                        }
                        this._notifySuccess(`✅ បានរក្សាទុកឯកសារទំព័រទាំង ${sortedPages.length} ទៅក្នុង Drive/Folder «${dirHandle.name}» ដោយជោគជ័យ!`);
                        return;
                    } finally {
                        if (eachBtn) {
                            eachBtn.disabled = (this.selectedPages.size === 0);
                            eachBtn.innerHTML = origHtml;
                        }
                    }
                } catch (err) {
                    if (err.name === 'AbortError') return; // User cancelled directory picker
                    console.warn("showDirectoryPicker failed, falling back to sequential download:", err);
                }
            }

            // Fallback: sequential browser download
            if (!confirm(`តើលោកអ្នកចង់ទាញយកទំព័រទាំង ${sortedPages.length} នេះដាច់ដោយឡែកពីគ្នា (${sortedPages.length} files) មែនទេ?`)) {
                return;
            }

            for (const pageNum of sortedPages) {
                const outName = `${cleanBase}_page_${pageNum}.pdf`;
                await this.extractAndDownload([pageNum], outName);
                await new Promise(r => setTimeout(r, 250));
            }
        }

        /**
         * Reusable PDF generation via PDFLib (Client-side, 100% offline & fast)
         */
        async _generatePdfBlob(pagesArray) {
            if (typeof PDFLib === 'undefined') {
                throw new Error("PDFLib library is not loaded.");
            }
            const { PDFDocument } = PDFLib;
            const srcDoc = await PDFDocument.load(this.rawArrayBuffer);
            const newDoc = await PDFDocument.create();

            const pageIndices = pagesArray.map(p => p - 1).filter(idx => idx >= 0 && idx < srcDoc.getPageCount());
            const copiedPages = await newDoc.copyPages(srcDoc, pageIndices);
            copiedPages.forEach(p => newDoc.addPage(p));

            const pdfBytes = await newDoc.save();
            return new Blob([pdfBytes], { type: 'application/pdf' });
        }

        /**
         * Core extraction logic (Supports Windows File System Access API to choose Drive C:, D:... freely)
         */
        async extractAndDownload(pagesArray, outFilename, chosenDrive = null, chosenFolder = null) {
            if (!this.rawArrayBuffer) {
                alert("⚠️ ឯកសារមិនទាន់ត្រូវបានផ្ទុកពេញលេញនៅឡើយ!");
                return;
            }

            let fileHandle = null;
            const canUseFilePicker = (window.isSecureContext && typeof window.showSaveFilePicker === 'function');

            // Trigger Windows Explorer Save As dialog: users can freely browse to Drive C, D, E, USB & select folders!
            if (canUseFilePicker) {
                try {
                    fileHandle = await window.showSaveFilePicker({
                        suggestedName: outFilename,
                        types: [{
                            description: 'ឯកសារ PDF (*.pdf)',
                            accept: {
                                'application/pdf': ['.pdf'],
                            },
                        }],
                    });
                } catch (pickerErr) {
                    if (pickerErr.name === 'AbortError') {
                        // User cancelled the file picker dialog
                        return null;
                    }
                    console.warn("showSaveFilePicker error, fallback to browser download:", pickerErr);
                    fileHandle = null;
                }
            }

            // Update UI status to show saving progress
            const saveBtn = document.getElementById(this.saveBtnId);
            const origHtml = saveBtn ? saveBtn.innerHTML : '';
            if (saveBtn) {
                saveBtn.disabled = true;
                saveBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin me-1"></i> កំពុងរក្សាទុក...';
            }

            try {
                const blob = await this._generatePdfBlob(pagesArray);

                if (fileHandle) {
                    // Write directly to user-chosen Drive / Folder
                    const writable = await fileHandle.createWritable();
                    await writable.write(blob);
                    await writable.close();

                    const savedName = fileHandle.name || outFilename;
                    this._notifySuccess(`✅ បានរក្សាទុក «${savedName}» ទៅកាន់ទីតាំង Drive ដែលបានជ្រើសរើសដោយជោគជ័យ!`);
                } else {
                    // Fallback: standard browser download
                    const downloadUrl = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = downloadUrl;
                    a.download = outFilename;
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                    setTimeout(() => URL.revokeObjectURL(downloadUrl), 2000);

                    if (chosenDrive && chosenFolder) {
                        this._notifySuccess(`✅ បានរក្សាទុក «${outFilename}» សម្រាប់ ${chosenDrive} (${chosenFolder}) ដោយជោគជ័យ!`);
                    } else {
                        this._notifySuccess(`✅ បានទាញយក «${outFilename}» (${pagesArray.length} ទំព័រ) ដោយជោគជ័យ!`);
                    }
                }

                return blob;
            } catch (err) {
                console.error("Client-side PDF extraction error:", err);
                // Fallback to backend API
                await this._extractViaBackend(pagesArray, outFilename);
            } finally {
                if (saveBtn) {
                    saveBtn.disabled = (this.selectedPages.size === 0);
                    saveBtn.innerHTML = origHtml;
                }
            }
        }

        /**
         * Floating Toast Notification
         */
        _notifySuccess(msg) {
            if (typeof showSystemToast === 'function') {
                showSystemToast(msg);
                return;
            }
            let container = document.querySelector('.pdf-system-toast-container');
            if (!container) {
                container = document.createElement('div');
                container.className = 'pdf-system-toast-container';
                document.body.appendChild(container);
            }

            const toast = document.createElement('div');
            toast.className = 'pdf-system-toast shadow';
            toast.innerHTML = `<i class="fa-solid fa-circle-check fs-5 text-light"></i> <span>${msg}</span>`;
            container.appendChild(toast);

            setTimeout(() => {
                toast.style.opacity = '0';
                toast.style.transform = 'translateY(-20px) scale(0.95)';
                setTimeout(() => toast.remove(), 350);
            }, 3500);
        }

        /**
         * ==============================================================================
         * 🔍 HIGH-RESOLUTION PAGE PREVIEW MODAL & CONTROLS
         * ==============================================================================
         */
        async previewPage(pageNum) {
            if (!this.pdfDoc) return;
            this.currentPreviewPage = Math.max(1, Math.min(this.numPages, pageNum));
            this.previewScale = 1.4;
            this.previewRotation = 0;

            this._ensurePreviewModal();

            // Show Bootstrap Modal
            const modalEl = document.getElementById('pdfPreviewPageModal');
            if (modalEl) {
                if (!this.previewBsModal) {
                    this.previewBsModal = new bootstrap.Modal(modalEl, {
                        backdrop: true,
                        keyboard: true
                    });
                }
                this.previewBsModal.show();
            }

            await this._renderPreviewPage();
        }

        _ensurePreviewModal() {
            let modalEl = document.getElementById('pdfPreviewPageModal');
            if (modalEl) return;

            modalEl = document.createElement('div');
            modalEl.id = 'pdfPreviewPageModal';
            modalEl.className = 'modal fade';
            modalEl.setAttribute('tabindex', '-1');
            modalEl.setAttribute('aria-hidden', 'true');

            modalEl.innerHTML = `
                <div class="modal-dialog modal-fullscreen modal-dialog-centered">
                    <div class="modal-content bg-dark text-white border-0">
                        <!-- Top Toolbar -->
                        <div class="modal-header border-secondary py-2 px-3 bg-black bg-opacity-75 d-flex flex-wrap align-items-center justify-content-between gap-2 shadow-sm">
                            <div class="d-flex align-items-center gap-2 overflow-hidden">
                                <span class="badge bg-danger rounded-pill px-2.5 py-1 fs-8">
                                    <i class="fa-solid fa-file-pdf me-1"></i> មើលទំព័រ
                                </span>
                                <h6 class="modal-title fw-bold text-white m-0 text-truncate" id="previewModalDocTitle" style="max-width: 320px;">
                                    ${this.currentTitle}
                                </h6>
                            </div>

                            <!-- Navigation & Zoom Controls -->
                            <div class="d-flex align-items-center gap-1.5 bg-secondary bg-opacity-25 border border-secondary rounded-pill px-2 py-1">
                                <!-- Prev Page Button -->
                                <button type="button" class="btn btn-sm btn-outline-light rounded-circle p-1.5" id="btnPreviewPrev" title="ទំព័រមុន (Previous - គ្រាប់ចុច ⬅️)">
                                    <i class="fa-solid fa-chevron-left" style="font-size: 11px;"></i>
                                </button>
                                
                                <div class="d-flex align-items-center px-2">
                                    <span class="fs-8 fw-bold text-light" id="previewModalPageCounter">1 / 1</span>
                                </div>

                                <!-- Next Page Button -->
                                <button type="button" class="btn btn-sm btn-outline-light rounded-circle p-1.5" id="btnPreviewNext" title="ទំព័របន្ទាប់ (Next - គ្រាប់ចុច ➡️)">
                                    <i class="fa-solid fa-chevron-right" style="font-size: 11px;"></i>
                                </button>

                                <div class="vr bg-secondary mx-1 my-1"></div>

                                <!-- Zoom Out -->
                                <button type="button" class="btn btn-sm btn-outline-light rounded-circle p-1.5" id="btnPreviewZoomOut" title="បង្រួម (Zoom Out -)">
                                    <i class="fa-solid fa-magnifying-glass-minus" style="font-size: 11px;"></i>
                                </button>

                                <!-- Zoom Reset -->
                                <button type="button" class="btn btn-sm btn-outline-secondary text-light rounded-pill px-2 fs-9 font-monospace" id="btnPreviewZoomReset" title="កំណត់ទំហំដើម (Reset Zoom)">
                                    100%
                                </button>

                                <!-- Zoom In -->
                                <button type="button" class="btn btn-sm btn-outline-light rounded-circle p-1.5" id="btnPreviewZoomIn" title="ពង្រីក (Zoom In +)">
                                    <i class="fa-solid fa-magnifying-glass-plus" style="font-size: 11px;"></i>
                                </button>

                                <!-- Rotate -->
                                <button type="button" class="btn btn-sm btn-outline-light rounded-circle p-1.5" id="btnPreviewRotate" title="បង្វិល 90° (Rotate R)">
                                    <i class="fa-solid fa-rotate-right" style="font-size: 11px;"></i>
                                </button>
                            </div>

                            <!-- Actions: Select Checkbox, Save this page, Close -->
                            <div class="d-flex align-items-center gap-2">
                                <button type="button" class="btn btn-sm btn-outline-light rounded-pill px-3 py-1.5 fs-8 fw-bold" id="btnPreviewToggleSelect">
                                    <i class="fa-solid fa-check-circle me-1"></i> <span id="previewModalSelectLabel">ជ្រើសរើសទំព័រនេះ</span>
                                </button>

                                <button type="button" class="btn btn-sm btn-success rounded-pill px-3 py-1.5 fs-8 fw-bold shadow-xs" id="btnPreviewSavePage" title="រក្សាទុកទំព័រនេះទៅកាន់ Drive">
                                    <i class="fa-solid fa-download me-1"></i> រក្សាទុកទំព័រនេះជា PDF
                                </button>

                                <button type="button" class="btn-close btn-close-white ms-2" data-bs-dismiss="modal" aria-label="Close"></button>
                            </div>
                        </div>

                        <!-- Modal Body (Canvas Viewport) -->
                        <div class="modal-body p-3 d-flex align-items-center justify-content-center overflow-auto position-relative" id="previewModalViewport" style="min-height: calc(100vh - 65px); background: #1a1d21;">
                            <div class="spinner-border text-primary position-absolute d-none" id="previewModalSpinner" style="width: 3rem; height: 3rem; z-index: 10;"></div>
                            <div id="previewModalCanvasWrapper" class="d-flex justify-content-center align-items-center">
                                <canvas id="previewModalCanvas" class="shadow-lg rounded bg-white" style="transition: transform 0.15s ease;"></canvas>
                            </div>
                        </div>
                    </div>
                </div>
            `;

            document.body.appendChild(modalEl);

            // Event listeners
            document.getElementById('btnPreviewPrev').addEventListener('click', () => this.previewPrevPage());
            document.getElementById('btnPreviewNext').addEventListener('click', () => this.previewNextPage());
            document.getElementById('btnPreviewZoomOut').addEventListener('click', () => this.previewZoom(-0.25));
            document.getElementById('btnPreviewZoomIn').addEventListener('click', () => this.previewZoom(0.25));
            document.getElementById('btnPreviewZoomReset').addEventListener('click', () => this.previewResetZoom());
            document.getElementById('btnPreviewRotate').addEventListener('click', () => this.previewRotate());
            document.getElementById('btnPreviewToggleSelect').addEventListener('click', () => this.previewToggleCurrentSelection());
            document.getElementById('btnPreviewSavePage').addEventListener('click', () => this.previewSaveCurrentPage());

            // Keyboard navigation
            modalEl.addEventListener('keydown', (e) => {
                if (e.key === 'ArrowLeft') {
                    e.preventDefault();
                    this.previewPrevPage();
                } else if (e.key === 'ArrowRight') {
                    e.preventDefault();
                    this.previewNextPage();
                } else if (e.key === '+' || e.key === '=') {
                    e.preventDefault();
                    this.previewZoom(0.25);
                } else if (e.key === '-' || e.key === '_') {
                    e.preventDefault();
                    this.previewZoom(-0.25);
                } else if (e.key === 'r' || e.key === 'R') {
                    e.preventDefault();
                    this.previewRotate();
                } else if (e.key === ' ') {
                    e.preventDefault();
                    this.previewToggleCurrentSelection();
                }
            });
        }

        async _renderPreviewPage() {
            if (!this.pdfDoc) return;
            const pageNum = this.currentPreviewPage;

            // Update header labels
            const titleEl = document.getElementById('previewModalDocTitle');
            if (titleEl) titleEl.textContent = `${this.currentTitle} — ទំព័រទី ${pageNum}`;

            const counterEl = document.getElementById('previewModalPageCounter');
            if (counterEl) counterEl.textContent = `${pageNum} / ${this.numPages}`;

            const prevBtn = document.getElementById('btnPreviewPrev');
            if (prevBtn) prevBtn.disabled = (pageNum <= 1);

            const nextBtn = document.getElementById('btnPreviewNext');
            if (nextBtn) nextBtn.disabled = (pageNum >= this.numPages);

            // Update select button label
            const isSelected = this.selectedPages.has(pageNum);
            const selectBtn = document.getElementById('btnPreviewToggleSelect');
            if (selectBtn) {
                if (isSelected) {
                    selectBtn.className = 'btn btn-sm btn-success rounded-pill px-3 py-1.5 fs-8 fw-bold';
                    selectBtn.innerHTML = '<i class="fa-solid fa-check-double me-1"></i> <span id="previewModalSelectLabel">បានជ្រើសទំព័រនេះ ✓</span>';
                } else {
                    selectBtn.className = 'btn btn-sm btn-outline-light rounded-pill px-3 py-1.5 fs-8 fw-bold';
                    selectBtn.innerHTML = '<i class="fa-solid fa-check-circle me-1"></i> <span id="previewModalSelectLabel">ជ្រើសរើសទំព័រនេះ</span>';
                }
            }

            const zoomResetBtn = document.getElementById('btnPreviewZoomReset');
            if (zoomResetBtn) {
                const pct = Math.round((this.previewScale / 1.4) * 100);
                zoomResetBtn.textContent = `${pct}%`;
            }

            const spinner = document.getElementById('previewModalSpinner');
            const canvas = document.getElementById('previewModalCanvas');
            if (!canvas) return;

            if (spinner) spinner.classList.remove('d-none');

            try {
                const page = await this.pdfDoc.getPage(pageNum);
                const totalRotation = ((page.rotate || 0) + (this.previewRotation || 0)) % 360;
                const viewport = page.getViewport({ scale: this.previewScale, rotation: totalRotation });

                const ctx = canvas.getContext('2d');
                canvas.width = viewport.width;
                canvas.height = viewport.height;

                await page.render({
                    canvasContext: ctx,
                    viewport: viewport
                }).promise;
            } catch (err) {
                console.warn("Preview render error:", err);
            } finally {
                if (spinner) spinner.classList.add('d-none');
            }
        }

        previewPrevPage() {
            if (this.currentPreviewPage > 1) {
                this.currentPreviewPage--;
                this._renderPreviewPage();
            }
        }

        previewNextPage() {
            if (this.currentPreviewPage < this.numPages) {
                this.currentPreviewPage++;
                this._renderPreviewPage();
            }
        }

        previewZoom(delta) {
            this.previewScale = Math.max(0.6, Math.min(3.5, this.previewScale + delta));
            this._renderPreviewPage();
        }

        previewResetZoom() {
            this.previewScale = 1.4;
            this._renderPreviewPage();
        }

        previewRotate() {
            this.previewRotation = (this.previewRotation + 90) % 360;
            this._renderPreviewPage();
        }

        previewToggleCurrentSelection() {
            this.togglePage(this.currentPreviewPage);
            this._renderPreviewPage();
        }

        previewSaveCurrentPage() {
            this.saveSinglePage(this.currentPreviewPage);
        }

        /**
         * Server-side extraction fallback via Python pypdf API
         */
        async _extractViaBackend(pagesArray, outFilename) {
            try {
                const formData = new FormData();
                const blob = new Blob([this.rawArrayBuffer], { type: 'application/pdf' });
                formData.append('pdf_file', blob, this.currentTitle);
                formData.append('pages', pagesArray.join(','));
                formData.append('filename', outFilename);
                formData.append('action', 'download');

                const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
                const res = await fetch('/api/pdf/extract-pages/', {
                    method: 'POST',
                    headers: { 'X-CSRFToken': csrfToken },
                    body: formData
                });

                if (!res.ok) throw new Error(`Server returned ${res.status}`);
                const resBlob = await res.blob();
                const downloadUrl = URL.createObjectURL(resBlob);
                const a = document.createElement('a');
                a.href = downloadUrl;
                a.download = outFilename;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                setTimeout(() => URL.revokeObjectURL(downloadUrl), 2000);
            } catch (backendErr) {
                console.error("Backend extraction failed:", backendErr);
                alert(`⚠️ ការបំបែកឯកសារបរាជ័យ៖ ${backendErr.message}`);
            }
        }

        /**
         * Save directly into Officer's reference documents (OfficerAttachment)
         */
        async saveToOfficerProfile(officerId, category = 'OTHER', customTitle = null, docNumber = '', issuedDate = '') {
            if (this.selectedPages.size === 0) {
                alert("⚠️ សូមជ្រើសរើសទំព័រយ៉ាងហោចណាស់ ១!");
                return;
            }

            const sortedPages = Array.from(this.selectedPages).sort((a, b) => a - b);
            const cleanBase = this.currentTitle.replace(/\.[^/.]+$/, "");
            const title = customTitle || prompt("សូមបញ្ចូលចំណងជើងឯកសារយោងថ្មី៖", `${cleanBase} (ទំព័រ ${sortedPages.join(',')})`);
            if (!title || !title.trim()) return;

            try {
                const blob = await this._generatePdfBlob(sortedPages);

                const formData = new FormData();
                formData.append('file', blob, `${title.trim()}.pdf`);
                formData.append('title', title.trim());
                formData.append('category', category);
                if (docNumber) formData.append('doc_number', docNumber);
                if (issuedDate) formData.append('issued_date', issuedDate);
                formData.append('description', `បំបែកចេញពីឯកសារដើម៖ «${this.currentTitle}» (ទំព័រ ${sortedPages.join(', ')})`);

                // Ensure CSRF token is obtained from input or cookies
                let csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
                if (!csrfToken) {
                    const cookieMatch = document.cookie.match(/csrftoken=([^;]+)/);
                    if (cookieMatch) csrfToken = decodeURIComponent(cookieMatch[1]);
                }
                if (!csrfToken) csrfToken = '';

                formData.append('csrfmiddlewaretoken', csrfToken);

                const res = await fetch(`/officers/${officerId}/attachments/add/`, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': csrfToken,
                        'X-Requested-With': 'XMLHttpRequest'
                    },
                    body: formData
                });

                if (res.ok) {
                    // Mark the saved pages visually with a green badge
                    sortedPages.forEach(p => {
                        const card = document.getElementById(`pdfCard-${p}`);
                        if (card) {
                            let badge = card.querySelector('.page-saved-badge');
                            if (!badge) {
                                badge = document.createElement('span');
                                badge.className = 'page-saved-badge badge bg-success position-absolute top-0 start-0 m-2 shadow-xs fs-9';
                                badge.innerHTML = '<i class="fa-solid fa-circle-check me-1"></i>បានបញ្ចូល';
                                badge.style.zIndex = '5';
                                card.appendChild(badge);
                            }
                        }
                    });

                    // Deselect previous pages so user can immediately pick other pages
                    this.deselectAll();

                    this._notifySuccess(`✅ បានបញ្ចូល «${title.trim()}» (ទំព័រ ${sortedPages.join(', ')}) ជូនមន្ត្រីរួចរាល់! ឯកសារ PDF នៅរក្សាដដែល លោកអ្នកអាចជ្រើសរើសទំព័រផ្សេងទៀតបន្តបាន។`);
                    return true;
                } else {
                    let errorMsg = `Server returned HTTP ${res.status}`;
                    try {
                        const errJson = await res.json();
                        if (errJson.error) errorMsg = errJson.error;
                    } catch (e) {
                        const errText = await res.text();
                        if (errText) console.warn("Save attachment error details:", errText);
                    }
                    throw new Error(errorMsg);
                }
            } catch (err) {
                console.error("Save to officer profile error:", err);
                alert(`⚠️ មិនអាចរក្សាទុកចូលក្នុងប្រវត្តិរូបមន្ត្រីបានឡើយ៖ ${err.message}`);
                return false;
            }
        }
    }

    // Export class globally
    window.PdfPageViewer = PdfPageViewer;

})(window);
