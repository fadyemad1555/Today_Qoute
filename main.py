import flet as ft
import requests
import time
import random


# Rate limiting and caching
last_request_time = 0
request_delay = 5.0  # 5 seconds between requests to avoid rate limits
quote_cache = []
cache_index = 0
daily_quote_cache = None
daily_quote_date = None

# Built-in offline quotes as fallback
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
    """Check if enough time has passed since last request"""
    global last_request_time
    current_time = time.time()
    time_since_last = current_time - last_request_time
    
    if time_since_last < request_delay:
        return False, request_delay - time_since_last
    return True, 0


def safe_api_request(url, timeout=8):
    """Make a safe API request with rate limiting"""
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
    """Fetch random quote with intelligent caching"""
    global quote_cache, cache_index
    
    # Use cache if available
    if quote_cache and cache_index < len(quote_cache):
        quote = quote_cache[cache_index]
        cache_index += 1
        return {
            "text": quote['q'],
            "author": quote['a'],
            "source": "Random Quote",
            "success": True
        }
    
    # Try to fetch new quotes if cache is empty
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
    
    # Use offline quotes as fallback
    quote = random.choice(OFFLINE_QUOTES)
    return {
        "text": quote['q'],
        "author": quote['a'],
        "source": "Offline Quote",
        "success": True
    }


def get_quote_of_day():
    """Fetch quote of the day with caching"""
    global daily_quote_cache, daily_quote_date
    
    # Check if we have today's cached quote
    import datetime
    today = datetime.date.today().isoformat()
    
    if daily_quote_cache and daily_quote_date == today:
        return daily_quote_cache
    
    # Try to fetch today's quote
    response = safe_api_request("https://zenquotes.io/api/today")
    
    if response:
        try:
            data = response.json()
            if data and isinstance(data, list):
                result = {
                    "text": data[0]['q'],
                    "author": data[0]['a'],
                    "source": "✨ Quote of the Day",
                    "success": True
                }
                # Cache it
                daily_quote_cache = result
                daily_quote_date = today
                return result
        except Exception as e:
            print(f"Failed to parse daily quote: {e}")
    
    # Fallback to random quote if API fails
    return get_random_quote()


