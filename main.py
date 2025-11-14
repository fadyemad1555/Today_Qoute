import flet as ft
import requests
import time
import random

# Try to import ads, but gracefully handle if not available
try:
    from flet_ads import BannerAd, InterstitialAd, BannerAdSize
    ADS_AVAILABLE = True
except ImportError:
    ADS_AVAILABLE = False
    print("Ads module not available. Install with: pip install flet-ads")


# Rate limiting and caching
last_request_time = 0
request_delay = 5.0
quote_cache = []
cache_index = 0
daily_quote_cache = None
daily_quote_date = None
browse_quotes_cache = []
browse_cache_time = None

OFFLINE_QUOTES = [
    {"q": "The only way to do great work is to love what you do.", "a": "Steve Jobs"},
    {"q": "Innovation distinguishes between a leader and a follower.", "a": "Steve Jobs"},
    {"q": "Life is what happens when you're busy making other plans.", "a": "John Lennon"},
    {"q": "The future belongs to those who believe in the beauty of their dreams.", "a": "Eleanor Roosevelt"},
    {"q": "It is during our darkest moments that we must focus to see the light.", "a": "Aristotle"},
    {"q": "The only impossible journey is the one you never begin.", "a": "Tony Robbins"},
    {"q": "In the middle of difficulty lies opportunity.", "a": "Albert Einstein"},
    {"q": "Success is not final, failure is not fatal: it is the courage to continue that counts.", "a": "Winston Churchill"},
    {"q": "Believe you can and you're halfway there.", "a": "Theodore Roosevelt"},
    {"q": "The best time to plant a tree was 20 years ago. The second best time is now.", "a": "Chinese Proverb"},
    {"q": "Your time is limited, don't waste it living someone else's life.", "a": "Steve Jobs"},
    {"q": "The way to get started is to quit talking and begin doing.", "a": "Walt Disney"},
    {"q": "Don't watch the clock; do what it does. Keep going.", "a": "Sam Levenson"},
    {"q": "The future depends on what you do today.", "a": "Mahatma Gandhi"},
    {"q": "Everything you've ever wanted is on the other side of fear.", "a": "George Addair"},
    {"q": "Believe in yourself. You are braver than you think.", "a": "Unknown"},
    {"q": "What we think, we become.", "a": "Buddha"},
    {"q": "The journey of a thousand miles begins with one step.", "a": "Lao Tzu"},
    {"q": "Life is 10% what happens to you and 90% how you react to it.", "a": "Charles R. Swindoll"},
    {"q": "Change your thoughts and you change your world.", "a": "Norman Vincent Peale"},
]


def can_make_request():
    global last_request_time
    current_time = time.time()
    time_since_last = current_time - last_request_time
    
    if time_since_last < request_delay:
        return False, request_delay - time_since_last
    return True, 0


def safe_api_request(url, timeout=8):
    global last_request_time
    
    can_request, wait_time = can_make_request()
    
    if not can_request:
        print(f"Rate limited: waiting {wait_time:.1f}s before next request")
        return None
    
    try:
        response = requests.get(url, timeout=timeout)
        last_request_time = time.time()
        
        if response.status_code == 429:
            print("Rate limit hit (429), using cache/offline quotes")
            return None
        
        response.raise_for_status()
        return response
    except Exception as e:
        print(f"API request failed: {e}")
        return None


def get_random_quote():
    global quote_cache, cache_index
    
    if quote_cache and cache_index < len(quote_cache):
        quote = quote_cache[cache_index]
        cache_index += 1
        return {
            "text": quote['q'],
            "author": quote['a'],
            "source": "Random Quote",
            "success": True
        }
    
    response = safe_api_request("https://zenquotes.io/api/quotes")
    
    if response:
        try:
            data = response.json()
            if data and isinstance(data, list):
                quote_cache = data
                cache_index = 0
                quote = random.choice(data)
                return {
                    "text": quote['q'],
                    "author": quote['a'],
                    "source": "Random Quote",
                    "success": True
                }
        except Exception as e:
            print(f"Failed to parse response: {e}")
    
    quote = random.choice(OFFLINE_QUOTES)
    return {
        "text": quote['q'],
        "author": quote['a'],
        "source": "Offline Quote",
        "success": True
    }


