import flet as ft

# ----------------------------------------------------------------------
# Placeholder data (layout only — no real logic)
# ----------------------------------------------------------------------
REMINDERS = [
    {"title": "Analyze AMZN & TSLA", "body": "Daily outlook with technicals + news digest.",
     "schedule": "Weekdays 8:00 AM", "status": "ok", "target": "Slack #markets"},
    {"title": "Crypto morning digest", "body": "BTC/ETH summary and overnight headlines.",
     "schedule": "Daily 7:30 AM", "status": "running", "target": "WeChat"},
    {"title": "Portfolio risk check", "body": "Flag any position that breaches risk threshold.",
     "schedule": "Mondays 9:00 AM", "status": "failed", "target": "Email"},
]

AGENTS = [
    {"name": "Stock Analyst", "version": "1.2.0",
     "description": "Analyzes equities and produces outlook reports.",
     "capabilities": ["streaming", "push"],
     "skills": [("Fundamental Analysis", ["finance", "equities"]),
                ("Technical Signals", ["charts", "TA"])]},
    {"name": "News Summarizer", "version": "0.9.1",
     "description": "Fetches and summarizes recent news for a topic.",
     "capabilities": ["streaming"],
     "skills": [("Headline Digest", ["news", "nlp"])]},
    {"name": "Report Composer", "version": "2.0.0",
     "description": "Merges multiple agent outputs into one formatted report.",
     "capabilities": ["push"],
     "skills": [("Markdown Report", ["formatting"]),
                ("Chart Embed", ["viz"])]},
]

RUNS = [
    {"task": "Analyze AMZN & TSLA", "when": "Today 8:00 AM", "status": "ok", "took": "42s"},
    {"task": "Crypto morning digest", "when": "Today 7:30 AM", "status": "running", "took": "—"},
    {"task": "Portfolio risk check", "when": "Mon 9:00 AM", "status": "failed", "took": "12s"},
]

INTEGRATIONS = [
    {"name": "Slack", "icon": ft.Icons.CHAT, "connected": True, "detail": "workspace: my-team"},
    {"name": "WeChat", "icon": ft.Icons.MESSAGE, "connected": True, "detail": "bound account"},
    {"name": "Email", "icon": ft.Icons.EMAIL, "connected": True, "detail": "me@example.com"},
    {"name": "Telegram", "icon": ft.Icons.SEND, "connected": False, "detail": "not connected"},
]

STATUS = {
    "ok": (ft.Icons.CHECK_CIRCLE, ft.Colors.GREEN),
    "running": (ft.Icons.AUTORENEW, ft.Colors.BLUE),
    "failed": (ft.Icons.ERROR, ft.Colors.RED),
}


# ----------------------------------------------------------------------
# Small reusable pieces
# ----------------------------------------------------------------------
def page_title(text, action=None):
    row = [ft.Text(text, size=26, weight=ft.FontWeight.BOLD, expand=True)]
    if action:
        row.append(action)
    return ft.Row(row, vertical_alignment=ft.CrossAxisAlignment.CENTER)


def badge(text, color=ft.Colors.BLUE_400):
    return ft.Container(
        content=ft.Text(text, size=11, color=ft.Colors.WHITE),
        bgcolor=color, border_radius=12,
        padding=ft.padding.symmetric(horizontal=8, vertical=3),
    )


# ----------------------------------------------------------------------
# VIEW 1 — Reminders / Tasks
# ----------------------------------------------------------------------
def reminder_card(r):
    icon, color = STATUS[r["status"]]
    return ft.Card(
        content=ft.Container(
            padding=16,
            content=ft.Column([
                ft.Row([
                    ft.Icon(icon, color=color),
                    ft.Text(r["title"], size=16, weight=ft.FontWeight.BOLD, expand=True),
                    ft.IconButton(ft.Icons.EDIT, tooltip="Edit"),
                    ft.IconButton(ft.Icons.MORE_VERT),
                ]),
                ft.Text(r["body"], size=13, color=ft.Colors.GREY_700),
                ft.Row([
                    ft.Chip(label=ft.Text(r["schedule"]),
                            leading=ft.Icon(ft.Icons.SCHEDULE, size=16)),
                    ft.Chip(label=ft.Text(r["target"]),
                            leading=ft.Icon(ft.Icons.SEND, size=16)),
                ], spacing=8, wrap=True),
            ], spacing=10),
        )
    )


def reminders_view():
    new_btn = ft.FilledButton("New reminder", icon=ft.Icons.ADD)
    return ft.Column([
        page_title("My Reminders", action=new_btn),
        ft.Text("Reminders double as notes and run as scheduled agent tasks.",
                size=13, color=ft.Colors.GREY_600),
        ft.Divider(),
        ft.Column([reminder_card(r) for r in REMINDERS], spacing=12),
    ], spacing=14, scroll=ft.ScrollMode.AUTO, expand=True)


