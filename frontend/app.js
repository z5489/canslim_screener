// App State
let appState = {
    dates: [],
    selectedDate: "",
    rawData: [],      // Parsed rows from CSV
    filteredData: [], // Rows after applying search & pass/all toggle
    sortColumn: "passes_all",
    sortOrder: "desc", // "asc" or "desc"
    filterMode: "passing", // "passing" or "all"
    searchQuery: ""
};

// DOM Elements
const dateSelect = document.getElementById("date-select");
const searchInput = document.getElementById("search-input");
const togglePassing = document.getElementById("toggle-passing");
const toggleAll = document.getElementById("toggle-all");
const exportCsvBtn = document.getElementById("export-csv-btn");
const tbody = document.getElementById("screener-tbody");
const errorBanner = document.getElementById("error-banner");
const errorMessage = document.getElementById("error-message");
const errorClose = document.getElementById("error-close");
const noResultsMsg = document.getElementById("no-results-msg");

const statTotal = document.getElementById("stat-total");
const statPassed = document.getElementById("stat-passed");
const statRate = document.getElementById("stat-rate");
const statTimestamp = document.getElementById("stat-timestamp");

// Initialize application on load
window.addEventListener("DOMContentLoaded", init);

function init() {
    setupEventListeners();
    fetchManifest();
}

function setupEventListeners() {
    // Date Dropdown change
    dateSelect.addEventListener("change", (e) => {
        if (e.target.value) {
            loadDateData(e.target.value);
        }
    });

    // Search Input
    searchInput.addEventListener("input", (e) => {
        appState.searchQuery = e.target.value.trim().toLowerCase();
        applyFiltersAndRender();
    });

    // Filter Buttons
    togglePassing.addEventListener("click", () => {
        setActiveFilter("passing");
    });
    toggleAll.addEventListener("click", () => {
        setActiveFilter("all");
    });

    // Export CSV
    exportCsvBtn.addEventListener("click", exportFilteredToCSV);

    // Error Close
    errorClose.addEventListener("click", () => {
        errorBanner.classList.add("hidden");
    });

    // Column headers sorting
    document.querySelectorAll("th.sortable").forEach(th => {
        th.addEventListener("click", () => {
            const column = th.dataset.sort;
            handleSort(column);
        });
    });
}

// Set active filter tab (Passing only vs All)
function setActiveFilter(mode) {
    appState.filterMode = mode;
    
    if (mode === "passing") {
        togglePassing.classList.add("active");
        togglePassing.querySelector(".dot").className = "dot green";
        toggleAll.classList.remove("active");
        toggleAll.querySelector(".dot").className = "dot gray";
    } else {
        toggleAll.classList.add("active");
        toggleAll.querySelector(".dot").className = "dot green";
        togglePassing.classList.remove("active");
        togglePassing.querySelector(".dot").className = "dot gray";
    }
    
    applyFiltersAndRender();
}

// Fetch list of available dates from manifest.json
function fetchManifest() {
    // Adjust manifest path to point relative to the root
    const manifestUrl = "./output/manifest.json?t=" + Date.now();

    fetch(manifestUrl)
        .then(response => {
            if (!response.ok) {
                throw new Error("Manifest file not found");
            }
            return response.json();
        })
        .then(data => {
            if (data.dates && data.dates.length > 0) {
                appState.dates = data.dates;
                populateDateDropdown();
                // Select and load the latest date
                const latestDate = data.dates[0];
                dateSelect.value = latestDate;
                loadDateData(latestDate);
            } else {
                showError("No data available in manifest.");
            }
        })
        .catch(err => {
            console.error("Manifest error:", err);
            showError("No data available yet. Please run the data pipeline first.");
        });
}

function populateDateDropdown() {
    dateSelect.innerHTML = "";
    appState.dates.forEach(date => {
        const option = document.createElement("option");
        option.value = date;
        option.textContent = date;
        dateSelect.appendChild(option);
    });
}

