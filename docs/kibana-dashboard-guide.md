# Kibana CMS Analytics Dashboard — Step-by-Step Build Guide

This guide walks you through building a complete analytics dashboard in Kibana
using the four Elasticsearch indices from this CMS AI Search platform.

## Prerequisites

- Access to your Elastic Cloud deployment (Kibana URL)
- The four indices populated with data:
  - `cms-content` (~2,200 docs)
  - `cms-search-logs` (~10,000 docs)
  - `cms-click-logs` (~5,000 docs)
  - `cms-content-views` (~8,000 docs)
- If you haven't generated analytics data yet, run:
  ```bash
  cd backend
  python -m scripts.generate_analytics
  ```

---

## Step 1 — Create Data Views

Data Views (formerly Index Patterns) tell Kibana how to read each index.

1. Open Kibana → **Stack Management** (left sidebar, bottom) → **Data Views**
2. Click **Create data view** and create these four:

| Name | Index pattern | Timestamp field |
|------|--------------|-----------------|
| `CMS Content` | `cms-content` | `created_at` |
| `CMS Search Logs` | `cms-search-logs` | `timestamp` |
| `CMS Click Logs` | `cms-click-logs` | `timestamp` |
| `CMS Content Views` | `cms-content-views` | `timestamp` |

For each one:
- Type the index pattern in the **Index pattern** field
- Select the timestamp field from the dropdown
- Click **Save data view to Kibana**

> **Verify**: After creating each data view, click on it and confirm
> you see all the expected fields listed (keyword, integer, date, etc.).

---

## Step 2 — Create the Dashboard

1. Go to **Dashboard** (left sidebar) → **Create dashboard**
2. Click the **pencil icon** (edit) in the top bar
3. Click **Save** → name it **"CMS AI Search — Analytics Dashboard"**
4. Keep it open — we'll add panels one by one below

---

## Step 3 — KPI Metric Panels (Top Row)

We'll create 6 metric panels for the header. For each one:
**Click "Create visualization"** in the dashboard editor.

### 3.1 — Total Assets

1. Select visualization type: **Metric**
2. Data view: **CMS Content**
3. In the metric config:
   - Primary metric → **Count**
4. Title: `Total Assets`
5. Click **Save and return**

### 3.2 — Total Searches

1. **Create visualization** → **Metric**
2. Data view: **CMS Search Logs**
3. Primary metric → **Count**
4. Title: `Total Searches`
5. **Save and return**

### 3.3 — Search Hit Rate %

1. **Create visualization** → **Metric**
2. Data view: **CMS Search Logs**
3. Click **Lens** editor (if not already)
4. Switch to **Formula** mode in the metric config
5. Enter this formula:
   ```
   ((count() - count(kql='result_count: 0')) / count()) * 100
   ```
6. Format: **Number** → suffix `%`, decimals: `1`
7. Title: `Search Hit Rate`
8. **Save and return**

### 3.4 — Avg Response Time (ms)

1. **Create visualization** → **Metric**
2. Data view: **CMS Search Logs**
3. Primary metric → **Average** of `response_time_ms`
4. Format: **Number** → suffix ` ms`, decimals: `0`
5. Title: `Avg Response Time`
6. **Save and return**

### 3.5 — Total Content Views

1. **Create visualization** → **Metric**
2. Data view: **CMS Content Views**
3. Primary metric → **Count**
4. Title: `Total Content Views`
5. **Save and return**

### 3.6 — Unique Users

1. **Create visualization** → **Metric**
2. Data view: **CMS Search Logs**
3. Primary metric → **Unique count** of `user_id`
4. Title: `Unique Users`
5. **Save and return**

> **Layout**: Drag all 6 metrics into a single row at the top of the dashboard.
> Resize each to roughly equal width (1/6 of the dashboard width).

---

## Step 4 — Search Performance Panels

### 4.1 — Search Volume by Type Over Time (Line Chart)

This shows how many searches happen daily, split by hybrid/keyword/image.

