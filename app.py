
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import httpx
import asyncio
import time

from scanner import get_contracts, scan_symbol
from daily_range_scanner import scan_daily_market

app = FastAPI(title="M-CORE Scanner")


@app.get("/", response_class=HTMLResponse)
async def dashboard():
    return HTML

@app.get("/api/daily-range")
async def api_daily_range():

    result = await scan_daily_market()

    return result

@app.get("/api/scan")
async def api_scan():

    semaphore = asyncio.Semaphore(5)

    async with httpx.AsyncClient(timeout=20) as client:

        symbols = await get_contracts(client)
        now_ms = int(time.time() * 1000)

        tasks = [
            scan_symbol(client, symbol, semaphore, now_ms)
            for symbol in symbols
        ]

        results = await asyncio.gather(*tasks)

    valid = [x for x in results if x is not None]

    valid.sort(
        key=lambda x: abs(x["change"]),
        reverse=True
    )

    return {
        "total_contracts": len(symbols),
        "scanned": len(valid),
        "failed": len(symbols) - len(valid),
        "results": valid
    }


HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">

<title>M-CORE Scanner</title>

<style>
* {
    box-sizing: border-box;
}

body {
    margin: 0;
    background: #0b0e14;
    color: #e5e7eb;
    font-family: Arial, sans-serif;
}

header {
    padding: 25px 35px;
    border-bottom: 1px solid #252a35;
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 15px;
}

.logo {
    font-size: 25px;
    font-weight: bold;
    letter-spacing: 2px;
}

.logo span {
    color: #22c55e;
}

.container {
    max-width: 1400px;
    margin: auto;
    padding: 30px;
}

.stats {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 15px;
    margin-bottom: 25px;
}

.stat {
    background: #151a23;
    border: 1px solid #252a35;
    padding: 20px;
    border-radius: 10px;
}

.stat small {
    color: #8993a4;
}

.stat h2 {
    margin-bottom: 0;
    font-size: 27px;
}

.controls {
    display: flex;
    gap: 12px;
    flex-wrap: wrap;
    margin-bottom: 20px;
}

input {
    background: #151a23;
    border: 1px solid #303746;
    color: white;
    padding: 12px;
    border-radius: 7px;
    min-width: 220px;
}

button {
    background: #16a34a;
    color: white;
    border: none;
    padding: 12px 22px;
    border-radius: 7px;
    cursor: pointer;
    font-weight: bold;
}

button:disabled {
    opacity: 0.5;
    cursor: wait;
}

.table-wrap {
    overflow-x: auto;
    background: #151a23;
    border: 1px solid #252a35;
    border-radius: 10px;
}

table {
    width: 100%;
    border-collapse: collapse;
    min-width: 650px;
}

th, td {
    padding: 15px;
    text-align: left;
    border-bottom: 1px solid #252a35;
}

th {
    color: #8993a4;
    font-size: 13px;
}

tr:hover {
    background: #1d2532;
}

.positive {
    color: #22c55e;
    font-weight: bold;
}

.negative {
    color: #ef4444;
    font-weight: bold;
}

.status {
    color: #8993a4;
    margin-bottom: 15px;
    font-size: 13px;
}

@media(max-width: 650px) {
    .container {
        padding: 15px;
    }

    header {
        padding: 20px;
    }

    .stats {
        grid-template-columns: 1fr;
    }
}
</style>
</head>

<body>

<header>
    <div class="logo">M-CORE <span>SCANNER</span></div>
    <div style="color:#8993a4">TOOBIT FUTURES | USDT</div>
</header>

<div class="container">

    <div class="stats">
        <div class="stat">
            <small>ACTIVE CONTRACTS</small>
            <h2 id="total">--</h2>
        </div>

        <div class="stat">
            <small>SUCCESSFULLY SCANNED</small>
            <h2 id="scanned">--</h2>
        </div>

        <div class="stat">
            <small>FAILED REQUESTS</small>
            <h2 id="failed">--</h2>
        </div>
    </div>

    <div class="controls">
        <button id="scanBtn" onclick="runScan()">
            SCAN MARKET
        </button>

        <input
            id="search"
            placeholder="Search symbol..."
            oninput="renderTable()"
        >
    </div>

    <div class="status" id="status">
        Ready to scan market.
    </div>

    <div class="table-wrap">
        <table>
            <thead>
                <tr>
                    <th>#</th>
                    <th>SYMBOL</th>
                    <th>15M CHANGE</th>
                    <th>PRICE</th>
                    <th>DIRECTION</th>
                </tr>
            </thead>

            <tbody id="tableBody">
                <tr>
                    <td colspan="5">
                        Click SCAN MARKET to start.
                    </td>
                </tr>
            </tbody>
        </table>
    </div>
        <div style="margin-top:45px;">

        <h2 style="color:#22c55e;">
            DAILY RANGE SCANNER
        </h2>

        <p style="color:#8993a4;">
            Price position relative to yesterday's high and low
        </p>

        <div class="stats">

            <div class="stat">
                <small>SCANNED</small>
                <h2 id="dailyScanned">--</h2>
            </div>

            <div class="stat">
                <small>FAILED</small>
                <h2 id="dailyFailed">--</h2>
            </div>

            <div class="stat">
                <small>MATCHED</small>
                <h2 id="dailyMatched">--</h2>
            </div>

        </div>

        <div class="controls">

            <button id="dailyScanBtn" onclick="runDailyScan()">
                SCAN DAILY RANGE
            </button>

            <input
                id="dailySearch"
                placeholder="Search symbol..."
                oninput="renderDailyTables()"
            >

        </div>

        <div class="status" id="dailyStatus">
            Ready to scan daily range.
        </div>

        <div id="dailyResults"></div>

    </div>

