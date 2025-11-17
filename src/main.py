import flet as ft
import requests
import time
import random
import asyncio

# Try to import ads, but gracefully handle if not available
try:
    import flet_ads as fta
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
    """Make API request with proper error handling and rate limiting"""
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
        
        if response.status_code != 200:
            print(f"API returned status code: {response.status_code}")
            return None
        
        return response
    except requests.exceptions.Timeout:
        print(f"Request timeout for {url}")
        return None
    except requests.exceptions.ConnectionError:
        print(f"Connection error for {url}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Request exception: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error in API request: {e}")
        return None


def get_random_quote():
    """Fetch random quote with comprehensive error handling"""
    global quote_cache, cache_index
    
    try:
        # Use cache if available
        if quote_cache and cache_index < len(quote_cache):
            quote = quote_cache[cache_index]
            cache_index += 1
            return {
                "text": quote.get('q', ''),
                "author": quote.get('a', 'Unknown'),
                "source": "Random Quote",
                "success": True
            }
        
        # Try API request
        response = safe_api_request("https://zenquotes.io/api/quotes")
        
        if response:
            try:
                data = response.json()
                if data and isinstance(data, list) and len(data) > 0:
                    # Validate quote data
                    valid_quotes = [q for q in data if q.get('q') and q.get('a')]
                    if valid_quotes:
                        quote_cache = valid_quotes
                        cache_index = 0
                        quote = random.choice(valid_quotes)
                        return {
                            "text": quote.get('q', ''),
                            "author": quote.get('a', 'Unknown'),
                            "source": "Random Quote",
                            "success": True
                        }
            except ValueError as e:
                print(f"JSON parsing error: {e}")
            except Exception as e:
                print(f"Error processing API response: {e}")
        
        # Fallback to offline quotes
        print("Using offline quotes as fallback")
        quote = random.choice(OFFLINE_QUOTES)
        return {
            "text": quote['q'],
            "author": quote['a'],
            "source": "Offline Quote",
            "success": True
        }
    except Exception as e:
        print(f"Critical error in get_random_quote: {e}")
        # Last resort fallback
        return {
            "text": "Every moment is a fresh beginning.",
            "author": "T.S. Eliot",
            "source": "Offline Quote",
            "success": True
        }


def get_quote_of_day():
    """Fetch quote of the day with error handling and smart caching"""
    global daily_quote_cache, daily_quote_date
    
    try:
        import datetime
        today = datetime.date.today().isoformat()
        
        # Return cached daily quote if available for today
        if daily_quote_cache and daily_quote_date == today:
            print("Using cached daily quote")
            return daily_quote_cache
        
        # Fetch new daily quote
        print("Fetching fresh daily quote from API")
        response = safe_api_request("https://zenquotes.io/api/today")
        
        if response:
            try:
                data = response.json()
                if data and isinstance(data, list) and len(data) > 0:
                    quote = data[0]
                    if quote.get('q') and quote.get('a'):
                        result = {
                            "text": quote['q'],
                            "author": quote['a'],
                            "source": "Quote of the Day",
                            "success": True
                        }
                        # Cache the daily quote
                        daily_quote_cache = result
                        daily_quote_date = today
                        print(f"Daily quote cached for {today}")
                        return result
            except ValueError as e:
                print(f"JSON parsing error for daily quote: {e}")
            except Exception as e:
                print(f"Error processing daily quote: {e}")
        
        # If API fails but we have a cached quote from a previous day, use it with updated source
        if daily_quote_cache:
            print("API failed, using previous daily quote")
            cached_quote = daily_quote_cache.copy()
            cached_quote["source"] = "Previous Daily Quote"
            return cached_quote
        
        # Last resort: fallback to random quote
        print("No cached daily quote available, using random quote")
        random_quote = get_random_quote()
        random_quote["source"] = "Quote of the Day (Offline)"
        return random_quote
    except Exception as e:
        print(f"Critical error in get_quote_of_day: {e}")
        # Try to return cached quote even if date check fails
        if daily_quote_cache:
            return daily_quote_cache
        return get_random_quote()