1. **Create visualization** → choose **Line** (Lens)
2. Data view: **CMS Search Logs**
3. Configure:
   - **Horizontal axis**: `timestamp` → Date histogram → interval: `Auto` (or `1d`)
   - **Vertical axis**: Count
   - **Break down by**: Top values of `search_type` (top 5)
4. Title: `Search Volume by Type`
5. **Save and return**

### 4.2 — Search Hit Rate Over Time (Dual Axis Line)

1. **Create visualization** → **Line** (Lens)
2. Data view: **CMS Search Logs**
3. Configure the **left axis** (line 1):
   - Metric: **Count** (label it "Total Searches")
4. Add a second metric for the **right axis** (line 2):
   - Click **+** to add a metric
   - Choose **Formula**:
     ```
     ((count() - count(kql='result_count: 0')) / count()) * 100
     ```
   - Label: "Hit Rate %"
   - Assign to **Right axis**
5. **Horizontal axis**: `timestamp` → Date histogram
6. Add a **Reference line** on the right axis at value `85` (your target)
7. Title: `Search Hit Rate Over Time`
8. **Save and return**

### 4.3 — Response Time Percentiles (Area Chart)

Shows p50, p90, p95 latency trends — critical for monitoring search SLAs.

1. **Create visualization** → **Area** (Lens)
2. Data view: **CMS Search Logs**
3. Add 3 metrics using **Percentile** of `response_time_ms`:
   - Metric 1: Percentile `50` → label `p50 (Median)`
   - Metric 2: Percentile `90` → label `p90`
   - Metric 3: Percentile `95` → label `p95`
4. **Horizontal axis**: `timestamp` → Date histogram
5. Add a **Reference line** at `500` (ms) → label `SLA Target`
6. Title: `Response Time Percentiles`
7. **Save and return**

### 4.4 — Search Type Distribution (Donut)

1. **Create visualization** → **Donut** (Lens)
2. Data view: **CMS Search Logs**
3. **Slice by**: Top values of `search_type`
4. **Size by**: Count
5. Title: `Search Type Distribution`
6. **Save and return**

### 4.5 — Filter Usage (Horizontal Bar)

Shows which filters users apply when searching.

1. **Create visualization** → **Bar horizontal** (Lens)
2. Data view: **CMS Search Logs**
3. **Vertical axis**: Top values of `filters_used` (top 10)
4. **Horizontal axis**: Count
5. Title: `Filter Usage`
6. **Save and return**

---

## Step 5 — Query Intelligence Panels

### 5.1 — Top Searched Queries (Tag Cloud)

1. **Create visualization** → **Tag cloud** (Aggregation based)
   - Note: Tag cloud is under **Aggregation based** → **Tag cloud**, not Lens
2. Data view: **CMS Search Logs**
3. **Tag size**: Count
4. **Buckets** → Add → **Tags**: Terms aggregation on `query_text.raw`, size `50`
5. Click **Update**
6. Title: `Top Searched Queries`
7. **Save and return**

### 5.2 — Top Searched Queries (Data Table — detailed view)

1. **Create visualization** → **Table** (Lens)
2. Data view: **CMS Search Logs**
3. **Rows**: Top values of `query_text.raw` (top 20)
4. **Metrics** (columns):
   - Count → label `Search Count`
   - Average of `result_count` → label `Avg Results`
   - Average of `response_time_ms` → label `Avg Latency (ms)`
5. **Sort** by `Search Count` descending
6. Title: `Top Queries — Detailed`
7. **Save and return**

### 5.3 — Zero-Result Queries (Table)

These are your content gap opportunities — queries users searched for but got nothing.

1. **Create visualization** → **Table** (Lens)
2. Data view: **CMS Search Logs**
3. First, add a **filter** (click the filter bar at the top):
   - Field: `result_count`, Operator: `is`, Value: `0`
4. **Rows**: Top values of `query_text.raw` (top 30)
5. **Metrics**:
   - Count → label `Times Searched`
   - Max of `timestamp` → label `Last Seen`
6. Sort by `Times Searched` descending
7. Title: `Zero-Result Queries (Content Gaps)`
8. **Save and return**

