package com.dmc.system;

import android.annotation.SuppressLint;
import android.app.AlertDialog;
import android.app.DownloadManager;
import android.content.Context;
import android.content.DialogInterface;
import android.content.Intent;
import android.content.SharedPreferences;
import android.graphics.Bitmap;
import android.net.Uri;
import android.os.Bundle;
import android.os.Environment;
import android.view.KeyEvent;
import android.view.View;
import android.webkit.CookieManager;
import android.webkit.DownloadListener;
import android.webkit.URLUtil;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.EditText;
import android.widget.ProgressBar;
import android.widget.Toast;

import androidx.annotation.Nullable;
import androidx.appcompat.app.AppCompatActivity;
import androidx.swiperefreshlayout.widget.SwipeRefreshLayout;

public class MainActivity extends AppCompatActivity {

    private static final String PREF_NAME = "DMC_PREFS";
    private static final String KEY_SERVER_URL = "SERVER_URL";
    private static final String DEFAULT_URL = "http://192.168.1.97:8000/";
    private static final int FILE_CHOOSER_REQUEST_CODE = 1001;

    private WebView webView;
    private SwipeRefreshLayout swipeRefreshLayout;
    private ProgressBar progressBar;
    private ValueCallback<Uri[]> fileUploadCallback;
    private SharedPreferences prefs;

    @SuppressLint("SetJavaScriptEnabled")
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        prefs = getSharedPreferences(PREF_NAME, Context.MODE_PRIVATE);

        webView = findViewById(R.id.webView);
        swipeRefreshLayout = findViewById(R.id.swipeRefreshLayout);
        progressBar = findViewById(R.id.progressBar);

        setupWebView();
        setupSwipeRefresh();

