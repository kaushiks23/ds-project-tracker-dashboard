from bs4 import BeautifulSoup
import requests
import csv
import pandas as pd
import os
from dotenv import load_dotenv
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.io as pio
from collections import Counter
import json

# ── Load environment variables ──────────────────────────────────────────────
load_dotenv()

API_KEY = os.getenv("CONFLUENCE_API_KEY")
BASE_URL = os.getenv("CONFLUENCE_BASE_URL")

if not API_KEY:
    raise ValueError("❌ CONFLUENCE_API_KEY not found! Check your .env file.")
if not BASE_URL:
    raise ValueError("❌ CONFLUENCE_BASE_URL not found! Check your .env file.")


# ── Function: Fetch page HTML from Confluence ────────────────────────────────
def fetch_confluence_page(url, api_key):
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    print(f"🔄 Fetching page: {url}")
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        print("✅ Page fetched successfully!")
        return response.text
    elif response.status_code == 401:
        raise ConnectionError("❌ Unauthorized! Check your API token.")
    elif response.status_code == 403:
        raise ConnectionError("❌ Forbidden! You may not have access to this page.")
    elif response.status_code == 404:
        raise ConnectionError("❌ Page not found! Check your Confluence URL.")
    else:
        raise ConnectionError(f"❌ Failed to fetch page. Status code: {response.status_code}")


# ── Function: Extract tables from HTML ──────────────────────────────────────
def extract_tables_from_html(html_content):
    soup = BeautifulSoup(html_content, 'lxml')
    tables = soup.find_all('table')
    if not tables:
        print("⚠️ No tables found on the page!")
        return []
    print(f"📊 Found {len(tables)} table(s) on the page.")
    extracted_tables = []
    for table in tables:
        table_data = []
        rows = table.find_all('tr')
        for row in rows:
            cells = row.find_all(['td', 'th'])
            row_data = [cell.get_text(strip=True) for cell in cells]
            if any(row_data):
                table_data.append(row_data)
        if table_data:
            extracted_tables.append(table_data)
    return extracted_tables