### 5.4 — Click Position Distribution (Bar Chart)

Reveals if your ranking is effective (most clicks should be positions 1–3).

1. **Create visualization** → **Bar vertical** (Lens)
2. Data view: **CMS Click Logs**
3. **Horizontal axis**: `position` → use **Intervals** (histogram) with interval `1`
   - Alternative: Top values of `position` if histogram is tricky
4. **Vertical axis**: Count
5. **Break down by**: Top values of `search_type`
6. Title: `Click Position Distribution`
7. **Save and return**

### 5.5 — Mean Reciprocal Rank by Search Type (Line Chart)

MRR = average of (1/position). The closer to 1.0, the better your ranking.

1. **Create visualization** → **Line** (Lens)
2. Data view: **CMS Click Logs**
3. Metric: **Formula**:
   ```
   1 / average(position)
   ```
   > Note: This is an approximation. True MRR would need a scripted field,
   > but this gives you directional value.
4. **Horizontal axis**: `timestamp` → Date histogram (interval: `1w`)
5. **Break down by**: Top values of `search_type`
6. Title: `Mean Reciprocal Rank (approx) by Search Type`
7. **Save and return**

---

## Step 6 — Content & Engagement Panels

### 6.1 — Most Viewed Content (Data Table)

1. **Create visualization** → **Table** (Lens)
2. Data view: **CMS Content**
3. **Rows**: Top values of `title.raw` (top 20)
4. **Metrics**:
   - Max of `view_count` → label `Views`
   - Max of `download_count` → label `Downloads`
5. Sort by `Views` descending
6. Enable **Color by value** on the Views column (Lens → click column → Color)
7. Title: `Most Viewed Content`
8. **Save and return**

### 6.2 — Content Type Breakdown (Treemap)

1. **Create visualization** → **Treemap** (Lens)
2. Data view: **CMS Content**
3. **Group by**: Top values of `content_type`
4. **Size by**: Count
5. Title: `Content by Type`
6. **Save and return**

### 6.3 — Content by Source (Horizontal Bar)

Shows distribution across Unsplash, Pexels, Wikipedia, arXiv, etc.

1. **Create visualization** → **Bar horizontal** (Lens)
2. Data view: **CMS Content**
3. **Vertical axis**: Top values of `source` (top 10)
4. **Horizontal axis**: Count
5. Title: `Content by Source`
6. **Save and return**

### 6.4 — Views by Referrer Source Over Time (Stacked Area)

Shows how users reach content: search vs recommendation vs direct vs external.

1. **Create visualization** → **Area** (Lens) → set to **Stacked**
2. Data view: **CMS Content Views**
3. **Horizontal axis**: `timestamp` → Date histogram (interval: `1w`)
4. **Vertical axis**: Count
5. **Break down by**: Top values of `referrer`
6. Title: `Views by Referrer Source`
7. **Save and return**

### 6.5 — Engagement by Category (Heatmap)

1. **Create visualization** → **Heatmap** (Lens)
2. Data view: **CMS Content Views**
3. **Horizontal axis**: `timestamp` → Date histogram (interval: `1w`)
4. **Vertical axis**: Top values of `category` (top 15)
5. **Cell value**: Count
6. Title: `Engagement Heatmap by Category`
7. **Save and return**

### 6.6 — Time Spent on Content by Type (Bar)

1. **Create visualization** → **Bar vertical** (Lens)
2. Data view: **CMS Content Views**
3. **Horizontal axis**: Top values of `content_type`
4. **Vertical axis**: Average of `time_spent_seconds`
5. Title: `Avg Time Spent by Content Type`
6. **Save and return**

---

## Step 7 — Geographic Analytics Panels

### 7.1 — Search Activity World Map

1. **Create visualization** → **Maps** (from the left sidebar → Maps, or add Maps panel)
2. Click **Add layer** → **Documents**
3. Data view: **CMS Search Logs**
4. Geospatial field: `geo`
5. **Scaling**: choose **Clusters** (for better performance)
6. **Tooltip fields**: add `query_text`, `search_type`, `region`
7. Style: size by count (larger circles = more searches)
8. Title: `Search Activity Map`
9. **Save and return** to dashboard