// Load individual dated CSV file
function loadDateData(dateString) {
    appState.selectedDate = dateString;
    const csvUrl = `./output/output_${dateString}.csv?v=${Date.now()}`;
    
    // Show loading spinner or text
    tbody.innerHTML = `<tr><td colspan="13" class="text-center py-8 text-muted">Loading ${dateString} data...</td></tr>`;
    errorBanner.classList.add("hidden");

    fetch(csvUrl)
        .then(response => {
            if (!response.ok) {
                throw new Error(`Data for ${dateString} is unavailable.`);
            }
            return response.text();
        })
        .then(csvText => {
            // Parse CSV with PapaParse
            const parsed = Papa.parse(csvText, {
                header: true,
                dynamicTyping: true,
                skipEmptyLines: true
            });
            
            appState.rawData = parsed.data;
            applyFiltersAndRender();
        })
        .catch(err => {
            console.error("CSV loading error:", err);
            showError(`Failed to load data for ${dateString}. Select another date.`);
            tbody.innerHTML = `<tr><td colspan="13" class="text-center py-8 text-danger">⚠️ Failed to load data for ${dateString}</td></tr>`;
        });
}

// Helper to convert yfinance boolean strings/values to proper JS boolean
function parseBool(val) {
    if (val === true || val === "True" || val === "true") return true;
    if (val === false || val === "False" || val === "false") return false;
    return null;
}

// Apply Filters (Search, Pass/All) and Sorting, then Render Table
function applyFiltersAndRender() {
    let data = [...appState.rawData];

    // Filter 1: Pass/All Toggle
    if (appState.filterMode === "passing") {
        data = data.filter(row => parseBool(row.passes_all) === true);
    }

    // Filter 2: Search Query
    if (appState.searchQuery) {
        data = data.filter(row => {
            const ticker = (row.ticker || "").toString().toLowerCase();
            const name = (row.name || "").toString().toLowerCase();
            return ticker.includes(appState.searchQuery) || name.includes(appState.searchQuery);
        });
    }

    // Sort Data
    const col = appState.sortColumn;
    const order = appState.sortOrder;

    data.sort((a, b) => {
        let valA = a[col];
        let valB = b[col];

        // Custom comparator for specific fields
        if (col.endsWith("_passes") || col === "passes_all") {
            valA = parseBool(valA);
            valB = parseBool(valB);
        }

        // Put nulls, undefined, and N/A values at the end of sorting
        const isNA_A = valA === null || valA === undefined || valA === "N/A" || valA === "Unknown";
        const isNA_B = valB === null || valB === undefined || valB === "N/A" || valB === "Unknown";

        if (isNA_A && isNA_B) return 0;
        if (isNA_A) return 1;
        if (isNA_B) return -1;

        if (typeof valA === "string" && typeof valB === "string") {
            return order === "asc" 
                ? valA.localeCompare(valB) 
                : valB.localeCompare(valA);
        } else {
            // Numeric or Boolean
            if (valA < valB) return order === "asc" ? -1 : 1;
            if (valA > valB) return order === "asc" ? 1 : -1;
            return 0;
        }
    });

    appState.filteredData = data;
    renderSummaryStats();
    renderTable();
    updateSortHeadersUI();
}

function renderSummaryStats() {
    const total = appState.rawData.length;
    // Tickers that passed all criteria (excluding any rows that contain errors)
    const passed = appState.rawData.filter(row => parseBool(row.passes_all) === true && !row.error).length;
    const rate = total > 0 ? ((passed / total) * 100).toFixed(1) : 0;

    statTotal.textContent = total.toLocaleString();
    statPassed.textContent = passed.toLocaleString();
    statRate.textContent = `${rate}%`;

    // Find the latest fetch timestamp in the data
    const firstRow = appState.rawData[0];
    if (firstRow && firstRow.fetched_at) {
        // Parse fetched_at ISO string
        try {
            const date = new Date(firstRow.fetched_at);
            // Format to a readable string (UTC)
            const pad = (n) => n.toString().padStart(2, '0');
            const formatted = `${date.getUTCFullYear()}-${pad(date.getUTCMonth()+1)}-${pad(date.getUTCDate())} ${pad(date.getUTCHours())}:${pad(date.getUTCMinutes())} UTC`;
            statTimestamp.textContent = formatted;
        } catch (e) {
            statTimestamp.textContent = firstRow.fetched_at;
        }
    } else {
        statTimestamp.textContent = "N/A";
    }
}