# ----------------------------------------------------------------------
# VIEW 1b — Task editor (the create/edit screen), shown as a section
# ----------------------------------------------------------------------
def task_editor_view():
    return ft.Column([
        page_title("New Reminder"),
        ft.Divider(),

        ft.Text("Note", size=14, weight=ft.FontWeight.BOLD),
        ft.TextField(label="Title", value="Analyze AMZN & TSLA"),
        ft.TextField(label="Description (rich text)", multiline=True, min_lines=4,
                     value="Please analyze AMZN and TSLA and summarize the outlook."),

        ft.Divider(),
        ft.Text("Schedule", size=14, weight=ft.FontWeight.BOLD),
        ft.Row([
            ft.Dropdown(label="Frequency", width=200,
                        options=[ft.dropdown.Option("Once"),
                                 ft.dropdown.Option("Daily"),
                                 ft.dropdown.Option("Weekdays"),
                                 ft.dropdown.Option("Custom (cron)")],
                        value="Weekdays"),
            ft.TextField(label="Time", value="08:00", width=120),
            ft.Dropdown(label="Timezone", width=200,
                        options=[ft.dropdown.Option("UTC"),
                                 ft.dropdown.Option("US/Eastern"),
                                 ft.dropdown.Option("Asia/Shanghai")],
                        value="US/Eastern"),
        ], spacing=12, wrap=True),
        ft.Text("Next runs:  Mon 8:00, Tue 8:00, Wed 8:00",
                size=12, color=ft.Colors.GREY_600),

        ft.Divider(),
        ft.Text("Execution plan", size=14, weight=ft.FontWeight.BOLD),
        ft.SegmentedButton(
            selected={"auto"},
            segments=[
                ft.Segment(value="auto", label=ft.Text("Auto (agentic)"),
                           icon=ft.Icon(ft.Icons.AUTO_AWESOME)),
                ft.Segment(value="manual", label=ft.Text("Manual"),
                           icon=ft.Icon(ft.Icons.TUNE)),
            ],
        ),
        ft.Container(
            bgcolor=ft.Colors.GREY_100, border_radius=8, padding=16,
            content=ft.Column([
                ft.Text("Proposed DAG (preview) — approve before saving",
                        size=12, color=ft.Colors.GREY_700),
                ft.Text("Analyze AMZN  ┐\nAnalyze TSLA  ┼─▶ Synthesize Report ─▶ Deliver",
                        size=13, font_family="monospace"),
                ft.Row([ft.TextButton("Edit plan"),
                        ft.FilledButton("Approve plan")],
                       alignment=ft.MainAxisAlignment.END),
            ], spacing=8),
        ),

        ft.Divider(),
        ft.Text("Delivery", size=14, weight=ft.FontWeight.BOLD),
        ft.Row([
            ft.Dropdown(label="Send report to", width=220,
                        options=[ft.dropdown.Option("Slack #markets"),
                                 ft.dropdown.Option("WeChat"),
                                 ft.dropdown.Option("Email")],
                        value="Slack #markets"),
            ft.Dropdown(label="Format", width=180,
                        options=[ft.dropdown.Option("Markdown"),
                                 ft.dropdown.Option("PDF"),
                                 ft.dropdown.Option("Plain text")],
                        value="Markdown"),
        ], spacing=12, wrap=True),

        ft.Divider(),
        ft.Row([ft.TextButton("Cancel"),
                ft.FilledButton("Save reminder", icon=ft.Icons.SAVE)],
               alignment=ft.MainAxisAlignment.END),
    ], spacing=12, scroll=ft.ScrollMode.AUTO, expand=True)


# ----------------------------------------------------------------------
# VIEW 2 — Agents catalog
# ----------------------------------------------------------------------
def agent_card(a):
    return ft.Card(
        content=ft.Container(
            width=340, padding=16,
            content=ft.Column([
                ft.Row([
                    ft.CircleAvatar(content=ft.Icon(ft.Icons.SMART_TOY),
                                    bgcolor=ft.Colors.INDIGO_100),
                    ft.Column([
                        ft.Text(a["name"], size=17, weight=ft.FontWeight.BOLD),
                        ft.Text(f"v{a['version']}", size=11, color=ft.Colors.GREY_500),
                    ], spacing=0),
                ], spacing=10),
                ft.Text(a["description"], size=13, color=ft.Colors.GREY_700),
                ft.Row([badge(c) for c in a["capabilities"]], wrap=True, spacing=6),
                ft.Divider(height=8),
                ft.Text("Skills", size=12, weight=ft.FontWeight.BOLD),
                ft.Column([
                    ft.Row([
                        ft.Icon(ft.Icons.BOLT, size=16, color=ft.Colors.AMBER),
                        ft.Text(name, size=13, weight=ft.FontWeight.W_500),
                        ft.Text("  ".join(f"#{t}" for t in tags),
                                size=11, color=ft.Colors.GREY_500),
                    ], spacing=6)
                    for name, tags in a["skills"]
                ], spacing=6),
                ft.Row([ft.TextButton("View card"),
                        ft.FilledButton("Use in task")],
                       alignment=ft.MainAxisAlignment.END),
            ], spacing=12),
        )
    )