### 7.2 — Regional Search Distribution (Horizontal Bar)

1. **Create visualization** → **Bar horizontal** (Lens)
2. Data view: **CMS Search Logs**
3. **Vertical axis**: Top values of `region` (top 10)
4. **Horizontal axis**: Count
5. Sort: descending by count
6. Title: `Searches by Region`
7. **Save and return**

### 7.3 — Top Queries per Region (Table)

1. **Create visualization** → **Table** (Lens)
2. Data view: **CMS Search Logs**
3. **Rows**:
   - First: Top values of `region` (top 7)
   - Then click **+** to add sub-bucket: Top values of `query_text.raw` (top 5)
4. **Metrics**: Count → label `Search Count`
5. Title: `Top Queries by Region`
6. **Save and return**

### 7.4 — Content Views by Region (Donut)

1. **Create visualization** → **Donut** (Lens)
2. Data view: **CMS Content Views**
3. **Slice by**: Top values of `region`
4. **Size by**: Count
5. Title: `Content Views by Region`
6. **Save and return**

---

## Step 8 — AI Search Quality Panels

### 8.1 — Hybrid vs Keyword Hit Rate (Side-by-Side Metrics)

Create two separate metric panels:

**Panel A — Hybrid Hit Rate:**
1. **Create visualization** → **Metric** (Lens)
2. Data view: **CMS Search Logs**
3. Add a **filter**: `search_type: hybrid`
4. Metric: **Formula**:
   ```
   ((count() - count(kql='result_count: 0')) / count()) * 100
   ```
5. Format: suffix `%`, decimals `1`
6. Title: `Hybrid Search Hit Rate`
7. **Save and return**

**Panel B — Keyword Hit Rate:**
1. Same as above but filter: `search_type: keyword`
2. Title: `Keyword Search Hit Rate`
3. **Save and return**

> Place these side by side to visually compare semantic vs traditional search.

### 8.2 — Response Time: Hybrid vs Keyword (Bar)

1. **Create visualization** → **Bar vertical** (Lens)
2. Data view: **CMS Search Logs**
3. **Horizontal axis**: Top values of `search_type`
4. Add 3 metrics:
   - Percentile of `response_time_ms` → percentile `50` → label `p50`
   - Percentile of `response_time_ms` → percentile `90` → label `p90`
   - Percentile of `response_time_ms` → percentile `95` → label `p95`
5. Title: `Response Time by Search Type`
6. **Save and return**

### 8.3 — Image Search Adoption Trend (Line)

1. **Create visualization** → **Line** (Lens)
2. Data view: **CMS Search Logs**
3. Add a **filter**: `search_type: image`
4. **Horizontal axis**: `timestamp` → Date histogram (interval: `1w`)
5. **Vertical axis**: Count
6. Title: `Image Search Usage Over Time`
7. **Save and return**

---

## Step 9 — Arrange the Dashboard Layout

Now arrange all panels into a logical layout. Click **Edit** on the dashboard.

Suggested layout (top to bottom):