</div>

<script>

let marketData = [];

async function runScan() {

    const btn = document.getElementById("scanBtn");
    const status = document.getElementById("status");

    btn.disabled = true;
    btn.textContent = "SCANNING...";
    status.textContent = "Receiving market data...";

    try {

        const response = await fetch("/api/scan");

        if (!response.ok) {
            throw new Error("Server error: " + response.status);
        }

        const data = await response.json();

        marketData = data.results;

        document.getElementById("total").textContent =
            data.total_contracts;

        document.getElementById("scanned").textContent =
            data.scanned;

        document.getElementById("failed").textContent =
            data.failed;

        status.textContent =
            "Scan completed | " + new Date().toLocaleTimeString();

        renderTable();

    } catch (error) {

        status.textContent = "Error: " + error.message;

    } finally {

        btn.disabled = false;
        btn.textContent = "SCAN MARKET";

    }
}

function renderTable() {

    const search = document
        .getElementById("search")
        .value.toUpperCase();

    const filtered = marketData.filter(item =>
        item.symbol.includes(search)
    );

    const body = document.getElementById("tableBody");

    body.innerHTML = "";

    filtered.forEach((item, index) => {

        const positive = item.change >= 0;

        const row = document.createElement("tr");

        const values = [
            index + 1,
            item.symbol,
            (positive ? "+" : "") +
                item.change.toFixed(3) + "%",
            item.price,
            positive ? "BULLISH" : "BEARISH"
        ];

        values.forEach((value, i) => {

            const cell = document.createElement("td");
            cell.textContent = value;

            if (i === 2 || i === 4) {
                cell.className =
                    positive ? "positive" : "negative";
            }

            row.appendChild(cell);

        });

        body.appendChild(row);

    });

    if (filtered.length === 0) {
        body.innerHTML =
            '<tr><td colspan="5">No results found.</td></tr>';
    }
}
let dailyData = null;

function escapeHTML(value) {
    return String(value).replace(/[&<>"']/g, char => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;"
    })[char]);
}

async function runDailyScan() {

    const btn = document.getElementById("dailyScanBtn");
    const status = document.getElementById("dailyStatus");

    btn.disabled = true;
    btn.textContent = "SCANNING...";
    status.textContent = "Scanning daily candles...";

    try {

        const response = await fetch("/api/daily-range");

        if (!response.ok) {
            throw new Error("Server error: " + response.status);
        }

        dailyData = await response.json();

        document.getElementById("dailyScanned").textContent =
            dailyData.scanned;

        document.getElementById("dailyFailed").textContent =
            dailyData.failed;

        document.getElementById("dailyMatched").textContent =
            dailyData.matched;

        status.textContent =
            "Daily scan completed | " +
            new Date().toLocaleTimeString();

        renderDailyTables();

    } catch (error) {

        status.textContent = "Error: " + error.message;

    } finally {

        btn.disabled = false;
        btn.textContent = "SCAN DAILY RANGE";

    }
}

function renderDailyTables() {

    if (!dailyData) return;

    const search = document
        .getElementById("dailySearch")
        .value.toUpperCase();

    const sections = [
        {
            title: "NEAR YESTERDAY HIGH",
            key: "top",
            metric: "position",
            label: "POSITION"
        },
        {
            title: "NEAR YESTERDAY LOW",
            key: "bottom",
            metric: "position",
            label: "POSITION"
        },
        {
            title: "ABOVE YESTERDAY HIGH",
            key: "above_high",
            metric: "distance_from_high",
            label: "DISTANCE FROM HIGH"
        },
        {
            title: "BELOW YESTERDAY LOW",
            key: "below_low",
            metric: "distance_from_low",
            label: "DISTANCE FROM LOW"
        }
    ];

    const container = document.getElementById("dailyResults");

    container.innerHTML = "";

    sections.forEach(section => {

        const items = dailyData[section.key].filter(item =>
            item.symbol.toUpperCase().includes(search)
        );

        let html = `
            <div style="margin-top:30px;">
                <h3>${section.title} (${items.length})</h3>

                <div class="table-wrap">
                    <table>
                        <thead>
                            <tr>
                                <th>#</th>
                                <th>SYMBOL</th>
                                <th>PRICE</th>
                                <th>YESTERDAY HIGH</th>
                                <th>YESTERDAY LOW</th>
                                <th>${section.label}</th>
                            </tr>
                        </thead>
                        <tbody>
        `;

        if (items.length === 0) {

            html += `
                <tr>
                    <td colspan="6">No results found.</td>
                </tr>
            `;

        } else {

            items.forEach((item, index) => {

                const metric = Number(item[section.metric]);

                html += `
                    <tr>
                        <td>${index + 1}</td>
                        <td>${escapeHTML(item.symbol)}</td>
                        <td>${item.price}</td>
                        <td>${item.yesterday_high}</td>
                        <td>${item.yesterday_low}</td>
                        <td class="positive">${metric.toFixed(3)}%</td>
                    </tr>
                `;

            });

        }

        html += `
                        </tbody>
                    </table>
                </div>
            </div>
        `;

        container.insertAdjacentHTML("beforeend", html);

    });
}
</script>

</body>
</html>
"""