# ── Function: Save tables to CSV ─────────────────────────────────────────────
def save_tables_to_csv(tables, output_file):
    with open(output_file, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        for table in tables:
            writer.writerows(table)
    print(f"💾 Tables saved to: {output_file}")


# ── Function: Load and clean CSV into DataFrame ──────────────────────────────
def load_and_clean_csv(filepath):
    df = pd.read_csv(filepath, index_col=False)
    df.columns = ['Sno' if 'Unnamed' in col else col for col in df.columns]
    df.dropna(how='all', inplace=True)
    df = df.apply(lambda col: col.str.strip() if col.dtype == 'object' else col)
    print(f"📋 DataFrame loaded with shape: {df.shape}")
    print(df.head())
    return df


# ── CHANGE 1: Anonymisation Function ─────────────────────────────────────────
# Anonymises 'Data Scientist' and 'Client' columns immediately after data load.
# Uses deterministic alias mapping (sorted names → DS_001, Client_001, etc.)
# Consistent aliases across runs. No mapping file needed — generated dynamically.
# NOTE: Remove the call to this function when moving to EPAM's official GitHub org.
def anonymise_columns(df):
    """Anonymise 'Data Scientist' and 'Client' columns with deterministic aliases."""

    if "Data Scientist" in df.columns:
        unique_ds = sorted(df["Data Scientist"].dropna().unique())
        ds_map = {name: f"DS_{str(i+1).zfill(3)}" for i, name in enumerate(unique_ds)}
        df["Data Scientist"] = df["Data Scientist"].map(ds_map)
        print(f"🔒 Anonymised 'Data Scientist': {len(ds_map)} unique values mapped.")
    else:
        print("⚠️ 'Data Scientist' column not found — skipping.")

    if "Client" in df.columns:
        unique_clients = sorted(df["Client"].dropna().unique())
        client_map = {name: f"Client_{str(i+1).zfill(3)}" for i, name in enumerate(unique_clients)}
        df["Client"] = df["Client"].map(client_map)
        print(f"🔒 Anonymised 'Client': {len(client_map)} unique values mapped.")
    else:
        print("⚠️ 'Client' column not found — skipping.")

    if "Project Name" in df.columns:
        for real_name, alias in client_map.items():
            df["Project Name"] = df["Project Name"].str.replace(real_name, alias, case=False)

    return df


# ── Main Execution ────────────────────────────────────────────────────────────
if __name__ == "__main__":

    OUTPUT_CSV = "data_science_projects_latest.csv"

    # Step 1: Fetch the Confluence page
    html_content = fetch_confluence_page(BASE_URL, API_KEY)

    # Step 2: Extract tables from the HTML
    tables = extract_tables_from_html(html_content)

    if not tables:
        print("⚠️ No data to save. Exiting.")
    else:
        # Step 3: Save to CSV
        save_tables_to_csv(tables, OUTPUT_CSV)

        # Step 4: Load and clean into DataFrame
        df = load_and_clean_csv(OUTPUT_CSV)

        # ── CHANGE 1: Anonymise immediately after load — before any charts ───────
        # To disable for production (EPAM GitHub org), comment out the line below.
        df = anonymise_columns(df)
        print("✅ Anonymisation complete. Real names replaced with aliases.")

        print("\n✅ Scraping complete! Data is ready for visualisation.")
        print("\n🎨 Generating HTML Dashboard...")

        # ── Custom Colors ─────────────────────────────────────────────────────────
        custom_colors = ["#00F6FF", "#B896FF", "#7BA8FF", "#B3E1EA",
                         "#61E2BB", "#F7DB11", "#D1AAC2", "#FFA07A"]

        def get_colors(n):
            return (custom_colors * (n // len(custom_colors) + 1))[:n]

        # ── Chart 1: Count of Use Cases by Client ────────────────────────────────
        client_counts = df["Client"].value_counts().reset_index()
        client_counts.columns = ["Client", "Count"]
        fig_client_bar = px.bar(
    client_counts,
    x="Count",
    y="Client",
    orientation="h",
    title="Count of Use Cases by Client",
    color="Client",
    color_discrete_sequence=get_colors(len(client_counts)),
    text="Count"
)
        fig_client_bar.update_layout(
            showlegend=False,
            plot_bgcolor="white",
            paper_bgcolor="white",
            title_font=dict(size=16),
            yaxis=dict(autorange="reversed"),
            height=500,
            margin=dict(l=20, r=80, t=40, b=20),
            uniformtext=dict(mode="hide", minsize=8)
        )
        fig_client_bar.update_traces(textposition="auto", textfont=dict(size=11, color="black"))

        # ── Chart 2: Use Cases Distribution by Client (Donut) ────────────────────
        uc_counts = df["Client"].value_counts()
        top_clients = uc_counts.nlargest(10)
        others_count = uc_counts[10:].sum()
        final_counts = pd.concat([top_clients, pd.Series({"Others": others_count})])
        final_counts = final_counts[final_counts > 0]
        fig_client_donut = go.Figure(data=[go.Pie(labels=final_counts.index, values=final_counts.values,
                                                   hole=0.5, marker=dict(colors=get_colors(len(final_counts))),
                                                   textinfo="label+percent", hoverinfo="label+value+percent")])
        fig_client_donut.update_layout(title="Use Cases Distribution by Client (Top 10 + Others)",
                                       paper_bgcolor="white", title_font=dict(size=16), showlegend=True)

        # ── Chart 3: Project Status Donut ────────────────────────────────────────
        status_counts = df["Status"].value_counts()
        status_counts = status_counts[status_counts > 0]
        fig_status_donut = go.Figure(data=[go.Pie(labels=status_counts.index, values=status_counts.values,
                                                   hole=0.5, marker=dict(colors=get_colors(len(status_counts))),
                                                   textinfo="label+percent", hoverinfo="label+value+percent")])
        fig_status_donut.update_layout(title="DS Project Status Distribution",
                                       paper_bgcolor="white", title_font=dict(size=16), showlegend=True)

        # ── Chart 4: Top 15 Core Technologies (Bar) ──────────────────────────────
        exclude_words_tech = {"GCP", "Azure", "AWS", "Databricks"}
        df["Core Technology"] = df["Core Technology"].fillna("")
        tech_list = []
        for row in df["Core Technology"]:
            words = [w.strip() for w in row.split(",") if w.strip() and w.strip() not in exclude_words_tech]
            tech_list.extend(words)
        tech_counts = Counter(tech_list)
        df_tech = pd.DataFrame(tech_counts.items(), columns=["Technology", "Count"])
        df_tech = df_tech.sort_values("Count", ascending=False).head(15)
        fig_tech_bar = px.bar(
    df_tech,
    x="Count",
    y="Technology",
    orientation="h",
    title="Top 15 Core Technologies Used",
    color="Technology",
    color_discrete_sequence=get_colors(len(df_tech)),
    text="Count"
)
        fig_tech_bar.update_layout(
            showlegend=False,
            plot_bgcolor="white",
            paper_bgcolor="white",
            title_font=dict(size=16),
            yaxis=dict(autorange="reversed"),
            height=500,
            margin=dict(l=20, r=80, t=40, b=20),
            uniformtext=dict(mode="hide", minsize=8)
        )
        fig_tech_bar.update_traces(textposition="auto", textfont=dict(size=11, color="black"))

        # ── Chart 5: Top Core Technologies Donut ─────────────────────────────────
        df_tech_all = pd.DataFrame(tech_counts.items(), columns=["Core Technology", "Count"])
        df_tech_all = df_tech_all.sort_values("Count", ascending=False)
        top_20 = df_tech_all.head(20)
        others_tech = df_tech_all.iloc[20:]["Count"].sum()
        df_tech_donut = pd.concat([top_20, pd.DataFrame([{"Core Technology": "Others", "Count": others_tech}])],
                                   ignore_index=True)
        df_tech_donut = df_tech_donut[df_tech_donut["Count"] > 0]
        fig_tech_donut = go.Figure(data=[go.Pie(labels=df_tech_donut["Core Technology"],
                                                 values=df_tech_donut["Count"], hole=0.5,
                                                 marker=dict(colors=get_colors(len(df_tech_donut))),
                                                 textinfo="label+percent", hoverinfo="label+value+percent")])
        fig_tech_donut.update_layout(title="Top Core Technologies Distribution",
                                     paper_bgcolor="white", title_font=dict(size=16), showlegend=True)

        # ── Chart 6: Top 15 Business Domains (Bar) ───────────────────────────────
        domain_col = "BusinessDomain" if "BusinessDomain" in df.columns else None
        if domain_col:
            df[domain_col] = df[domain_col].fillna("")
            domain_list = []
            for row in df[domain_col]:
                words = [w.strip().lower() for w in row.split(",") if w.strip()]
                domain_list.extend(words)
            domain_counts = Counter(domain_list)
            df_domain = pd.DataFrame(domain_counts.items(), columns=["Business Domain", "Count"])
            df_domain["Business Domain"] = df_domain["Business Domain"].str.title()
            df_domain = df_domain.sort_values("Count", ascending=False).head(15)
            fig_domain_bar = px.bar(
    df_domain,
    x="Count",
    y="Business Domain",
    orientation="h",
    title="Top 15 Business Domains",
    color="Business Domain",
    color_discrete_sequence=get_colors(len(df_domain)),
    text="Count"
)
            fig_domain_bar.update_layout(
                showlegend=False,
                plot_bgcolor="white",
                paper_bgcolor="white",
                title_font=dict(size=16),
                yaxis=dict(autorange="reversed"),
                height=500,
                margin=dict(l=20, r=80, t=40, b=20),
                uniformtext=dict(mode="hide", minsize=8)
            )
            fig_domain_bar.update_traces(textposition="auto", textfont=dict(size=11, color="black"))
        else:
            fig_domain_bar = go.Figure()
            fig_domain_bar.update_layout(title="Business Domain column not found")

        # ── Chart 7: Stacked Bar - Client vs Status ───────────────────────────────
        stacked_data = pd.crosstab(df["Client"], df["Status"])
        stacked_data["Total"] = stacked_data.sum(axis=1)
        stacked_data = stacked_data[stacked_data["Total"] > 0].sort_values("Total", ascending=False).drop(columns=["Total"])
        fig_stacked = go.Figure()
        for i, status_col in enumerate(stacked_data.columns):
            fig_stacked.add_trace(go.Bar(name=status_col, x=stacked_data.index, y=stacked_data[status_col],
                                         marker_color=custom_colors[i % len(custom_colors)],
                                         text=stacked_data[status_col].apply(lambda v: str(int(v)) if v > 0 else ""),
                                         textposition="inside"))
        fig_stacked.update_layout(barmode="stack", title="Client vs Project Status (Stacked)",
                                  xaxis_title="Client", yaxis_title="Number of Use Cases",
                                  plot_bgcolor="white", paper_bgcolor="white", title_font=dict(size=16),
                                  xaxis=dict(tickangle=-45), legend_title="Status")

        # ── Chart 8: Algorithms Sunburst ──────────────────────────────────────────
        algo_col = "Algorithms" if "Algorithms" in df.columns else None
        if algo_col:
            df[algo_col] = df[algo_col].fillna("")
            df_split = df[algo_col].str.split(",", expand=True).iloc[:, :2]
            df_split.columns = ["Level 1", "Level 2"]
            df_split["Level 1"] = df_split["Level 1"].str.strip()
            df_split["Level 2"] = df_split["Level 2"].str.strip().fillna("")
            df_final_sun = pd.concat([df, df_split], axis=1)
            df_final_sun = df_final_sun[df_final_sun["Level 1"].notna() & (df_final_sun["Level 1"] != "")]
            for col in df_final_sun.columns:
                if df_final_sun[col].dtype == object:
                    df_final_sun[col] = df_final_sun[col].fillna("")
                else:
                    df_final_sun[col] = df_final_sun[col].fillna(0)
            df_sun_counts = df_final_sun.groupby(["Level 1", "Level 2"]).size().reset_index(name="Count")
            fig_sunburst = px.sunburst(df_sun_counts, path=["Level 1", "Level 2"], values="Count",
                                       title="Hierarchical Algorithm Segments", color="Level 1",
                                       color_discrete_sequence=custom_colors)
            fig_sunburst.update_layout(paper_bgcolor="white", title_font=dict(size=16), width=700, height=700)
        else:
            fig_sunburst = go.Figure()
            fig_sunburst.update_layout(title="Algorithms column not found")

        # ── Convert all charts to HTML divs ──────────────────────────────────────
        def fig_to_html(fig):
            return pio.to_html(fig, full_html=False, include_plotlyjs=False)

        chart_client_bar   = fig_to_html(fig_client_bar)
        chart_client_donut = fig_to_html(fig_client_donut)
        chart_status_donut = fig_to_html(fig_status_donut)
        chart_tech_bar     = fig_to_html(fig_tech_bar)
        chart_tech_donut   = fig_to_html(fig_tech_donut)
        chart_domain_bar   = fig_to_html(fig_domain_bar)
        chart_stacked      = fig_to_html(fig_stacked)
        chart_sunburst     = fig_to_html(fig_sunburst)

        # ── Prepare table data ────────────────────────────────────────────────────
        table_columns = df.columns.tolist()
        table_data    = df.fillna("").values.tolist()

        # ── Get unique filter values ──────────────────────────────────────────────
        status_options = sorted(df["Status"].dropna().unique().tolist())
        client_options = sorted(df["Client"].dropna().unique().tolist())
        domain_options = sorted(df["BusinessDomain"].dropna().unique().tolist()) if "BusinessDomain" in df.columns else []

        # ── CHANGE 2: Data Scientist filter options ───────────────────────────────
        ds_options = sorted(df["Data Scientist"].dropna().unique().tolist()) if "Data Scientist" in df.columns else []

        # ── Build the HTML Dashboard ──────────────────────────────────────────────
        html_content = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8" />
            <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
            <title>Data Science Projects Dashboard</title>
            <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
            <style>
                * {{ box-sizing: border-box; margin: 0; padding: 0; }}
                body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f0f2f5; color: #333; }}
                header {{ background: linear-gradient(135deg, #1a1a2e, #16213e); color: white; padding: 24px 40px; display: flex; align-items: center; justify-content: space-between; }}
                header h1 {{ font-size: 24px; font-weight: 700; letter-spacing: 1px; }}
                header span {{ font-size: 13px; opacity: 0.7; }}
                .filter-bar {{ background: white; padding: 16px 40px; display: flex; gap: 20px; flex-wrap: wrap; align-items: center; border-bottom: 1px solid #ddd; box-shadow: 0 2px 6px rgba(0,0,0,0.05); }}
                .filter-bar label {{ font-size: 13px; font-weight: 600; color: #555; }}
                .filter-bar select {{ padding: 7px 12px; border-radius: 6px; border: 1px solid #ccc; font-size: 13px; background: #fafafa; cursor: pointer; min-width: 160px; }}
                .filter-bar button {{ padding: 7px 18px; background: #1a1a2e; color: white; border: none; border-radius: 6px; font-size: 13px; cursor: pointer; transition: background 0.2s; }}
                .filter-bar button:hover {{ background: #00F6FF; color: #1a1a2e; }}
                .kpi-row {{ display: flex; gap: 20px; padding: 24px 40px 0 40px; flex-wrap: wrap; }}
                .kpi-card {{ background: white; border-radius: 12px; padding: 20px 28px; flex: 1; min-width: 160px; box-shadow: 0 2px 10px rgba(0,0,0,0.07); border-left: 5px solid #00F6FF; text-align: center; }}
                .kpi-card h3 {{ font-size: 32px; font-weight: 700; color: #1a1a2e; }}
                .kpi-card p {{ font-size: 13px; color: #777; margin-top: 4px; }}
                .charts-grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 24px; padding: 24px 40px; }}
                .chart-card {{ background: white; border-radius: 12px; padding: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.07); }}
                .chart-card.full-width {{ grid-column: span 2; }}
                .section-title {{ font-size: 18px; font-weight: 700; padding: 10px 40px 0 40px; color: #1a1a2e; }}
                .table-section {{ padding: 10px 40px 40px 40px; }}
                .table-wrapper {{ overflow-x: auto; border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.07); background: white; }}
                table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
                thead tr {{ background: #1a1a2e; color: white; }}
                thead th {{ padding: 12px 14px; text-align: left; white-space: nowrap; }}
                tbody tr:nth-child(even) {{ background: #f7f9fc; }}
                tbody tr:hover {{ background: #e8f4ff; }}
                tbody td {{ padding: 10px 14px; border-bottom: 1px solid #eee; white-space: nowrap; max-width: 200px; overflow: hidden; text-overflow: ellipsis; }}
                footer {{ text-align: center; padding: 20px; font-size: 12px; color: #aaa; background: white; border-top: 1px solid #eee; }}
            </style>
        </head>
        <body>

        <header>
            <h1>📊 Data Science Projects Dashboard</h1>
            <span id="last-updated">Last Updated: Auto-generated</span>
        </header>

        <!-- ── CHANGE 2: Filter Bar with Data Scientist dropdown added ─────────── -->
        <div class="filter-bar">
            <label>Filter by Status:</label>
            <select id="filter-status" onchange="applyFilters()">
                <option value="All">All</option>
                {"".join(f'<option value="{s}">{s}</option>' for s in status_options)}
            </select>

            <label>Filter by Client:</label>
            <select id="filter-client" onchange="applyFilters()">
                <option value="All">All</option>
                {"".join(f'<option value="{c}">{c}</option>' for c in client_options)}
            </select>

            <label>Filter by Data Scientist:</label>
            <select id="filter-ds" onchange="applyFilters()">
                <option value="All">All</option>
                {"".join(f'<option value="{ds}">{ds}</option>' for ds in ds_options)}
            </select>

            <label>Filter by Domain:</label>
            <select id="filter-domain" onchange="applyFilters()">
                <option value="All">All</option>
                {"".join(f'<option value="{d}">{d}</option>' for d in domain_options)}
            </select>

            <button onclick="resetFilters()">Reset Filters</button>
        </div>

        <div class="kpi-row">
            <div class="kpi-card">
                <h3 id="kpi-total">{len(df)}</h3>
                <p>Total Projects</p>
            </div>
            <div class="kpi-card" style="border-left-color:#B896FF;">
                <h3 id="kpi-clients">{df['Client'].nunique()}</h3>
                <p>Unique Clients</p>
            </div>
            <div class="kpi-card" style="border-left-color:#61E2BB;">
                <h3 id="kpi-active">{df[df['Status'].str.contains('Active|active|ongoing|Ongoing', na=False)].shape[0]}</h3>
                <p>Active Projects</p>
            </div>
            <div class="kpi-card" style="border-left-color:#F7DB11;">
                <h3 id="kpi-completed">{df[df['Status'].str.contains('Completed|completed|Done|done', na=False)].shape[0]}</h3>
                <p>Completed Projects</p>
            </div>
            <div class="kpi-card" style="border-left-color:#FFA07A;">
                <h3 id="kpi-domains">{df['BusinessDomain'].nunique() if 'BusinessDomain' in df.columns else 'N/A'}</h3>
                <p>Business Domains</p>
            </div>
        </div>

        <div class="charts-grid">
            <div class="chart-card">{chart_client_bar}</div>
            <div class="chart-card">{chart_client_donut}</div>
            <div class="chart-card">{chart_status_donut}</div>
            <div class="chart-card">{chart_stacked}</div>
            <div class="chart-card">{chart_tech_bar}</div>
            <div class="chart-card">{chart_tech_donut}</div>
            <div class="chart-card">{chart_domain_bar}</div>
            <div class="chart-card">{chart_sunburst}</div>
        </div>

        <p class="section-title">📋 Project Data Table</p>
        <div class="table-section">
            <div class="table-wrapper">
                <table id="project-table">
                    <thead>
                        <tr>{"".join(f"<th>{col}</th>" for col in table_columns)}</tr>
                    </thead>
                    <tbody id="table-body">
                        {"".join("<tr>" + "".join(f"<td title='{str(cell)}'>{str(cell)}</td>" for cell in row) + "</tr>" for row in table_data)}
                    </tbody>
                </table>
            </div>
        </div>

        <footer>Auto-generated Dashboard | Data Science Projects Tracker</footer>

        <!-- ── CHANGE 2: Updated JS with dsIdx + applyFilters + resetFilters ───── -->
        <script>
            const allData = {json.dumps(table_data)};
            const columns = {json.dumps(table_columns)};

            const statusIdx = columns.indexOf("Status");
            const clientIdx = columns.indexOf("Client");
            const domainIdx = columns.indexOf("BusinessDomain");
            const dsIdx     = columns.indexOf("Data Scientist");  // ── CHANGE 2

            function applyFilters() {{
                const statusVal = document.getElementById("filter-status").value;
                const clientVal = document.getElementById("filter-client").value;
                const dsVal     = document.getElementById("filter-ds").value;  // ── CHANGE 2
                const domainVal = document.getElementById("filter-domain").value;

                const filtered = allData.filter(row => {{
                    const matchStatus = statusVal === "All" || row[statusIdx] === statusVal;
                    const matchClient = clientVal === "All" || row[clientIdx] === clientVal;
                    const matchDS     = dsVal === "All" || (dsIdx >= 0 && row[dsIdx] === dsVal);  // ── CHANGE 2
                    const matchDomain = domainVal === "All" || (domainIdx >= 0 && row[domainIdx] === domainVal);
                    return matchStatus && matchClient && matchDS && matchDomain;
                }});

                const tbody = document.getElementById("table-body");
                tbody.innerHTML = filtered.map(row =>
                    "<tr>" + row.map(cell => `<td title="${{cell}}">${{cell}}</td>`).join("") + "</tr>"
                ).join("");

                document.getElementById("kpi-total").innerText = filtered.length;
                const uniqueClients = new Set(filtered.map(r => r[clientIdx])).size;
                document.getElementById("kpi-clients").innerText = uniqueClients;
            }}

            function resetFilters() {{
                document.getElementById("filter-status").value = "All";
                document.getElementById("filter-client").value = "All";
                document.getElementById("filter-ds").value = "All";  // ── CHANGE 2
                document.getElementById("filter-domain").value = "All";
                applyFilters();
            }}

            document.getElementById("last-updated").innerText =
                "Last Updated: " + new Date().toLocaleString();
        </script>

        </body>
        </html>
        """

        output_html = "dashboard.html"
        with open(output_html, "w", encoding="utf-8") as f:
            f.write(html_content)

        print(f"✅ Dashboard saved to: {output_html}")
        print("🌐 Open dashboard.html in your browser to view it!")