def main(page: ft.Page):
    # Page configuration
    page.title = "Quote Explorer"
    page.theme_mode = ft.ThemeMode.DARK
    page.window.width = 520
    page.window.height = 720
    page.padding = 30
    page.bgcolor = "#0f172a"
    
    # Current quote data
    current_quote = {"text": "", "author": "", "source": ""}
    
    # UI Components
    quote_text = ft.Text(
        value="",
        size=24,
        color="#fbbf24",
        weight=ft.FontWeight.W_500,
        text_align=ft.TextAlign.CENTER,
        selectable=True,
        max_lines=10
    )
    
    author_text = ft.Text(
        value="",
        size=18,
        color="#fcd34d",
        italic=True,
        text_align=ft.TextAlign.CENTER,
        selectable=True,
        weight=ft.FontWeight.W_600
    )
    
    source_chip = ft.Container(
        content=ft.Text(
            value="",
            size=12,
            color="#94a3b8",
            text_align=ft.TextAlign.CENTER,
            weight=ft.FontWeight.W_500
        ),
        bgcolor="#1e293b",
        padding=ft.padding.symmetric(horizontal=15, vertical=8),
        border_radius=20,
        visible=False
    )
    
    loading_container = ft.Container(
        content=ft.Column(
            [
                ft.ProgressRing(
                    color="#fbbf24",
                    width=40,
                    height=40,
                    stroke_width=3
                ),
                ft.Text(
                    "Loading...",
                    size=14,
                    color="#94a3b8",
                    text_align=ft.TextAlign.CENTER
                )
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=12
        ),
        visible=False
    )
    
    error_container = ft.Container(
        content=ft.Row(
            [
                ft.Icon(ft.Icons.INFO_OUTLINE, color="#fbbf24", size=20),
                ft.Text(
                    value="",
                    size=13,
                    color="#fcd34d",
                    expand=True,
                    text_align=ft.TextAlign.CENTER
                )
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=8
        ),
        bgcolor="#1e293b",
        border=ft.border.all(1, "#fbbf24"),
        padding=12,
        border_radius=10,
        visible=False
    )
    
    def show_error(message):
        """Display error message"""
        error_container.content.controls[1].value = message
        error_container.visible = True
        page.update()
    
    def hide_error():
        """Hide error message"""
        error_container.visible = False
        page.update()
    
    def update_quote_display(quote_data):
        """Update the UI with new quote data"""
        loading_container.visible = False
        
        if quote_data.get("success"):
            hide_error()
            current_quote.update(quote_data)
            quote_text.value = f'"{quote_data["text"]}"'
            author_text.value = f"— {quote_data['author']}"
            source_chip.content.value = quote_data.get('source', '')
            source_chip.visible = True
            quote_text.visible = True
            author_text.visible = True
        else:
            quote_text.visible = False
            author_text.visible = False
            source_chip.visible = False
            show_error(quote_data.get("error", "Unable to load quote"))
        
        page.update()
    
    def fetch_quote(fetch_function, *args):
        """Generic quote fetching with loading state"""
        hide_error()
        quote_text.visible = False
        author_text.visible = False
        source_chip.visible = False
        loading_container.visible = True
        page.update()
        
        quote_data = fetch_function(*args)
        update_quote_display(quote_data)
    
    def on_random_click(e):
        fetch_quote(get_random_quote)
    
    def on_daily_click(e):
        fetch_quote(get_quote_of_day)
    
    def on_copy_click(e):
        """Copy quote to clipboard"""
        if not current_quote.get("text"):
            show_error("⚠️ No quote to copy")
            return
        
        full_text = f'{current_quote["text"]}\n— {current_quote["author"]}'
        page.set_clipboard(full_text)
        
        # Show success feedback
        snackbar = ft.SnackBar(
            content=ft.Text("✓ Quote copied to clipboard!", color="#fff"),
            bgcolor="#16a34a",
            duration=2000
        )
        page.overlay.append(snackbar)
        snackbar.open = True
        page.update()
    
    def on_share_click(e):
        """Share quote"""
        if not current_quote.get("text"):
            show_error("⚠️ No quote to share")
            return
        
        full_text = f'{current_quote["text"]}\n— {current_quote["author"]}'
        page.set_clipboard(full_text)
        
        snackbar = ft.SnackBar(
            content=ft.Text("✓ Quote ready to share! (Copied)", color="#fff"),
            bgcolor="#16a34a",
            duration=2500
        )
        page.overlay.append(snackbar)
        snackbar.open = True
        page.update()
    
    # Quote display container
    quote_container = ft.Container(
        content=ft.Column(
            [
                ft.Icon(
                    ft.Icons.FORMAT_QUOTE_ROUNDED,
                    size=50,
                    color="#fbbf24",
                    opacity=0.4
                ),
                quote_text,
                author_text,
                loading_container,
                source_chip,
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=15
        ),
        border_radius=20,
        bgcolor="#1e293b",
        padding=35,
        gradient=ft.LinearGradient(
            begin=ft.alignment.top_left,
            end=ft.alignment.bottom_right,
            colors=["#1e293b", "#0f172a"]
        ),
        border=ft.border.all(1, "#334155"),
        shadow=ft.BoxShadow(
            spread_radius=0,
            blur_radius=25,
            color=ft.Colors.with_opacity(0.6, ft.Colors.BLACK),
            offset=ft.Offset(0, 10)
        ),
        expand=True
    )
    
    # Action buttons
    button_random = ft.Container(
        content=ft.Column(
            [
                ft.Icon(ft.Icons.SHUFFLE_ROUNDED, color="#0f172a", size=28),
                ft.Text("Random", size=13, color="#0f172a", weight=ft.FontWeight.BOLD)
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=6
        ),
        bgcolor="#fbbf24",
        border_radius=14,
        padding=18,
        ink=True,
        on_click=on_random_click,
        expand=True,
        shadow=ft.BoxShadow(
            spread_radius=0,
            blur_radius=10,
            color=ft.Colors.with_opacity(0.4, "#fbbf24"),
            offset=ft.Offset(0, 4)
        )
    )
    
    button_daily = ft.Container(
        content=ft.Column(
            [
                ft.Icon(ft.Icons.TODAY_ROUNDED, color="#fbbf24", size=28),
                ft.Text("Daily", size=13, color="#fbbf24", weight=ft.FontWeight.BOLD)
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=6
        ),
        bgcolor="#1e293b",
        border=ft.border.all(2, "#fbbf24"),
        border_radius=14,
        padding=18,
        ink=True,
        on_click=on_daily_click,
        expand=True
    )
    
    button_copy = ft.Container(
        content=ft.Column(
            [
                ft.Icon(ft.Icons.COPY_ROUNDED, color="#fbbf24", size=28),
                ft.Text("Copy", size=13, color="#fbbf24", weight=ft.FontWeight.BOLD)
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=6
        ),
        bgcolor="#1e293b",
        border=ft.border.all(2, "#fbbf24"),
        border_radius=14,
        padding=18,
        ink=True,
        on_click=on_copy_click,
        expand=True
    )
    
    button_share = ft.Container(
        content=ft.Column(
            [
                ft.Icon(ft.Icons.SHARE_ROUNDED, color="#fbbf24", size=28),
                ft.Text("Share", size=13, color="#fbbf24", weight=ft.FontWeight.BOLD)
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=6
        ),
        bgcolor="#1e293b",
        border=ft.border.all(2, "#fbbf24"),
        border_radius=14,
        padding=18,
        ink=True,
        on_click=on_share_click,
        expand=True
    )
    
    buttons_row1 = ft.Row(
        [button_random, button_daily],
        spacing=12,
        alignment=ft.MainAxisAlignment.CENTER
    )
    
    buttons_row2 = ft.Row(
        [button_copy, button_share],
        spacing=12,
        alignment=ft.MainAxisAlignment.CENTER
    )
    
    # Main layout
    main_column = ft.Column(
        [
            ft.Container(
                content=ft.Column(
                    [
                        ft.Text(
                            "Quote Explorer",
                            size=36,
                            weight=ft.FontWeight.BOLD,
                            color="#fbbf24",
                            text_align=ft.TextAlign.CENTER,
                        ),
                        ft.Text(
                            "Daily inspiration at your fingertips",
                            size=14,
                            color="#94a3b8",
                            text_align=ft.TextAlign.CENTER,
                            italic=True
                        ),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=6
                ),
                padding=ft.padding.only(bottom=20)
            ),
            quote_container,
            ft.Container(content=error_container, padding=ft.padding.only(top=10, bottom=10)),
            ft.Container(
                content=ft.Column(
                    [
                        ft.Text(
                            "Quick Actions",
                            size=16,
                            weight=ft.FontWeight.BOLD,
                            color="#fbbf24",
                        ),
                        buttons_row1,
                        buttons_row2,
                    ],
                    spacing=12
                ),
                padding=ft.padding.only(top=10)
            ),
        ],
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        spacing=0,
        expand=True
    )
    
    page.add(main_column)
    
    # Load initial quote
    fetch_quote(get_random_quote)


if __name__ == "__main__":
    ft.app(target=main, view=ft.AppView.FLET_APP)