```
┌─────────────────────────────────────────────────────────────┐
│  Row 1: KPI Metrics (6 small panels, equal width)           │
│  [Total Assets] [Total Searches] [Hit Rate %]               │
│  [Avg Response] [Total Views]    [Unique Users]              │
├──────────────────────────┬──────────────────────────────────┤
│  Row 2 Left:             │  Row 2 Right:                    │
│  Search Volume by Type   │  Search Hit Rate Over Time       │
│  (line chart)            │  (dual-axis line)                │
├──────────────────────────┼──────────────────────────────────┤
│  Row 3 Left:             │  Row 3 Right:                    │
│  Response Time Pctiles   │  Search Type Distribution        │
│  (area chart)            │  (donut)                         │
├──────────────────────────┼──────────────────────────────────┤
│  Row 4 Left:             │  Row 4 Right:                    │
│  Top Searched Queries    │  Zero-Result Queries             │
│  (tag cloud)             │  (table)                         │
├──────────────────────────┼──────────────────────────────────┤
│  Row 5 Left:             │  Row 5 Right:                    │
│  Click Position Distrib. │  MRR by Search Type              │
│  (bar)                   │  (line)                          │
├──────────────────────────┼──────────────────────────────────┤
│  Row 6 Left:             │  Row 6 Right:                    │
│  Most Viewed Content     │  Content Type Breakdown          │
│  (table)                 │  (treemap)                       │
├──────────────────────────┼──────────────────────────────────┤
│  Row 7 Left:             │  Row 7 Right:                    │
│  Views by Referrer       │  Engagement Heatmap              │
│  (stacked area)          │  (heatmap)                       │
├──────────────────────────┼──────────────────────────────────┤
│  Row 8 Left:             │  Row 8 Right:                    │
│  Search Activity Map     │  Top Queries by Region           │
│  (map)                   │  (table)                         │
├──────────────────────────┼──────────────────────────────────┤
│  Row 9: AI Search Quality                                   │
│  [Hybrid Hit Rate] [Keyword Hit Rate] [Resp Time by Type]   │
│  [Image Search Adoption Trend]                              │
└─────────────────────────────────────────────────────────────┘
```

Tips for arranging:
- **Drag panels** by their title bar to reposition
- **Resize** by dragging the bottom-right corner
- Keep KPI metrics at **height ~100px**; charts at **~300px**
- Give tables and maps more vertical space (~400px)

---

## Step 10 — Add Dashboard Filters & Controls

1. While in **Edit** mode, click **Controls** in the top toolbar
2. Add these filter controls:

| Control type | Field | Data view |
|-------------|-------|-----------|
| Options list | `search_type` | CMS Search Logs |
| Options list | `content_type` | CMS Content Views |
| Options list | `category` | CMS Content Views |
| Options list | `region` | CMS Search Logs |
| Range slider | `response_time_ms` | CMS Search Logs |

3. Click **Save**

These controls let anyone interactively filter the entire dashboard.

> Also set the **time picker** (top-right) to `Last 90 days` to match
> the synthetic data range.

---

## Step 11 — Set Up Alerts (Optional but Recommended)

### 11.1 — Zero-Result Rate Spike Alert

1. Go to **Stack Management** → **Rules** → **Create rule**
2. Rule type: **Elasticsearch query**
3. Index: `cms-search-logs`
4. Condition: query matches docs where `result_count = 0`
5. Threshold: count > `300` in `24 hours`
   (baseline is ~15% of ~110/day = ~16, so 300 means a spike)
6. Action: email / Slack / webhook
7. Name: `High Zero-Result Rate Alert`

### 11.2 — Latency Degradation Alert

1. **Create rule** → **Elasticsearch query**
2. Index: `cms-search-logs`
3. Condition: `response_time_ms > 1000`
4. Threshold: count > `50` in `1 hour`
5. Name: `Search Latency SLA Breach`

### 11.3 — Search Volume Anomaly (requires ML license)

1. Go to **Machine Learning** → **Anomaly Detection** → **Create job**
2. Data view: **CMS Search Logs**
3. Use **Single metric** job: count over time
4. Bucket span: `1h`
5. This will auto-detect unusual search volume drops or spikes

---

## Step 12 — Create a Scripted Field for MRR (Optional Advanced)

For a more accurate Mean Reciprocal Rank calculation:

1. Go to **Stack Management** → **Data Views** → **CMS Click Logs**
2. Click **Add scripted field** (or use Runtime fields)
3. Name: `reciprocal_rank`
4. Type: `number`
5. Script:
   ```painless
   if (doc['position'].size() > 0 && doc['position'].value > 0) {
     return 1.0 / doc['position'].value;
   }
   return 0;
   ```
6. **Save**

Now in any visualization, you can use `Average of reciprocal_rank` for true MRR.

---

## Quick Reference — Field Cheat Sheet

