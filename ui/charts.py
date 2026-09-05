"""
Plotly chart generators for crawl analytics, depth breakdowns, and network graph visualization.
Styled with a high-end cyber-analytics dark aesthetic.
"""

from typing import List, Dict, Tuple
import html
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import networkx as nx
from urllib.parse import urlparse

from crawler.models import PageResult


DARK_PLOT_BG = "rgba(15, 23, 42, 0.65)"
DARK_GRID_COLOR = "rgba(255, 255, 255, 0.08)"
FONT_FAMILY = "Plus Jakarta Sans, sans-serif"


def create_depth_bar_chart(pages: List[PageResult]) -> go.Figure:
    """Create bar chart showing count of pages crawled at each depth level."""
    if not pages:
        fig = go.Figure()
        fig.update_layout(
            title=dict(text="Pages Crawled by Depth (No Data)", font=dict(color="#94A3B8")),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
        )
        return fig

    depth_counts = pd.Series([p.depth for p in pages]).value_counts().sort_index()
    df = pd.DataFrame({"Depth": [f"Depth {d}" for d in depth_counts.index], "Pages Crawled": depth_counts.values})

    fig = px.bar(
        df,
        x="Depth",
        y="Pages Crawled",
        color="Pages Crawled",
        color_continuous_scale=[[0, "#00f0ff"], [1, "#8b5cf6"]],
        text="Pages Crawled",
        title="Pages Crawled by Traversal Depth",
    )
    fig.update_traces(
        textposition="outside",
        textfont=dict(color="#f8fafc", family=FONT_FAMILY, size=11),
        marker=dict(line=dict(width=1, color="rgba(255,255,255,0.15)")),
    )
    fig.update_layout(
        title=dict(font=dict(color="#FFFFFF", size=14, family=FONT_FAMILY)),
        xaxis=dict(
            title=dict(text="Crawling Depth", font=dict(color="#94A3B8", size=11)),
            tickfont=dict(color="#94A3B8", size=10),
            gridcolor=DARK_GRID_COLOR,
            showgrid=True,
        ),
        yaxis=dict(
            title=dict(text="Pages Crawled", font=dict(color="#94A3B8", size=11)),
            tickfont=dict(color="#94A3B8", size=10),
            gridcolor=DARK_GRID_COLOR,
            showgrid=True,
        ),
        coloraxis_showscale=False,
        margin=dict(l=20, r=20, t=45, b=20),
        height=320,
        plot_bgcolor=DARK_PLOT_BG,
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def create_status_donut_chart(pages_count: int, failures_count: int) -> go.Figure:
    """Create donut chart comparing successful vs failed requests."""
    labels = ["Successful Pages", "Failed Requests"]
    values = [pages_count, failures_count]
    colors = ["#10b981", "#ff3366"]

    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=0.62,
        marker=dict(colors=colors, line=dict(color="#0c101b", width=2)),
        textinfo="label+value",
        textfont=dict(color="#f8fafc", family=FONT_FAMILY, size=10),
        insidetextorientation="radial",
    )])
    fig.update_layout(
        title=dict(text="Crawl Success vs Failure Ratio", font=dict(color="#FFFFFF", size=14, family=FONT_FAMILY)),
        margin=dict(l=20, r=20, t=45, b=20),
        height=320,
        showlegend=False,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def create_links_distribution_chart(total_internal: int, total_external: int) -> go.Figure:
    """Create donut chart comparing total internal vs external links discovered."""
    labels = ["Internal Links (Same Domain)", "External Links (Outbound)"]
    values = [total_internal, total_external]
    colors = ["#00f0ff", "#a855f7"]

    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=0.62,
        marker=dict(colors=colors, line=dict(color="#0c101b", width=2)),
        textinfo="label+value",
        textfont=dict(color="#f8fafc", family=FONT_FAMILY, size=10),
    )])
    fig.update_layout(
        title=dict(text="Internal vs External Hyperlinks", font=dict(color="#FFFFFF", size=14, family=FONT_FAMILY)),
        margin=dict(l=20, r=20, t=45, b=20),
        height=320,
        showlegend=False,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def create_top_domains_chart(pages: List[PageResult], top_n: int = 10) -> go.Figure:
    """Create horizontal bar chart of top domains discovered across links."""
    domain_counts: Dict[str, int] = {}
    for p in pages:
        for ext_url in p.external_urls:
            dom = urlparse(ext_url).netloc.lower()
            if dom:
                domain_counts[dom] = domain_counts.get(dom, 0) + 1

    if not domain_counts:
        # Fallback to crawled pages domains
        for p in pages:
            if p.domain:
                domain_counts[p.domain] = domain_counts.get(p.domain, 0) + 1

    if not domain_counts:
        fig = go.Figure()
        fig.update_layout(
            title=dict(text="Top External Domains Discovered (No Data)", font=dict(color="#94A3B8")),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
        )
        return fig

    sorted_domains = sorted(domain_counts.items(), key=lambda x: x[1], reverse=True)[:top_n]
    df = pd.DataFrame(sorted_domains, columns=["Domain", "Frequency"])
    df = df.iloc[::-1]

    fig = px.bar(
        df,
        x="Frequency",
        y="Domain",
        orientation="h",
        color="Frequency",
        color_continuous_scale=[[0, "#8b5cf6"], [1, "#ec4899"]],
        text="Frequency",
        title=f"Top {len(df)} Discovered Domains",
    )
    fig.update_traces(
        textposition="outside",
        textfont=dict(color="#f8fafc", family=FONT_FAMILY, size=10),
        marker=dict(line=dict(width=1, color="rgba(255,255,255,0.1)")),
    )
    fig.update_layout(
        title=dict(font=dict(color="#FFFFFF", size=14, family=FONT_FAMILY)),
        xaxis=dict(
            title=dict(text="Referenced Count", font=dict(color="#94A3B8", size=11)),
            tickfont=dict(color="#94A3B8", size=10),
            gridcolor=DARK_GRID_COLOR,
            showgrid=True,
        ),
        yaxis=dict(
            title="",
            tickfont=dict(color="#94A3B8", size=10),
            gridcolor=DARK_GRID_COLOR,
            showgrid=False,
        ),
        coloraxis_showscale=False,
        margin=dict(l=20, r=20, t=45, b=20),
        height=320,
        plot_bgcolor=DARK_PLOT_BG,
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def create_response_time_chart(pages: List[PageResult]) -> go.Figure:
    """Create a scatter plot of response times across crawled pages with futuristic accents."""
    if not pages:
        fig = go.Figure()
        fig.update_layout(
            title=dict(text="Response Time Performance (No Data)", font=dict(color="#94A3B8")),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
        )
        return fig

    df = pd.DataFrame([{
        "Index": i + 1,
        "URL": p.url,
        "Title": p.title,
        "Depth": f"Depth {p.depth}",
        # Clamp to 0.001s minimum so no bubble has size=0 and disappears
        "Response Time (s)": max(p.response_time, 0.001),
    } for i, p in enumerate(pages)])

    fig = px.scatter(
        df,
        x="Index",
        y="Response Time (s)",
        color="Depth",
        color_discrete_sequence=["#00f0ff", "#8b5cf6", "#10b981", "#f59e0b"],
        hover_data=["Title", "URL"],
        title="Webpage Response Latency Telemetry",
        size="Response Time (s)",
        size_max=12,
    )
    # Add an average reference line
    avg_resp = df["Response Time (s)"].mean()
    fig.add_hline(
        y=avg_resp,
        line_dash="dash",
        line_color="#f59e0b",
        annotation_text=f"Mean Latency: {avg_resp:.3f}s",
        annotation_position="bottom right",
        annotation_font=dict(color="#f59e0b", size=10, family=FONT_FAMILY),
    )

    fig.update_layout(
        title=dict(font=dict(color="#FFFFFF", size=14, family=FONT_FAMILY)),
        xaxis=dict(
            title=dict(text="Crawl Sequence (#)", font=dict(color="#94A3B8", size=11)),
            tickfont=dict(color="#94A3B8", size=10),
            gridcolor=DARK_GRID_COLOR,
            showgrid=True,
        ),
        yaxis=dict(
            title=dict(text="Latency (seconds)", font=dict(color="#94A3B8", size=11)),
            tickfont=dict(color="#94A3B8", size=10),
            gridcolor=DARK_GRID_COLOR,
            showgrid=True,
        ),
        legend=dict(
            font=dict(color="#94A3B8", size=10, family=FONT_FAMILY),
            bgcolor="rgba(14,20,32,0.6)",
            bordercolor="rgba(255,255,255,0.06)",
        ),
        margin=dict(l=20, r=20, t=45, b=20),
        height=320,
        plot_bgcolor=DARK_PLOT_BG,
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def create_crawl_network_graph(
    pages: List[PageResult],
    edges: List[Tuple[str, str, int]],
    max_nodes: int = 60
) -> go.Figure:
    """
    Build a futuristic interactive 2D node-link network visualization of the crawl tree.
    Capped at max_nodes for optimal client-side performance.
    """
    if not pages:
        fig = go.Figure()
        fig.update_layout(
            title=dict(text="Crawl Graph Visualization (No Data)", font=dict(color="#94A3B8")),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
        )
        return fig

    # Build networkx DiGraph
    G = nx.DiGraph()

    display_pages = pages[:max_nodes]
    display_urls = {p.url for p in display_pages}

    for p in display_pages:
        short_title = p.title[:30] + "..." if len(p.title) > 30 else p.title
        G.add_node(
            p.url,
            title=short_title,
            depth=p.depth,
            links=p.unique_links,
            domain=p.domain,
            status=p.status_code,
        )

    # Add edges
    for src, tgt, depth in edges:
        if src in display_urls and tgt in display_urls:
            G.add_edge(src, tgt)
        elif src in display_urls and len(G.nodes) < max_nodes:
            G.add_node(
                tgt,
                title=tgt.split("/")[-1] or tgt,
                depth=depth,
                links=0,
                domain=urlparse(tgt).netloc,
                status=200,
            )
            G.add_edge(src, tgt)

    if len(G.nodes) == 0:
        fig = go.Figure()
        fig.update_layout(
            title=dict(text="Crawl Graph (Single Root Page)", font=dict(color="#94A3B8")),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
        )
        return fig

    # Compute spring layout
    try:
        pos = nx.spring_layout(G, k=0.5, iterations=40, seed=42)
    except Exception:
        pos = nx.circular_layout(G)

    # Prepare edge coordinates
    edge_x = []
    edge_y = []
    for edge in G.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])

    edge_trace = go.Scatter(
        x=edge_x,
        y=edge_y,
        line=dict(width=1.3, color="rgba(0, 240, 255, 0.3)"),
        hoverinfo="none",
        mode="lines",
    )

    # Prepare node coordinates and depth-based neon palette
    node_x = []
    node_y = []
    node_text = []
    node_color = []
    node_size = []

    # Cyber depth palette
    depth_color_map = {
        0: "#00f0ff",  # Cyan for Seed
        1: "#8b5cf6",  # Violet for Depth 1
        2: "#10b981",  # Neon Green for Depth 2
        3: "#f59e0b",  # Amber for Depth 3
    }

    for node in G.nodes():
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)
        data = G.nodes[node]
        depth = data.get("depth", 0)
        
        node_color.append(depth_color_map.get(depth, "#ec4899"))

        # Sizing
        if depth == 0:
            node_size.append(26)
        elif depth == 1:
            node_size.append(18)
        else:
            node_size.append(12)

        safe_node_title = html.escape(str(data.get('title', 'Page')))
        safe_node_url = html.escape(str(node))
        safe_node_domain = html.escape(str(data.get('domain', '')))
        hover_info = (
            f"<b>{safe_node_title}</b><br>"
            f"Depth Level: {depth}<br>"
            f"Target URL: {safe_node_url}<br>"
            f"Hyperlinks: {data.get('links', 0)}<br>"
            f"Host Domain: {safe_node_domain}"
        )
        node_text.append(hover_info)

    node_trace = go.Scatter(
        x=node_x,
        y=node_y,
        mode="markers+text",
        hoverinfo="text",
        text=[G.nodes[n].get("title", "")[:15] for n in G.nodes()],
        textposition="top center",
        textfont=dict(size=9, color="#94A3B8", family=FONT_FAMILY),
        marker=dict(
            color=node_color,
            size=node_size,
            line=dict(width=1.8, color="#FFFFFF"),
        ),
    )
    node_trace.hovertext = node_text

    fig = go.Figure(
        data=[edge_trace, node_trace],
        layout=go.Layout(
            title=dict(
                text="Interactive Crawl Traversal Topology (BFS Graph)",
                font=dict(color="#FFFFFF", size=15, family=FONT_FAMILY),
            ),
            showlegend=False,
            hovermode="closest",
            margin=dict(b=20, l=20, r=20, t=45),
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            height=490,
            plot_bgcolor="rgba(10, 15, 26, 0.8)",
            paper_bgcolor="rgba(0,0,0,0)",
        ),
    )
    return fig