def get_quote_of_day():
    global daily_quote_cache, daily_quote_date
    
    import datetime
    today = datetime.date.today().isoformat()
    
    if daily_quote_cache and daily_quote_date == today:
        return daily_quote_cache
    
    response = safe_api_request("https://zenquotes.io/api/today")
    
    if response:
        try:
            data = response.json()
            if data and isinstance(data, list):
                result = {
                    "text": data[0]['q'],
                    "author": data[0]['a'],
                    "source": "Quote of the Day",
                    "success": True
                }
                daily_quote_cache = result
                daily_quote_date = today
                return result
        except Exception as e:
            print(f"Failed to parse daily quote: {e}")
    
    return get_random_quote()


def get_browse_quotes():
    global browse_quotes_cache, browse_cache_time
    
    # Cache browse quotes for 1 hour
    current_time = time.time()
    if browse_quotes_cache and browse_cache_time and (current_time - browse_cache_time < 3600):
        return {"quotes": browse_quotes_cache, "success": True, "source": "cache"}
    
    response = safe_api_request("https://zenquotes.io/api/quotes")
    
    if response:
        try:
            data = response.json()
            if data and isinstance(data, list):
                browse_quotes_cache = data
                browse_cache_time = current_time
                return {"quotes": data, "success": True, "source": "api"}
        except Exception as e:
            print(f"Failed to parse browse quotes: {e}")
    
    # Return offline quotes if API fails
    if not browse_quotes_cache:
        browse_quotes_cache = OFFLINE_QUOTES
    
    return {"quotes": browse_quotes_cache, "success": True, "source": "offline"}