### cms-content
| Field | Type | Use for |
|-------|------|---------|
| `title` / `title.raw` | text / keyword | Top content tables |
| `content_type` | keyword | image, video, audio, document, article, book, paper |
| `category` | keyword | nature, technology, business, health, travel, etc. |
| `source` | keyword | unsplash, pexels, pixabay, freesound, wikipedia, arxiv, gutenberg, archive |
| `tags` | keyword | Tag analysis |
| `author` | keyword | Author leaderboards |
| `region` | keyword | Geographic distribution |
| `view_count` | integer | Popularity ranking |
| `download_count` | integer | Download metrics |
| `created_at` | date | Time-series of content creation |

### cms-search-logs
| Field | Type | Use for |
|-------|------|---------|
| `query_text.raw` | keyword | Top queries, zero-results |
| `search_type` | keyword | hybrid / keyword / image breakdown |
| `result_count` | integer | Hit rate (filter =0 for failures) |
| `response_time_ms` | integer | Latency percentiles, SLA |
| `user_id` | keyword | Unique user counts |
| `session_id` | keyword | Session analysis |
| `region` | keyword | Regional search patterns |
| `geo` | geo_point | Map visualizations |
| `filters_used` | keyword | Filter adoption tracking |
| `timestamp` | date | All time-series |

### cms-click-logs
| Field | Type | Use for |
|-------|------|---------|
| `content_id` | keyword | Most clicked content |
| `query_text.raw` | keyword | Query-to-click mapping |
| `position` | integer | Click position distribution, MRR |
| `search_type` | keyword | Click behavior by search type |
| `region` | keyword | Regional click patterns |
| `timestamp` | date | Time-series |

### cms-content-views
| Field | Type | Use for |
|-------|------|---------|
| `content_id` | keyword | Most viewed content |
| `content_type` | keyword | Views by content type |
| `category` | keyword | Engagement by category |
| `referrer` | keyword | search / recommendation / direct / external |
| `time_spent_seconds` | integer | Engagement depth |
| `region` | keyword | Regional consumption |
| `timestamp` | date | Time-series |

---

## Summary — All 25 Panels

| # | Panel | Chart Type | Data View |
|---|-------|-----------|-----------|
| 1 | Total Assets | Metric | CMS Content |
| 2 | Total Searches | Metric | CMS Search Logs |
| 3 | Search Hit Rate % | Metric (formula) | CMS Search Logs |
| 4 | Avg Response Time | Metric | CMS Search Logs |
| 5 | Total Content Views | Metric | CMS Content Views |
| 6 | Unique Users | Metric (cardinality) | CMS Search Logs |
| 7 | Search Volume by Type | Line | CMS Search Logs |
| 8 | Search Hit Rate Over Time | Dual-axis Line | CMS Search Logs |
| 9 | Response Time Percentiles | Area | CMS Search Logs |
| 10 | Search Type Distribution | Donut | CMS Search Logs |
| 11 | Filter Usage | Horizontal Bar | CMS Search Logs |
| 12 | Top Searched Queries | Tag Cloud | CMS Search Logs |
| 13 | Top Queries — Detailed | Table | CMS Search Logs |
| 14 | Zero-Result Queries | Table | CMS Search Logs |
| 15 | Click Position Distribution | Bar | CMS Click Logs |
| 16 | MRR by Search Type | Line (formula) | CMS Click Logs |
| 17 | Most Viewed Content | Table | CMS Content |
| 18 | Content by Type | Treemap | CMS Content |
| 19 | Content by Source | Horizontal Bar | CMS Content |
| 20 | Views by Referrer Source | Stacked Area | CMS Content Views |
| 21 | Engagement Heatmap | Heatmap | CMS Content Views |
| 22 | Avg Time Spent by Type | Bar | CMS Content Views |
| 23 | Search Activity Map | Map | CMS Search Logs |
| 24 | Top Queries by Region | Table | CMS Search Logs |
| 25 | Hybrid vs Keyword Hit Rate | 2x Metric (formula) | CMS Search Logs |