def agents_view():
    add_btn = ft.OutlinedButton("Add agent", icon=ft.Icons.ADD_LINK)
    return ft.Column([
        page_title("Available Agents", action=add_btn),
        ft.Text("Registered A2A agents. Cards show live capabilities and skills.",
                size=13, color=ft.Colors.GREY_600),
        ft.Divider(),
        ft.Row([agent_card(a) for a in AGENTS], wrap=True, spacing=16, run_spacing=16),
    ], spacing=14, scroll=ft.ScrollMode.AUTO, expand=True)


# ----------------------------------------------------------------------
# VIEW 3 — Runs / Activity
# ----------------------------------------------------------------------
def runs_view():
    rows = []
    for run in RUNS:
        icon, color = STATUS[run["status"]]
        rows.append(ft.DataRow(cells=[
            ft.DataCell(ft.Row([ft.Icon(icon, color=color, size=18),
                                ft.Text(run["status"])], spacing=6)),
            ft.DataCell(ft.Text(run["task"])),
            ft.DataCell(ft.Text(run["when"])),
            ft.DataCell(ft.Text(run["took"])),
            ft.DataCell(ft.TextButton("View report")),
        ]))
    table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("Status")),
            ft.DataColumn(ft.Text("Task")),
            ft.DataColumn(ft.Text("When")),
            ft.DataColumn(ft.Text("Duration")),
            ft.DataColumn(ft.Text("")),
        ],
        rows=rows,
    )
    return ft.Column([
        page_title("Runs & Activity"),
        ft.Text("Every scheduled execution and its DAG run appears here.",
                size=13, color=ft.Colors.GREY_600),
        ft.Divider(),
        table,
    ], spacing=14, scroll=ft.ScrollMode.AUTO, expand=True)


# ----------------------------------------------------------------------
# VIEW 4 — Integrations / Delivery
# ----------------------------------------------------------------------
def integration_card(i):
    status_color = ft.Colors.GREEN if i["connected"] else ft.Colors.GREY_400
    status_text = "Connected" if i["connected"] else "Not connected"
    btn = ft.OutlinedButton("Disconnect") if i["connected"] else ft.FilledButton("Connect")
    return ft.Card(
        content=ft.Container(
            width=280, padding=16,
            content=ft.Column([
                ft.Row([
                    ft.Icon(i["icon"], size=28),
                    ft.Text(i["name"], size=16, weight=ft.FontWeight.BOLD, expand=True),
                    ft.Icon(ft.Icons.CIRCLE, size=12, color=status_color),
                ]),
                ft.Text(status_text, size=12, color=status_color),
                ft.Text(i["detail"], size=12, color=ft.Colors.GREY_600),
                ft.Row([btn], alignment=ft.MainAxisAlignment.END),
            ], spacing=10),
        )
    )


def integrations_view():
    return ft.Column([
        page_title("Integrations & Delivery"),
        ft.Text("Connect destinations once, then reference them from any reminder.",
                size=13, color=ft.Colors.GREY_600),
        ft.Divider(),
        ft.Row([integration_card(i) for i in INTEGRATIONS],
               wrap=True, spacing=16, run_spacing=16),
    ], spacing=14, scroll=ft.ScrollMode.AUTO, expand=True)


# ----------------------------------------------------------------------
# App shell — navigation rail + content area
# ----------------------------------------------------------------------
def main(page: ft.Page):
    page.title = "Smart Reminders"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 0

    content = ft.Container(expand=True, padding=24, content=reminders_view())

    # index -> builder  (index 1 is the editor, reachable from the rail here for preview)
    views = {
        0: reminders_view,
        1: task_editor_view,
        2: agents_view,
        3: runs_view,
        4: integrations_view,
    }

    def on_nav_change(e):
        content.content = views[e.control.selected_index]()
        page.update()

    rail = ft.NavigationRail(
        selected_index=0,
        label_type=ft.NavigationRailLabelType.ALL,
        min_width=100,
        group_alignment=-0.9,
        on_change=on_nav_change,
        destinations=[
            ft.NavigationRailDestination(icon=ft.Icons.NOTES, label="Reminders"),
            ft.NavigationRailDestination(icon=ft.Icons.EDIT_NOTE, label="New Task"),
            ft.NavigationRailDestination(icon=ft.Icons.SMART_TOY, label="Agents"),
            ft.NavigationRailDestination(icon=ft.Icons.HISTORY, label="Runs"),
            ft.NavigationRailDestination(icon=ft.Icons.HUB, label="Integrations"),
        ],
    )

    page.add(
        ft.Row([
            rail,
            ft.VerticalDivider(width=1),
            content,
        ], expand=True, spacing=0)
    )


ft.app(main)