def get_browse_quotes():
    """Fetch browse quotes with error handling"""
    global browse_quotes_cache, browse_cache_time
    
    try:
        # Use cache if recent (1 hour)
        current_time = time.time()
        if browse_quotes_cache and browse_cache_time and (current_time - browse_cache_time < 3600):
            return {"quotes": browse_quotes_cache, "success": True, "source": "cache"}
        
        response = safe_api_request("https://zenquotes.io/api/quotes")
        
        if response:
            try:
                data = response.json()
                if data and isinstance(data, list) and len(data) > 0:
                    # Validate quotes
                    valid_quotes = [q for q in data if q.get('q') and q.get('a')]
                    if valid_quotes:
                        browse_quotes_cache = valid_quotes
                        browse_cache_time = current_time
                        return {"quotes": valid_quotes, "success": True, "source": "api"}
            except ValueError as e:
                print(f"JSON parsing error for browse quotes: {e}")
            except Exception as e:
                print(f"Error processing browse quotes: {e}")
        
        # Use offline quotes as fallback
        if not browse_quotes_cache:
            browse_quotes_cache = OFFLINE_QUOTES
        
        return {"quotes": browse_quotes_cache, "success": True, "source": "offline"}
    except Exception as e:
        print(f"Critical error in get_browse_quotes: {e}")
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
    
    # Check if mobile platform
    is_mobile = page.platform in [ft.PagePlatform.ANDROID, ft.PagePlatform.IOS]
    
    # Test ad unit IDs
    ad_ids = {
        ft.PagePlatform.ANDROID: {
            "banner": "ca-app-pub-3940256099942544/6300978111",
        },
        ft.PagePlatform.IOS: {
            "banner": "ca-app-pub-3940256099942544/2934735716",
        },
    }
    
    # Banner ad state management
    ad_retry_count = 0
    max_ad_retries = 3  # Fast retries
    ad_retry_delay = 5  # seconds for fast retries
    ad_loaded_successfully = False  # Track if ad loaded successfully
    background_retry_delay = 20  # seconds for background retries
    background_retry_running = False  # Track if background retry is running
    
    def create_ad_placeholder(message="Ad Space"):
        """Create a placeholder for banner ad"""
        return ft.Container(
            width=320,
            height=50,
            bgcolor=ft.Colors.with_opacity(0.05, "#1e293b"),
            border=ft.border.all(1, ft.Colors.with_opacity(0.1, "#475569")),
            border_radius=8,
            alignment=ft.alignment.center,
            content=ft.Text(
                message,
                size=10,
                color="#64748b",
                weight=ft.FontWeight.W_400
            )
        )
    
    # Create banner ad container reference
    banner_ad_container = ft.Container(
        content=create_ad_placeholder("Ad Loading..." if is_mobile and ADS_AVAILABLE else "Ad Space"),
        alignment=ft.alignment.center,
    )
    
    async def background_retry_ad():
        """Keep retrying ad load in background every 20 seconds until success"""
        global ad_loaded_successfully, background_retry_running
        
        background_retry_running = True
        print("Background retry task started")
        
        while not ad_loaded_successfully:
            try:
                print(f"Background retry: waiting {background_retry_delay}s... (loaded={ad_loaded_successfully})")
                await asyncio.sleep(background_retry_delay)
                
                if not ad_loaded_successfully:
                    print("Background retry: attempting to load ad...")
                    try:
                        load_banner_ad()
                    except Exception as e:
                        print(f"Background retry failed: {e}")
                else:
                    print("Background retry: ad loaded successfully, stopping background retries")
                    break
            except Exception as e:
                print(f"Error in background retry loop: {e}")
                await asyncio.sleep(background_retry_delay)
        
        background_retry_running = False
        print("Background retry task stopped")
    
    async def delayed_retry():
        """Delayed retry using asyncio"""
        try:
            await asyncio.sleep(ad_retry_delay)
            load_banner_ad()
        except Exception as e:
            print(f"Delayed retry failed: {e}")
            retry_banner_ad()
    
    def retry_banner_ad():
        """Retry loading banner ad after error"""
        global ad_retry_count, background_retry_running
        
        # Don't retry if ad already loaded successfully
        if ad_loaded_successfully:
            print("Ad already loaded successfully, skipping retry")
            return
        
        if ad_retry_count >= max_ad_retries:
            print(f"Fast retries ({max_ad_retries}) completed, starting background retries every {background_retry_delay}s")
            banner_ad_container.content = create_ad_placeholder("Ad will retry...")
            page.update()
            
            # Start background retry task if not already running
            if not background_retry_running:
                page.run_task(background_retry_ad)
                print("Background retry task scheduled")
            return
        
        ad_retry_count += 1
        print(f"Fast retry {ad_retry_count}/{max_ad_retries}...")
        
        banner_ad_container.content = create_ad_placeholder(f"Retrying {ad_retry_count}/{max_ad_retries}...")
        page.update()
        
        # Schedule delayed retry
        page.run_task(delayed_retry)
    
    def load_banner_ad():
        """Load banner ad with error handling and retry logic"""
        global ad_retry_count, ad_loaded_successfully
        
        # Don't reload if ad already loaded successfully
        if ad_loaded_successfully:
            print("Banner ad already loaded successfully, skipping reload")
            return
        
        if not ADS_AVAILABLE or not is_mobile:
            banner_ad_container.content = create_ad_placeholder("Ad Space")
            page.update()
            return
        
        try:
            def on_ad_load(e):
                global ad_loaded_successfully
                print("🎉 BannerAd loaded successfully - will not refresh, background retries stopped")
                ad_loaded_successfully = True  # Mark as loaded, prevent future reloads
                ad_retry_count = 0  # Reset retry count on success
                # Update placeholder to remove retry message
                try:
                    page.update()
                except:
                    pass
            
            def on_ad_error(e):
                # Only retry if ad hasn't loaded successfully yet
                if not ad_loaded_successfully:
                    error_msg = e.data if hasattr(e, 'data') else str(e)
                    print(f"BannerAd error: {error_msg}")
                    retry_banner_ad()
                else:
                    print("Ad error occurred but ad already loaded, ignoring")
            
            new_ad = fta.BannerAd(
                unit_id=ad_ids.get(page.platform, {}).get("banner"),
                on_click=lambda e: print("BannerAd clicked"),
                on_load=on_ad_load,
                on_error=on_ad_error,
                on_open=lambda e: print("BannerAd opened"),
                on_close=lambda e: print("BannerAd closed"),
                on_impression=lambda e: print("BannerAd impression"),
                on_will_dismiss=lambda e: print("BannerAd will dismiss"),
            )
            
            banner_ad_container.content = ft.Container(
                width=320,
                height=50,
                bgcolor=ft.Colors.TRANSPARENT,
                alignment=ft.alignment.center,
                content=new_ad,
            )
            page.update()
            
        except Exception as e:
            print(f"Failed to create banner ad: {e}")
            if not ad_loaded_successfully:
                retry_banner_ad()
    
    # Initialize banner ad
    if ADS_AVAILABLE and is_mobile:
        load_banner_ad()
    
    # Animated decorative elements
    def create_deco_circles():
        try:
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
        except Exception as e:
            print(f"Error creating decorative circles: {e}")
            return ft.Container(expand=True)
    
    # Navigation bar
    def create_nav_button(icon, label, page_name, is_active=False):
        def on_nav_click(e):
            try:
                switch_page(page_name)
            except Exception as ex:
                print(f"Error in navigation click: {ex}")
                show_error("Navigation error occurred")
        
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
        try:
            for nav, page_name in [(nav_home, "home"), (nav_browse, "browse"), (nav_about, "about")]:
                is_active = page_name == active_page
                nav.bgcolor = ft.Colors.with_opacity(0.1, "#fbbf24") if is_active else None
                nav.content.controls[0].color = "#fbbf24" if is_active else "#64748b"
                nav.content.controls[1].color = "#fbbf24" if is_active else "#64748b"
                nav.content.controls[1].weight = ft.FontWeight.BOLD if is_active else ft.FontWeight.W_500
            page.update()
        except Exception as e:
            print(f"Error updating navigation: {e}")
    
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
        try:
            if error_container and error_container.content:
                error_container.content.controls[1].value = message
                error_container.visible = True
                page.update()
        except Exception as e:
            print(f"Error showing error message: {e}")
    
    def hide_error():
        try:
            error_container.visible = False
            page.update()
        except Exception as e:
            print(f"Error hiding error message: {e}")
    
    def update_quote_display(quote_data):
        try:
            loading_container.visible = False
            
            if quote_data.get("success") and quote_data.get("text"):
                hide_error()
                current_quote.update(quote_data)
                quote_text.value = f'"{quote_data["text"]}"'
                author_text.value = f"— {quote_data.get('author', 'Unknown')}"
                source_badge.content.controls[1].value = quote_data.get('source', 'Quote')
                source_badge.visible = True
                quote_text.visible = True
                author_text.visible = True
            else:
                quote_text.visible = False
                author_text.visible = False
                source_badge.visible = False
                show_error(quote_data.get("error", "Unable to load quote"))
            
            page.update()
        except Exception as e:
            print(f"Error updating quote display: {e}")
            loading_container.visible = False
            quote_text.visible = False
            author_text.visible = False
            source_badge.visible = False
            show_error("Error displaying quote")
            page.update()
    
    def fetch_quote(fetch_function, *args):
        try:
            hide_error()
            quote_text.visible = False
            author_text.visible = False
            source_badge.visible = False
            loading_container.visible = True
            page.update()
            
            quote_data = fetch_function(*args)
            update_quote_display(quote_data)
        except Exception as e:
            print(f"Error fetching quote: {e}")
            loading_container.visible = False
            show_error("Failed to fetch quote")
            page.update()
    
    def on_random_click(e):
        try:
            fetch_quote(get_random_quote)
        except Exception as ex:
            print(f"Error in random click handler: {ex}")
            show_error("Error loading random quote")
    
    def on_daily_click(e):
        try:
            # Check if we already have today's quote cached
            import datetime
            today = datetime.date.today().isoformat()
            
            if daily_quote_cache and daily_quote_date == today:
                # Show cached daily quote immediately
                update_quote_display(daily_quote_cache)
            else:
                # Fetch fresh daily quote
                fetch_quote(get_quote_of_day)
        except Exception as ex:
            print(f"Error in daily click handler: {ex}")
            fetch_quote(get_quote_of_day)
    
    def on_copy_click(e):
        try:
            if not current_quote.get("text"):
                show_error("No quote to copy")
                return
            
            full_text = f'{current_quote["text"]}\n— {current_quote.get("author", "Unknown")}'
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
        except Exception as ex:
            print(f"Error copying quote: {ex}")
            show_error("Failed to copy quote")
    
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
    
    # Action buttons with visual indicators
    def create_button(icon, label, on_click, is_primary=False, badge_text=None):
        button_content = ft.Column(
            [
                ft.Stack(
                    [
                        ft.Icon(
                            icon,
                            color="#0f172a" if is_primary else "#fbbf24",
                            size=24
                        ),
                        # Badge indicator
                        ft.Container(
                            content=ft.Text(
                                badge_text if badge_text else "",
                                size=8,
                                color="#fff",
                                weight=ft.FontWeight.BOLD
                            ),
                            bgcolor="#10b981",
                            border_radius=8,
                            padding=ft.padding.symmetric(horizontal=4, vertical=2),
                            right=-5,
                            top=-5,
                            visible=badge_text is not None
                        ) if badge_text else ft.Container(),
                    ],
                    width=24,
                    height=24,
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
        )
        
        return ft.Container(
            content=button_content,
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
    
    # Check if daily quote is available
    def has_daily_quote():
        import datetime
        today = datetime.date.today().isoformat()
        return daily_quote_cache and daily_quote_date == today
    
    button_random = create_button(ft.Icons.SHUFFLE_ROUNDED, "Random", on_random_click, False)
    button_daily = create_button(ft.Icons.TODAY_ROUNDED, "Daily", on_daily_click, True, "★")
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
            try:
                quote_text_val = quote_data.get("q", "")
                author_val = quote_data.get("a", "Unknown")
                
                if not quote_text_val:
                    return
                
                full_text = f'{quote_text_val}\n— {author_val}'
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
            except Exception as ex:
                print(f"Error copying quote from card: {ex}")
        
        # Alternate colors for variety
        colors = [
            ("#fbbf24", "#fef3c7"),  # amber
            ("#60a5fa", "#dbeafe"),  # blue
            ("#a78bfa", "#ede9fe"),  # violet
            ("#f472b6", "#fce7f3"),  # pink
            ("#34d399", "#d1fae5"),  # emerald
        ]
        primary_color, secondary_color = colors[index % len(colors)]
        
        quote_text_val = quote_data.get("q", "No quote available")
        author_val = quote_data.get("a", "Unknown")
        
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
                        f'"{quote_text_val}"',
                        size=15,
                        color="#f8fafc",
                        weight=ft.FontWeight.W_500,
                        selectable=True,
                    ),
                    ft.Container(height=8),
                    ft.Text(
                        f"— {author_val}",
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
        try:
            if not append:
                browse_quotes_list.controls.clear()
                browse_loading.visible = True
            else:
                # Remove the "Load More" button and attribution if they exist
                if len(browse_quotes_list.controls) >= 2:
                    browse_quotes_list.controls = browse_quotes_list.controls[:-2]
            
            page.update()
            
            result = get_browse_quotes()
            
            browse_loading.visible = False
            
            if result.get("success"):
                quotes = result.get("quotes", [])
                if not quotes:
                    raise ValueError("No quotes returned from API")
                
                start_index = len([c for c in browse_quotes_list.controls if isinstance(c, ft.Container)])
                
                for i, quote in enumerate(quotes):
                    try:
                        browse_quotes_list.controls.append(create_quote_card(quote, start_index + i))
                    except Exception as card_error:
                        print(f"Error creating quote card: {card_error}")
                        continue
                
                # Add "Load More" button
                def on_load_more(e):
                    try:
                        load_browse_quotes(append=True)
                    except Exception as ex:
                        print(f"Error loading more quotes: {ex}")
                        show_error("Failed to load more quotes")
                
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
                raise ValueError("Failed to fetch quotes")
            
            page.update()
        except Exception as e:
            print(f"Critical error in load_browse_quotes: {e}")
            browse_loading.visible = False
            browse_quotes_list.controls.clear()
            browse_quotes_list.controls.append(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Icon(ft.Icons.ERROR_OUTLINE, color="#fb923c", size=40),
                            ft.Container(height=12),
                            ft.Text(
                                "Unable to Load Quotes",
                                size=15,
                                color="#f8fafc",
                                weight=ft.FontWeight.BOLD,
                                text_align=ft.TextAlign.CENTER,
                            ),
                            ft.Container(height=8),
                            ft.Text(
                                "Please check your connection and try again",
                                size=13,
                                color="#94a3b8",
                                text_align=ft.TextAlign.CENTER,
                            ),
                            ft.Container(height=16),
                            ft.ElevatedButton(
                                "Retry",
                                icon=ft.Icons.REFRESH_ROUNDED,
                                on_click=lambda e: load_browse_quotes(),
                                bgcolor="#fbbf24",
                                color="#0f172a",
                            ),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=0
                    ),
                    padding=40,
                    alignment=ft.alignment.center,
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
                            "Version 2.1",
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
                                    ft.Text("• Offline quote support", size=13, color="#94a3b8"),
                                    ft.Text("• Smart error handling", size=13, color="#94a3b8"),
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
        try:
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
        except Exception as e:
            print(f"Critical error switching page: {e}")
            show_error(f"Navigation error: {str(e)[:50]}")
    
    # Main layout
    try:
        main_content = ft.Column(
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
        
        # Always add banner ad below the safe area
        page.add(
            ft.Column(
                [
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.Container(height=5),  # Top spacing for safe area
                                banner_ad_container,
                                ft.Container(height=5),  # Bottom spacing
                            ],
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            spacing=0,
                        ),
                        bgcolor=ft.Colors.with_opacity(0.3, "#0a0e1a"),
                        alignment=ft.alignment.center,
                    ),
                    ft.Divider(height=1, color=ft.Colors.with_opacity(0.1, "#475569")),
                    main_content
                ],
                spacing=0,
                expand=True
            )
        )
        
        # Load initial quote - prioritize daily quote on app start
        fetch_quote(get_quote_of_day)
    except Exception as e:
        print(f"Critical error initializing app: {e}")
        # Show error screen
        error_screen = ft.Container(
            content=ft.Column(
                [
                    ft.Icon(ft.Icons.ERROR_OUTLINE, color="#fb923c", size=64),
                    ft.Container(height=20),
                    ft.Text(
                        "App Initialization Failed",
                        size=20,
                        color="#f8fafc",
                        weight=ft.FontWeight.BOLD,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Container(height=12),
                    ft.Text(
                        "Please restart the application",
                        size=14,
                        color="#94a3b8",
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Container(height=8),
                    ft.Text(
                        f"Error: {str(e)[:100]}",
                        size=11,
                        color="#64748b",
                        text_align=ft.TextAlign.CENTER,
                        italic=True,
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            expand=True,
            alignment=ft.alignment.center,
            padding=40,
        )
        page.add(error_screen)


if __name__ == "__main__":
    ft.app(target=main)