function renderTable() {
    tbody.innerHTML = "";
    
    if (appState.filteredData.length === 0) {
        noResultsMsg.classList.remove("hidden");
        return;
    }
    noResultsMsg.classList.add("hidden");

    appState.filteredData.forEach(row => {
        const tr = document.createElement("tr");
        
        // Error Row check
        const hasError = !!row.error;
        if (hasError) {
            tr.className = "error-row";
            tr.innerHTML = `
                <td class="ticker-col">${escapeHtml(row.ticker)}</td>
                <td class="name-col" colspan="10">
                    <span class="error-badge">API Error</span> ${escapeHtml(row.error)}
                </td>
                <td class="text-center">
                    <span class="badge fail">✗ Fail</span>
                </td>
            `;
            tbody.appendChild(tr);
            return;
        }

        const passesAll = parseBool(row.passes_all);
        if (!passesAll) {
            tr.className = "failing-row";
        }

        // Cell template generator
        const createCellHTML = (passField, valField) => {
            const pass = parseBool(row[passField]);
            const val = row[valField];
            
            if (pass === null || val === "N/A" || val === "Unknown") {
                return `<td class="text-center"><span class="badge na">— N/A</span></td>`;
            }
            if (pass === true) {
                return `<td class="text-center"><span class="badge pass">✓ Pass</span><span class="cell-value">${escapeHtml(val)}</span></td>`;
            } else {
                return `<td class="text-center failing-cell"><span class="badge fail">✗ Fail</span><span class="cell-value">${escapeHtml(val)}</span></td>`;
            }
        };

        tr.innerHTML = `
            <td class="ticker-col">${escapeHtml(row.ticker)}</td>
            <td class="name-col" title="${escapeHtml(row.name)}">${escapeHtml(row.name)}</td>
            <td class="text-right font-semibold">$${row.price ? Number(row.price).toFixed(2) : "—"}</td>
            ${createCellHTML("c1_price_vs_52w_low_passes", "c1_price_vs_52w_low_value")}
            ${createCellHTML("c2_market_cap_passes", "c2_market_cap_value")}
            ${createCellHTML("c3_eps_growth_passes", "c3_eps_growth_value")}
            ${createCellHTML("c4_avg_volume_passes", "c4_avg_volume_value")}
            ${createCellHTML("c5_price_vs_sma50_passes", "c5_price_vs_sma50_value")}
            ${createCellHTML("c6_volatility_1m_passes", "c6_volatility_1m_value")}
            ${createCellHTML("c7_revenue_growth_passes", "c7_revenue_growth_value")}
            ${createCellHTML("c8_float_passes", "c8_float_value")}
            ${createCellHTML("c9_us_market_passes", "c9_us_market_value")}
            <td class="text-center">
                <span class="badge ${passesAll ? 'pass' : 'fail'}">${passesAll ? '✓ Pass' : '✗ Fail'}</span>
            </td>
        `;
        
        tbody.appendChild(tr);
    });
}

function updateSortHeadersUI() {
    document.querySelectorAll("th.sortable").forEach(th => {
        const column = th.dataset.sort;
        const indicator = th.querySelector(".sort-indicator");
        
        if (column === appState.sortColumn) {
            indicator.textContent = appState.sortOrder === "asc" ? "▲" : "▼";
            th.classList.add("sorted");
        } else {
            indicator.textContent = "";
            th.classList.remove("sorted");
        }
    });
}

function handleSort(column) {
    if (appState.sortColumn === column) {
        // Toggle sort order
        appState.sortOrder = appState.sortOrder === "asc" ? "desc" : "asc";
    } else {
        appState.sortColumn = column;
        appState.sortOrder = "desc"; // Default descending
    }
    
    applyFiltersAndRender();
}

// Client-Side CSV Export of currently filtered & sorted table
function exportFilteredToCSV() {
    if (appState.filteredData.length === 0) return;
    
    const csvContent = Papa.unparse(appState.filteredData);
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    
    const link = document.createElement("a");
    link.setAttribute("href", url);
    link.setAttribute("download", `canslim_screened_${appState.selectedDate}.csv`);
    link.style.visibility = "hidden";
    
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

function showError(msg) {
    errorMessage.textContent = msg;
    errorBanner.classList.remove("hidden");
}

function escapeHtml(str) {
    if (typeof str !== "string") return str;
    return str
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}