def main(page: ft.Page):
    page.title = "Quote Explorer"
    page.theme_mode = ft.ThemeMode.DARK
    page.window.width = 480
    page.window.height = 700
    page.padding = 0
    page.bgcolor = "#0a0e1a"
    
    current_quote = {"text": "", "author": "", "source": ""}
    current_page_view = ft.Ref[ft.Container]()
    
    # Initialize ads if available
    interstitial_ad = None
    if ADS_AVAILABLE:
        try:
            # Test AdMob unit IDs for Android (use iOS IDs for iOS)
            interstitial_ad = InterstitialAd(
                unit_id="ca-app-pub-3940256099942544/1033173712",  # Test ID for Android
            )
            
            def on_ad_loaded(e):
                print("Interstitial ad loaded successfully!")
            
            def on_ad_error(e):
                print(f"Ad error: {e.data}")
            
            interstitial_ad.on_load = on_ad_loaded
            interstitial_ad.on_error = on_ad_error
            interstitial_ad.load()
        except Exception as e:
            print(f"Failed to initialize ads: {e}")
            interstitial_ad = None
    
    # Animated decorative elements
    def create_deco_circles():
        return ft.Container(
            content=ft.Stack(
                [
                    ft.Container(
                        width=400,
                        height=400,
                        border_radius=200,
                        bgcolor=ft.Colors.with_opacity(0.03, "#fbbf24"),
                        blur=ft.Blur(50, 50, ft.BlurTileMode.CLAMP),
                        left=-100,
                        top=-150
                    ),
                    ft.Container(
                        width=300,
                        height=300,
                        border_radius=150,
                        bgcolor=ft.Colors.with_opacity(0.02, "#60a5fa"),
                        blur=ft.Blur(40, 40, ft.BlurTileMode.CLAMP),
                        right=-80,
                        bottom=-100
                    ),
                ]
            ),
            expand=True
        )
    
    # Navigation bar
    def create_nav_button(icon, label, page_name, is_active=False):
        def on_nav_click(e):
            switch_page(page_name)
        
        return ft.Container(
            content=ft.Column(
                [
                    ft.Icon(
                        icon,
                        color="#fbbf24" if is_active else "#64748b",
                        size=22
                    ),
                    ft.Text(
                        label,
                        size=10,
                        color="#fbbf24" if is_active else "#64748b",
                        weight=ft.FontWeight.BOLD if is_active else ft.FontWeight.W_500
                    )
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=4
            ),
            padding=ft.padding.symmetric(horizontal=16, vertical=10),
            ink=True,
            on_click=on_nav_click,
            border_radius=12,
            bgcolor=ft.Colors.with_opacity(0.1, "#fbbf24") if is_active else None,
            animate=ft.Animation(200, ft.AnimationCurve.EASE_OUT),
        )
    
    nav_home = create_nav_button(ft.Icons.HOME_ROUNDED, "Home", "home", True)
    nav_browse = create_nav_button(ft.Icons.EXPLORE_ROUNDED, "Browse", "browse", False)
    nav_about = create_nav_button(ft.Icons.INFO_ROUNDED, "About", "about", False)
    
    navbar = ft.Container(
        content=ft.Row(
            [nav_home, nav_browse, nav_about],
            alignment=ft.MainAxisAlignment.SPACE_AROUND,
            spacing=0
        ),
        bgcolor=ft.Colors.with_opacity(0.95, "#1e293b"),
        padding=ft.padding.symmetric(vertical=8, horizontal=20),
        border=ft.border.only(top=ft.BorderSide(1, ft.Colors.with_opacity(0.2, "#475569"))),
        shadow=ft.BoxShadow(
            spread_radius=0,
            blur_radius=20,
            color=ft.Colors.with_opacity(0.4, ft.Colors.BLACK),
            offset=ft.Offset(0, -5)
        ),
    )
    
    def update_nav_active(active_page):
        for nav, page_name in [(nav_home, "home"), (nav_browse, "browse"), (nav_about, "about")]:
            is_active = page_name == active_page
            nav.bgcolor = ft.Colors.with_opacity(0.1, "#fbbf24") if is_active else None
            nav.content.controls[0].color = "#fbbf24" if is_active else "#64748b"
            nav.content.controls[1].color = "#fbbf24" if is_active else "#64748b"
            nav.content.controls[1].weight = ft.FontWeight.BOLD if is_active else ft.FontWeight.W_500
        page.update()
    
    # Home Page Components
    quote_icon = ft.Icon(
        ft.Icons.FORMAT_QUOTE_ROUNDED,
        size=56,
        color="#fbbf24",
        opacity=0.15
    )
    
    quote_text = ft.Text(
        value="",
        size=17,
        color="#f8fafc",
        weight=ft.FontWeight.W_500,
        text_align=ft.TextAlign.CENTER,
        selectable=True,
        max_lines=None,
    )
    
    author_text = ft.Text(
        value="",
        size=12,
        color="#94a3b8",
        italic=True,
        text_align=ft.TextAlign.CENTER,
        selectable=True,
        weight=ft.FontWeight.W_500
    )
    
    source_badge = ft.Container(
        content=ft.Row(
            [
                ft.Icon(ft.Icons.AUTO_AWESOME_ROUNDED, size=14, color="#fbbf24"),
                ft.Text(
                    value="",
                    size=11,
                    color="#cbd5e1",
                    weight=ft.FontWeight.W_600,
                    text_align=ft.TextAlign.CENTER,
                )
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=6
        ),
        bgcolor="#1e293b",
        padding=ft.padding.symmetric(horizontal=16, vertical=7),
        border_radius=25,
        border=ft.border.all(1, "#334155"),
        visible=False
    )
    
    loading_ring = ft.ProgressRing(
        color="#fbbf24",
        width=50,
        height=50,
        stroke_width=3.5
    )
    
    loading_container = ft.Container(
        content=ft.Column(
            [
                loading_ring,
                ft.Text(
                    "Fetching inspiration...",
                    size=13,
                    color="#64748b",
                    text_align=ft.TextAlign.CENTER,
                    weight=ft.FontWeight.W_500
                )
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=16
        ),
        visible=False
    )
    
    error_container = ft.Container(
        content=ft.Row(
            [
                ft.Icon(ft.Icons.ERROR_OUTLINE_ROUNDED, color="#fb923c", size=18),
                ft.Text(
                    value="",
                    size=12,
                    color="#fcd34d",
                    expand=True,
                    text_align=ft.TextAlign.CENTER,
                    weight=ft.FontWeight.W_500
                )
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=8
        ),
        bgcolor=ft.Colors.with_opacity(0.1, "#fb923c"),
        border=ft.border.all(1, ft.Colors.with_opacity(0.3, "#fb923c")),
        padding=14,
        border_radius=12,
        visible=False
    )
    
    def show_error(message):
        error_container.content.controls[1].value = message
        error_container.visible = True
        page.update()
    
    def hide_error():
        error_container.visible = False
        page.update()
    
    def update_quote_display(quote_data):
        loading_container.visible = False
        
        if quote_data.get("success"):
            hide_error()
            current_quote.update(quote_data)
            quote_text.value = f'"{quote_data["text"]}"'
            author_text.value = f"— {quote_data['author']}"
            source_badge.content.controls[1].value = quote_data.get('source', '')
            source_badge.visible = True
            quote_text.visible = True
            author_text.visible = True
        else:
            quote_text.visible = False
            author_text.visible = False
            source_badge.visible = False
            show_error(quote_data.get("error", "Unable to load quote"))
        
        page.update()
    
    def fetch_quote(fetch_function, *args):
        hide_error()
        quote_text.visible = False
        author_text.visible = False
        source_badge.visible = False
        loading_container.visible = True
        page.update()
        
        quote_data = fetch_function(*args)
        update_quote_display(quote_data)
    
    def on_random_click(e):
        fetch_quote(get_random_quote)
    
    def on_daily_click(e):
        fetch_quote(get_quote_of_day)
    
    def on_copy_click(e):
        if not current_quote.get("text"):
            show_error("⚠️ No quote to copy")
            return
        
        full_text = f'{current_quote["text"]}\n— {current_quote["author"]}'
        page.set_clipboard(full_text)
        
        snackbar = ft.SnackBar(
            content=ft.Row(
                [
                    ft.Icon(ft.Icons.CHECK_CIRCLE_ROUNDED, color="#10b981", size=20),
                    ft.Text("Quote copied!", color="#fbbf24", size=14, weight=ft.FontWeight.W_500)
                ],
                spacing=8
            ),
            bgcolor="#1e293b",
            duration=2000,
            behavior=ft.SnackBarBehavior.FLOATING,
        )
        page.overlay.append(snackbar)
        snackbar.open = True
        page.update()
    
    # Quote display container
    quote_content = ft.Column(
        [
            quote_icon,
            ft.Container(height=8),
            quote_text,
            ft.Container(height=12),
            author_text,
            ft.Container(height=8),
            loading_container,
            source_badge,
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        alignment=ft.MainAxisAlignment.CENTER,
        spacing=0,
        scroll=ft.ScrollMode.ADAPTIVE,
    )
    
    quote_container = ft.Container(
        content=quote_content,
        border_radius=24,
        bgcolor=ft.Colors.with_opacity(0.9, "#1e293b"),
        padding=40,
        gradient=ft.LinearGradient(
            begin=ft.alignment.top_left,
            end=ft.alignment.bottom_right,
            colors=[
                ft.Colors.with_opacity(0.05, "#fbbf24"),
                ft.Colors.with_opacity(0.02, "#1e293b")
            ]
        ),
        border=ft.border.all(1, ft.Colors.with_opacity(0.2, "#475569")),
        shadow=ft.BoxShadow(
            spread_radius=0,
            blur_radius=30,
            color=ft.Colors.with_opacity(0.3, ft.Colors.BLACK),
            offset=ft.Offset(0, 15)
        ),
        blur=ft.Blur(10, 10, ft.BlurTileMode.CLAMP),
        height=340,
    )
    
    # Action buttons
    def create_button(icon, label, on_click, is_primary=False):
        return ft.Container(
            content=ft.Column(
                [
                    ft.Icon(
                        icon,
                        color="#0f172a" if is_primary else "#fbbf24",
                        size=24
                    ),
                    ft.Text(
                        label,
                        size=11,
                        color="#0f172a" if is_primary else "#fbbf24",
                        weight=ft.FontWeight.BOLD
                    )
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=6
            ),
            bgcolor="#fbbf24" if is_primary else ft.Colors.with_opacity(0.05, "#1e293b"),
            border=None if is_primary else ft.border.all(1.5, ft.Colors.with_opacity(0.6, "#fbbf24")),
            border_radius=14,
            padding=16,
            ink=True,
            on_click=on_click,
            expand=True,
            shadow=ft.BoxShadow(
                spread_radius=0,
                blur_radius=15 if is_primary else 8,
                color=ft.Colors.with_opacity(0.35 if is_primary else 0.2, "#fbbf24"),
                offset=ft.Offset(0, 6)
            ) if is_primary else None,
            animate=ft.Animation(150, ft.AnimationCurve.EASE_OUT),
        )
    
    button_random = create_button(ft.Icons.SHUFFLE_ROUNDED, "Random", on_random_click, True)
    button_daily = create_button(ft.Icons.TODAY_ROUNDED, "Daily", on_daily_click, False)
    button_copy = create_button(ft.Icons.CONTENT_COPY_ROUNDED, "Copy", on_copy_click, False)
    
    buttons_row = ft.Row(
        [button_random, button_daily, button_copy],
        spacing=10,
        alignment=ft.MainAxisAlignment.CENTER
    )
    
    # Header
    header = ft.Container(
        content=ft.Column(
            [
                ft.Text(
                    "Quote Explorer",
                    size=38,
                    weight=ft.FontWeight.BOLD,
                    color="#f8fafc",
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.Container(
                    content=ft.Text(
                        "Daily inspiration at your fingertips",
                        size=13,
                        color="#64748b",
                        text_align=ft.TextAlign.CENTER,
                        weight=ft.FontWeight.W_500
                    ),
                    padding=ft.padding.only(top=2)
                ),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=4
        ),
        padding=ft.padding.only(top=30, bottom=20, left=30, right=30)
    )
    
    # Home page content
    home_content = ft.Column(
        [
            header,
            ft.Container(
                content=quote_container,
                padding=ft.padding.symmetric(horizontal=30)
            ),
            ft.Container(
                content=error_container,
                padding=ft.padding.only(top=16, bottom=8, left=30, right=30)
            ),
            ft.Container(
                content=ft.Column(
                    [
                        ft.Container(
                            content=ft.Text(
                                "Quick Actions",
                                size=14,
                                weight=ft.FontWeight.BOLD,
                                color="#94a3b8",
                            ),
                            padding=ft.padding.only(bottom=10)
                        ),
                        buttons_row,
                    ],
                    spacing=12
                ),
                padding=ft.padding.only(top=16, bottom=20, left=30, right=30)
            ),
        ],
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        spacing=0,
        scroll=ft.ScrollMode.ADAPTIVE,
        auto_scroll=False,
        expand=True,
    )
    
    # Browse Page Components
    browse_quotes_list = ft.Column(
        spacing=16,
        scroll=ft.ScrollMode.ADAPTIVE,
        auto_scroll=False,
    )
    
    browse_loading = ft.Container(
        content=ft.Column(
            [
                ft.ProgressRing(color="#fbbf24", width=50, height=50, stroke_width=3.5),
                ft.Text(
                    "Loading quotes...",
                    size=13,
                    color="#64748b",
                    weight=ft.FontWeight.W_500
                )
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=16
        ),
        expand=True,
        alignment=ft.alignment.center
    )
    
    def create_quote_card(quote_data, index):
        def copy_quote(e):
            full_text = f'{quote_data["q"]}\n— {quote_data["a"]}'
            page.set_clipboard(full_text)
            
            snackbar = ft.SnackBar(
                content=ft.Row(
                    [
                        ft.Icon(ft.Icons.CHECK_CIRCLE_ROUNDED, color="#10b981", size=18),
                        ft.Text("Copied!", color="#fbbf24", size=13, weight=ft.FontWeight.W_500)
                    ],
                    spacing=8
                ),
                bgcolor="#1e293b",
                duration=1500,
                behavior=ft.SnackBarBehavior.FLOATING,
            )
            page.overlay.append(snackbar)
            snackbar.open = True
            page.update()
        
        # Alternate colors for variety
        colors = [
            ("#fbbf24", "#fef3c7"),  # amber
            ("#60a5fa", "#dbeafe"),  # blue
            ("#a78bfa", "#ede9fe"),  # violet
            ("#f472b6", "#fce7f3"),  # pink
            ("#34d399", "#d1fae5"),  # emerald
        ]
        primary_color, secondary_color = colors[index % len(colors)]
        
        return ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Icon(
                                ft.Icons.FORMAT_QUOTE,
                                size=20,
                                color=primary_color,
                                opacity=0.7
                            ),
                            ft.Container(expand=True),
                            ft.IconButton(
                                icon=ft.Icons.CONTENT_COPY,
                                icon_size=18,
                                icon_color=ft.Colors.with_opacity(0.6, "#94a3b8"),
                                on_click=copy_quote,
                                tooltip="Copy quote"
                            )
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    ft.Text(
                        f'"{quote_data["q"]}"',
                        size=15,
                        color="#f8fafc",
                        weight=ft.FontWeight.W_500,
                        selectable=True,
                    ),
                    ft.Container(height=8),
                    ft.Text(
                        f"— {quote_data['a']}",
                        size=12,
                        color="#94a3b8",
                        italic=True,
                        weight=ft.FontWeight.W_500,
                        selectable=True,
                    ),
                ],
                spacing=8
            ),
            bgcolor=ft.Colors.with_opacity(0.05, "#1e293b"),
            border=ft.border.all(1, ft.Colors.with_opacity(0.2, primary_color)),
            border_radius=16,
            padding=20,
            animate=ft.Animation(200, ft.AnimationCurve.EASE_OUT),
            shadow=ft.BoxShadow(
                spread_radius=0,
                blur_radius=10,
                color=ft.Colors.with_opacity(0.1, primary_color),
                offset=ft.Offset(0, 4)
            ),
        )
    
    def load_browse_quotes(append=False):
        if not append:
            browse_quotes_list.controls.clear()
            browse_loading.visible = True
        else:
            # Remove the "Load More" button and attribution if they exist
            if len(browse_quotes_list.controls) > 0:
                # Remove last 2 items (attribution and load more button)
                browse_quotes_list.controls = browse_quotes_list.controls[:-2] if len(browse_quotes_list.controls) >= 2 else []
        
        page.update()
        
        result = get_browse_quotes()
        
        browse_loading.visible = False
        
        if result.get("success"):
            quotes = result.get("quotes", [])
            start_index = len([c for c in browse_quotes_list.controls if isinstance(c, ft.Container)])
            
            for i, quote in enumerate(quotes):
                browse_quotes_list.controls.append(create_quote_card(quote, start_index + i))
            
            # Add "Load More" button
            def on_load_more(e):
                load_browse_quotes(append=True)
            
            load_more_button = ft.Container(
                content=ft.Row(
                    [
                        ft.Icon(ft.Icons.REFRESH_ROUNDED, color="#fbbf24", size=20),
                        ft.Text(
                            "Load More Quotes",
                            size=14,
                            color="#fbbf24",
                            weight=ft.FontWeight.BOLD
                        )
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=8
                ),
                bgcolor=ft.Colors.with_opacity(0.05, "#1e293b"),
                border=ft.border.all(1.5, ft.Colors.with_opacity(0.6, "#fbbf24")),
                border_radius=14,
                padding=16,
                ink=True,
                on_click=on_load_more,
                shadow=ft.BoxShadow(
                    spread_radius=0,
                    blur_radius=8,
                    color=ft.Colors.with_opacity(0.2, "#fbbf24"),
                    offset=ft.Offset(0, 4)
                ),
                animate=ft.Animation(150, ft.AnimationCurve.EASE_OUT),
            )
            
            browse_quotes_list.controls.append(load_more_button)
            
            # Add attribution at the bottom
            browse_quotes_list.controls.append(
                ft.Container(
                    content=ft.Text(
                        "Quotes provided by ZenQuotes.io",
                        size=11,
                        color="#64748b",
                        text_align=ft.TextAlign.CENTER,
                        weight=ft.FontWeight.W_400
                    ),
                    padding=ft.padding.only(top=10, bottom=20)
                )
            )
        else:
            browse_quotes_list.controls.append(
                ft.Container(
                    content=ft.Text(
                        "Failed to load quotes. Please try again.",
                        size=13,
                        color="#fb923c",
                        text_align=ft.TextAlign.CENTER,
                    ),
                    padding=20
                )
            )
        
        page.update()
    
    browse_header = ft.Container(
        content=ft.Column(
            [
                ft.Text(
                    "Browse Quotes",
                    size=32,
                    weight=ft.FontWeight.BOLD,
                    color="#f8fafc",
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.Text(
                    "Scroll through our curated collection",
                    size=13,
                    color="#64748b",
                    text_align=ft.TextAlign.CENTER,
                    weight=ft.FontWeight.W_500
                ),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=4
        ),
        padding=ft.padding.only(top=30, bottom=20, left=30, right=30)
    )
    
    browse_content = ft.Column(
        [
            browse_header,
            ft.Container(
                content=ft.Stack(
                    [
                        browse_quotes_list,
                        browse_loading,
                    ]
                ),
                padding=ft.padding.symmetric(horizontal=30),
                expand=True,
            ),
        ],
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        spacing=0,
        expand=True,
    )
    
    # About page content
    def show_support_ad(e):
        if interstitial_ad:
            try:
                if interstitiagitl_ad.is_loaded():
                    interstitial_ad.show()
                    
                    # Show thank you message
                    snackbar = ft.SnackBar(
                        content=ft.Row(
                            [
                                ft.Icon(ft.Icons.FAVORITE, color="#f472b6", size=20),
                                ft.Text("Thank you for your support! 💝", color="#fbbf24", size=14, weight=ft.FontWeight.W_500)
                            ],
                            spacing=8
                        ),
                        bgcolor="#1e293b",
                        duration=3000,
                        behavior=ft.SnackBarBehavior.FLOATING,
                    )
                    page.overlay.append(snackbar)
                    snackbar.open = True
                    page.update()
                    
                    # Reload ad for next time
                    interstitial_ad.load()
                else:
                    # Ad not loaded yet
                    snackbar = ft.SnackBar(
                        content=ft.Row(
                            [
                                ft.Icon(ft.Icons.INFO_OUTLINE, color="#60a5fa", size=20),
                                ft.Text("Ad is loading... Please try again in a moment", color="#fbbf24", size=13, weight=ft.FontWeight.W_500)
                            ],
                            spacing=8
                        ),
                        bgcolor="#1e293b",
                        duration=2000,
                        behavior=ft.SnackBarBehavior.FLOATING,
                    )
                    page.overlay.append(snackbar)
                    snackbar.open = True
                    page.update()
                    interstitial_ad.load()
            except Exception as e:
                print(f"Error showing ad: {e}")
                show_support_message()
        else:
            show_support_message()
    
    def show_support_message():
        snackbar = ft.SnackBar(
            content=ft.Row(
                [
                    ft.Icon(ft.Icons.INFO_OUTLINE, color="#60a5fa", size=20),
                    ft.Text("Ads only available on mobile apps", color="#fbbf24", size=13, weight=ft.FontWeight.W_500)
                ],
                spacing=8
            ),
            bgcolor="#1e293b",
            duration=2500,
            behavior=ft.SnackBarBehavior.FLOATING,
        )
        page.overlay.append(snackbar)
        snackbar.open = True
        page.update()
    
    about_content = ft.Column(
        [
            ft.Container(
                content=ft.Column(
                    [
                        ft.Container(
                            content=ft.Icon(
                                ft.Icons.AUTO_STORIES_ROUNDED,
                                size=64,
                                color="#fbbf24"
                            ),
                            padding=ft.padding.only(bottom=12)
                        ),
                        ft.Text(
                            "Quote Explorer",
                            size=34,
                            weight=ft.FontWeight.BOLD,
                            color="#f8fafc",
                            text_align=ft.TextAlign.CENTER,
                        ),
                        ft.Text(
                            "Version 2.0",
                            size=13,
                            color="#64748b",
                            text_align=ft.TextAlign.CENTER,
                            weight=ft.FontWeight.W_500
                        ),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=4
                ),
                padding=ft.padding.only(top=30, bottom=25, left=30, right=30)
            ),
            ft.Container(
                content=ft.Column(
                    [
                        ft.Text(
                            "About This App",
                            size=17,
                            weight=ft.FontWeight.BOLD,
                            color="#f8fafc",
                        ),
                        ft.Container(height=6),
                        ft.Text(
                            "Quote Explorer brings you daily inspiration through carefully curated quotes from thinkers, leaders, and visionaries throughout history. Browse through our extensive collection or get a fresh random quote anytime.",
                            size=13,
                            color="#94a3b8",
                            weight=ft.FontWeight.W_400,
                            text_align=ft.TextAlign.LEFT,
                        ),
                        ft.Container(height=20),
                        ft.Container(
                            content=ft.Column(
                                [
                                    ft.Text(
                                        "Support the Developer",
                                        size=15,
                                        weight=ft.FontWeight.BOLD,
                                        color="#f8fafc",
                                    ),
                                    ft.Container(height=8),
                                    ft.Text(
                                        "Help keep this app free and ad-free! Watch a quick ad to support development.",
                                        size=13,
                                        color="#94a3b8",
                                        weight=ft.FontWeight.W_400,
                                        text_align=ft.TextAlign.CENTER,
                                    ),
                                    ft.Container(height=12),
                                    ft.Container(
                                        content=ft.Row(
                                            [
                                                ft.Icon(ft.Icons.PLAY_CIRCLE_FILLED, color="#f472b6", size=22),
                                                ft.Text(
                                                    "Support Me - Watch Ad",
                                                    size=14,
                                                    color="#f8fafc",
                                                    weight=ft.FontWeight.BOLD
                                                )
                                            ],
                                            alignment=ft.MainAxisAlignment.CENTER,
                                            spacing=10
                                        ),
                                        bgcolor=ft.Colors.with_opacity(0.15, "#f472b6"),
                                        border=ft.border.all(1.5, ft.Colors.with_opacity(0.6, "#f472b6")),
                                        border_radius=14,
                                        padding=16,
                                        ink=True,
                                        on_click=show_support_ad,
                                        shadow=ft.BoxShadow(
                                            spread_radius=0,
                                            blur_radius=12,
                                            color=ft.Colors.with_opacity(0.3, "#f472b6"),
                                            offset=ft.Offset(0, 4)
                                        ),
                                        animate=ft.Animation(150, ft.AnimationCurve.EASE_OUT),
                                    ),
                                ],
                                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                spacing=0
                            ),
                            bgcolor=ft.Colors.with_opacity(0.05, "#1e293b"),
                            border=ft.border.all(1, ft.Colors.with_opacity(0.2, "#475569")),
                            border_radius=12,
                            padding=16,
                        ),
                        ft.Container(height=20),
                        ft.Container(
                            content=ft.Column(
                                [
                                    ft.Text(
                                        "Features:",
                                        size=15,
                                        weight=ft.FontWeight.BOLD,
                                        color="#f8fafc",
                                    ),
                                    ft.Container(height=8),
                                    ft.Text("• Random inspirational quotes", size=13, color="#94a3b8"),
                                    ft.Text("• Daily featured quote", size=13, color="#94a3b8"),
                                    ft.Text("• Browse extensive collection", size=13, color="#94a3b8"),
                                    ft.Text("• One-tap copy to clipboard", size=13, color="#94a3b8"),
                                    ft.Text("• Beautiful modern interface", size=13, color="#94a3b8"),
                                ],
                                spacing=6
                            ),
                            bgcolor=ft.Colors.with_opacity(0.05, "#1e293b"),
                            border=ft.border.all(1, ft.Colors.with_opacity(0.2, "#475569")),
                            border_radius=12,
                            padding=16,
                        ),
                        ft.Container(height=20),
                        ft.Container(
                            content=ft.Column(
                                [
                                    ft.Text(
                                        "Made with ❤️ BY FADY",
                                        size=12,
                                        color="#f8fafc",
                                        text_align=ft.TextAlign.CENTER,
                                        weight=ft.FontWeight.W_600
                                    ),
                                    ft.Container(height=8),
                                    ft.Text(
                                        "Powered by ZenQuotes API",
                                        size=11,
                                        color="#64748b",
                                        text_align=ft.TextAlign.CENTER,
                                        weight=ft.FontWeight.W_400
                                    ),
                                    ft.Container(height=4),
                                    ft.Text(
                                        "© 2025 Quote Explorer",
                                        size=11,
                                        color="#64748b",
                                        text_align=ft.TextAlign.CENTER,
                                        weight=ft.FontWeight.W_400
                                    ),
                                ],
                                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                spacing=0
                            ),
                            padding=ft.padding.symmetric(vertical=16)
                        ),
                    ],
                    spacing=0
                ),
                padding=ft.padding.symmetric(horizontal=30)
            ),
        ],
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        spacing=0,
        scroll=ft.ScrollMode.ADAPTIVE,
        auto_scroll=False,
        expand=True,
    )
    
    # Page container
    page_container = ft.Container(
        ref=current_page_view,
        content=home_content,
        expand=True,
        animate=ft.Animation(300, ft.AnimationCurve.EASE_IN_OUT)
    )
    
    def switch_page(page_name):
        if page_name == "home":
            page_container.content = home_content
            update_nav_active("home")
        elif page_name == "browse":
            page_container.content = browse_content
            update_nav_active("browse")
            load_browse_quotes()
        elif page_name == "about":
            page_container.content = about_content
            update_nav_active("about")
        page.update()
    
    # Main layout
    page.add(
        ft.Column(
            [
                ft.Stack(
                    [
                        create_deco_circles(),
                        page_container
                    ],
                    expand=True
                ),
                navbar
            ],
            spacing=0,
            expand=True
        )
    )
    
    # Load initial quote
    fetch_quote(get_random_quote)


if __name__ == "__main__":
    ft.app(target=main)