        loadCurrentServer();
    }

    /**
     * Fixes and ensures proper scheme and port 8000 for local network connections,
     * while preserving HTTPS for public Cloudflare Tunnels.
     */
    private String formatServerUrl(String raw) {
        if (raw == null) return DEFAULT_URL;
        String url = raw.trim();
        if (url.isEmpty()) return DEFAULT_URL;

        // Ensure protocol
        if (!url.startsWith("http://") && !url.startsWith("https://")) {
            url = "http://" + url;
        }

        // If scheme is http:// and user did not specify any port, fix port to 8000
        try {
            Uri parsed = Uri.parse(url);
            String host = parsed.getHost();
            int port = parsed.getPort();
            if (port == -1 && !url.startsWith("https://") && host != null && !host.isEmpty()) {
                String path = parsed.getPath();
                if (path == null || path.isEmpty()) {
                    path = "/";
                }
                url = "http://" + host + ":8000" + path;
            }
        } catch (Exception ignored) {
        }

        if (!url.endsWith("/")) {
            url = url + "/";
        }
        return url;
    }

    @SuppressLint("SetJavaScriptEnabled")
    private void setupWebView() {
        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setDatabaseEnabled(true);
        settings.setAllowFileAccess(true);
        settings.setAllowContentAccess(true);
        settings.setLoadWithOverviewMode(true);
        settings.setUseWideViewPort(true);
        settings.setSupportZoom(true);
        settings.setBuiltInZoomControls(true);
        settings.setDisplayZoomControls(false);
        settings.setTextZoom(100);
        settings.setLayoutAlgorithm(WebSettings.LayoutAlgorithm.NORMAL);
        settings.setCacheMode(WebSettings.LOAD_DEFAULT);
        settings.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);

        CookieManager cookieManager = CookieManager.getInstance();
        cookieManager.setAcceptCookie(true);
        cookieManager.setAcceptThirdPartyCookies(webView, true);

        // Enable downloading reports, Excel files, PDF forms, and documents
        webView.setDownloadListener(new DownloadListener() {
            @Override
            public void onDownloadStart(String url, String userAgent, String contentDisposition, String mimeType, long contentLength) {
                try {
                    DownloadManager.Request request = new DownloadManager.Request(Uri.parse(url));
                    if (mimeType != null && !mimeType.isEmpty()) {
                        request.setMimeType(mimeType);
                    }
                    String cookies = CookieManager.getInstance().getCookie(url);
                    if (cookies != null) {
                        request.addRequestHeader("cookie", cookies);
                    }
                    if (userAgent != null) {
                        request.addRequestHeader("User-Agent", userAgent);
                    }
                    request.setDescription("DMC System - កំពុងទាញយកឯកសារ...");
                    String filename = URLUtil.guessFileName(url, contentDisposition, mimeType);
                    request.setTitle(filename);
                    request.allowScanningByMediaScanner();
                    request.setNotificationVisibility(DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED);
                    request.setDestinationInExternalPublicDir(Environment.DIRECTORY_DOWNLOADS, filename);

                    DownloadManager dm = (DownloadManager) getSystemService(Context.DOWNLOAD_SERVICE);
                    if (dm != null) {
                        dm.enqueue(request);
                        Toast.makeText(MainActivity.this, "📥 កំពុងទាញយកឯកសារ៖ " + filename, Toast.LENGTH_SHORT).show();
                    }
                } catch (Exception e) {
                    try {
                        Intent intent = new Intent(Intent.ACTION_VIEW, Uri.parse(url));
                        startActivity(intent);
                    } catch (Exception ex) {
                        Toast.makeText(MainActivity.this, "មិនអាចទាញយកឯកសារបានឡើយ: " + e.getMessage(), Toast.LENGTH_SHORT).show();
                    }
                }
            }
        });

        webView.setWebViewClient(new WebViewClient() {
            @Override
            public void onPageStarted(WebView view, String url, Bitmap favicon) {
                super.onPageStarted(view, url, favicon);
                progressBar.setVisibility(View.VISIBLE);
            }

            @Override
            public void onPageFinished(WebView view, String url) {
                super.onPageFinished(view, url);
                progressBar.setVisibility(View.GONE);
                swipeRefreshLayout.setRefreshing(false);
            }

            @Override
            public void onReceivedError(WebView view, WebResourceRequest request, WebResourceError error) {
                super.onReceivedError(view, request, error);
                if (request.isForMainFrame()) {
                    showConnectionErrorDialog();
                }
            }
        });

        webView.setWebChromeClient(new WebChromeClient() {
            @Override
            public void onProgressChanged(WebView view, int newProgress) {
                progressBar.setProgress(newProgress);
            }

            // Support photo and document uploads in form
            @Override
            public boolean onShowFileChooser(WebView webView, ValueCallback<Uri[]> filePathCallback,
                                            FileChooserParams fileChooserParams) {
                if (fileUploadCallback != null) {
                    fileUploadCallback.onReceiveValue(null);
                }
                fileUploadCallback = filePathCallback;

                Intent intent = fileChooserParams.createIntent();
                try {
                    startActivityForResult(intent, FILE_CHOOSER_REQUEST_CODE);
                } catch (Exception e) {
                    fileUploadCallback = null;
                    Toast.makeText(MainActivity.this, "មិនអាចបើកកម្មវិធីជ្រើសរើសឯកសារបានឡើយ", Toast.LENGTH_SHORT).show();
                    return false;
                }
                return true;
            }
        });

        // Long press anywhere to configure IP/Port settings
        webView.setOnLongClickListener(v -> {
            showServerSettingsDialog();
            return false;
        });
    }

    private void setupSwipeRefresh() {
        swipeRefreshLayout.setColorSchemeResources(R.color.primary_emerald, R.color.accent_amber);
        swipeRefreshLayout.setOnRefreshListener(() -> webView.reload());
        swipeRefreshLayout.setOnChildScrollUpCallback((parent, child) -> webView.getScrollY() > 0);
    }

    private void loadCurrentServer() {
        String url = prefs.getString(KEY_SERVER_URL, DEFAULT_URL);
        webView.loadUrl(url);
    }

    public void showServerSettingsDialog() {
        AlertDialog.Builder builder = new AlertDialog.Builder(this);
        builder.setTitle("កំណត់អាសយដ្ឋាន Server (DMC System)");
        builder.setMessage("សូមបញ្ចូលលេខ IP របស់កុំព្យូទ័រ Server (Port 8000 ត្រូវបានកំណត់ដោយស្វ័យប្រវត្ត)៖\n(ឧទាហរណ៍៖ " + DEFAULT_URL + ")៖");

        final EditText input = new EditText(this);
        input.setSingleLine(true);
        input.setText(prefs.getString(KEY_SERVER_URL, DEFAULT_URL));
        if (input.getText() != null) {
            input.setSelection(input.getText().length());
        }
        builder.setView(input);

        builder.setPositiveButton("រក្សាទុក & ភ្ជាប់", (dialog, which) -> {
            String newUrl = formatServerUrl(input.getText().toString());
            prefs.edit().putString(KEY_SERVER_URL, newUrl).apply();
            webView.loadUrl(newUrl);
            Toast.makeText(this, "បានប្តូរអាសយដ្ឋានទៅ៖ " + newUrl, Toast.LENGTH_SHORT).show();
        });

        builder.setNeutralButton("កំណត់លំនាំដើម", (dialog, which) -> {
            prefs.edit().putString(KEY_SERVER_URL, DEFAULT_URL).apply();
            webView.loadUrl(DEFAULT_URL);
            Toast.makeText(this, "បានកំណត់ទៅអាសយដ្ឋានដើម៖ " + DEFAULT_URL, Toast.LENGTH_SHORT).show();
        });

        builder.setNegativeButton("បោះបង់", (dialog, which) -> dialog.cancel());
        builder.show();
    }

    private void showConnectionErrorDialog() {
        AlertDialog.Builder builder = new AlertDialog.Builder(this);
        builder.setTitle("មិនអាចភ្ជាប់ទៅកាន់ Server (Port 8000)");
        builder.setMessage("មិនអាចភ្ជាប់ទៅកាន់ DMC System ឡើយ។\n\nសូមពិនិត្យមើល៖\n១. ទូរស័ព្ទបានភ្ជាប់ Wi-Fi តែមួយជាមួយ Server (ឬបើក Cloudflare Tunnel)\n២. Server បានបើកដំណើរការ (Port 8000)\n៣. ពិនិត្យលេខ IP របស់កុំព្យូទ័រ Server");
        builder.setPositiveButton("ប្តូរលេខ IP Server", (dialog, which) -> showServerSettingsDialog());
        builder.setNegativeButton("ព្យាយាមម្តងទៀត", (dialog, which) -> webView.reload());
        builder.show();
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, @Nullable Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode == FILE_CHOOSER_REQUEST_CODE) {
            if (fileUploadCallback != null) {
                Uri[] results = null;
                if (resultCode == RESULT_OK && data != null) {
                    if (data.getData() != null) {
                        results = new Uri[]{data.getData()};
                    } else if (data.getClipData() != null) {
                        int count = data.getClipData().getItemCount();
                        results = new Uri[count];
                        for (int i = 0; i < count; i++) {
                            results[i] = data.getClipData().getItemAt(i).getUri();
                        }
                    }
                }
                fileUploadCallback.onReceiveValue(results);
                fileUploadCallback = null;
            }
        }
    }

    @Override
    public boolean onKeyDown(int keyCode, KeyEvent event) {
        if (keyCode == KeyEvent.KEYCODE_BACK && webView.canGoBack()) {
            webView.goBack();
            return true;
        }
        return super.onKeyDown(keyCode, event);
    }
}

// Auto-Build Trigger: 2026-11-02 15:59:49
