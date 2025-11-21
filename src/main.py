"""
Quote Explorer - A modern inspirational quotes app built with Flet

Features:
- Daily featured quotes with smart caching
- Random inspirational quotes
- Browse extensive quote collection
- One-tap clipboard copy
- Create beautiful quote images with backgrounds
- Download generated images
- Event-driven banner ad loading (no threading/async)
- Comprehensive offline support
- Smart error handling and recovery
"""

import flet as ft
import requests
import time
import random
import base64
import io
import os
# Try to import PIL/Pillow
try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False
    print("Pillow not available. Install with: pip install Pillow")

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

# Enhanced Background themes for quote images with emojis
ENHANCED_BACKGROUND_THEMES = {
    "sunset": {
        "name": "Sunset",
        "colors": [(255, 94, 77), (245, 158, 11), (251, 191, 36)],
        "icon": ft.Icons.WB_SUNNY,
        "icon_emoji": "🌅",
        "description": "Warm orange to yellow gradient"
    },
    "ocean": {
        "name": "Ocean",
        "colors": [(14, 165, 233), (56, 189, 248), (125, 211, 252)],
        "icon": ft.Icons.WATER,
        "icon_emoji": "🌊",
        "description": "Deep blue to light blue gradient"
    },
    "forest": {
        "name": "Forest",
        "colors": [(34, 197, 94), (74, 222, 128), (134, 239, 172)],
        "icon": ft.Icons.FOREST,
        "icon_emoji": "🌲",
        "description": "Rich green gradient"
    },
    "night": {
        "name": "Night Sky",
        "colors": [(30, 27, 75), (67, 56, 202), (99, 102, 241)],
        "icon": ft.Icons.NIGHTLIGHT,
        "icon_emoji": "🌙",
        "description": "Deep purple to blue gradient"
    },
    "autumn": {
        "name": "Autumn",
        "colors": [(234, 88, 12), (251, 146, 60), (253, 186, 116)],
        "icon": ft.Icons.PARK,
        "icon_emoji": "🍂",
        "description": "Warm autumn colors"
    },
    "lavender": {
        "name": "Lavender",
        "colors": [(167, 139, 250), (196, 181, 253), (221, 214, 254)],
        "icon": ft.Icons.SPA,
        "icon_emoji": "💜",
        "description": "Soft purple gradient"
    },
    "space": {
        "name": "Space",
        "colors": [(17, 24, 39), (55, 65, 81), (107, 114, 128)],
        "icon": ft.Icons.ROCKET_LAUNCH,
        "icon_emoji": "🚀",
        "description": "Dark cosmic gradient"
    },
    "random": {
        "name": "Random Photo",
        "colors": None,
        "icon": ft.Icons.PHOTO_ROUNDED,
        "icon_emoji": "🎲",
        "description": "Random beautiful photo background"
    },
}


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

def get_random_background():
    """Load random background image without API"""
    try:
        # List of suitable Picsum IDs for quote backgrounds
        picsum_ids = [12, 13, 14, 15, 16, 17, 43, 58, 74, 76, 88, 89, 92, 93, 1036, 1037]
        chosen_id = random.choice(picsum_ids)

        url = f"https://picsum.photos/id/{chosen_id}/1080/1080?blur"
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        img = Image.open(io.BytesIO(resp.content)).convert("RGB")
        return img

    except Exception as e:
        print("Failed to load random background image:", e)
        return None

def create_quote_image(quote_text, author, theme_key="sunset"):
    width, height = 1080, 1080

    # If Random → use background image from internet
    if theme_key.lower() == "random":
        img = get_random_background()
        if img is None:
            return None
    else:
        # Old gradient backgrounds
        img = Image.new('RGB', (width, height))
        draw = ImageDraw.Draw(img)

        theme = ENHANCED_BACKGROUND_THEMES.get(theme_key, ENHANCED_BACKGROUND_THEMES["sunset"])
        colors = theme["colors"]

        for y in range(height):
            ratio = y / height
            if ratio < 0.5:
                blend = ratio * 2
                r = int(colors[0][0] * (1 - blend) + colors[1][0] * blend)
                g = int(colors[0][1] * (1 - blend) + colors[1][1] * blend)
                b = int(colors[0][2] * (1 - blend) + colors[1][2] * blend)
            else:
                blend = (ratio - 0.5) * 2
                r = int(colors[1][0] * (1 - blend) + colors[2][0] * blend)
                g = int(colors[1][1] * (1 - blend) + colors[2][1] * blend)
                b = int(colors[1][2] * (1 - blend) + colors[2][2] * blend)

            draw.line([(0, y), (width, y)], fill=(r, g, b))

    # ---- Text ----
    draw = ImageDraw.Draw(img)
    font_path = "src/assets/arial.ttf"
    if not os.path.isfile(font_path):
        font_path = "assets/arial.ttf"
    try:
        quote_font = ImageFont.truetype(font_path, 72)
        author_font = ImageFont.truetype(font_path, 52)
    except:
        quote_font = ImageFont.load_default()
        author_font = ImageFont.load_default()

    formatted_quote = f'"{quote_text}"'
    words = formatted_quote.split()
    lines, current_line = [], []
    max_width = width - 160

    for word in words:
        test = ' '.join(current_line + [word])
        w = draw.textbbox((0, 0), test, font=quote_font)[2]
        if w <= max_width:
            current_line.append(word)
        else:
            lines.append(' '.join(current_line))
            current_line = [word]
    if current_line:
        lines.append(' '.join(current_line))

    y = (height - (len(lines) * 95 + 200)) // 2

    for line in lines:
        w = draw.textbbox((0, 0), line, font=quote_font)[2]
        x = (width - w) // 2
        draw.text((x+3, y+3), line, font=quote_font, fill=(0,0,0))
        draw.text((x, y), line, font=quote_font, fill=(255,255,255))
        y += 95

    author_text = f"— {author}"
    w = draw.textbbox((0, 0), author_text, font=author_font)[2]
    x = (width - w) // 2
    draw.text((x+3, y+3), author_text, font=author_font, fill=(0,0,0))
    draw.text((x, y), author_text, font=author_font, fill=(255,255,255))

    # Base64 output
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


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
    
    # Banner ad state management
    global ad_loaded_successfully, ad_load_attempted
    ad_loaded_successfully = False
    ad_load_attempted = False
    
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
    
    # Banner ad state management - Simple event-driven approach
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
        content=create_ad_placeholder("Tap to load ad" if is_mobile and ADS_AVAILABLE else "Ad Space"),
        alignment=ft.alignment.center,
    )
    
    def try_load_banner_ad():
        """Try to load banner ad on every user interaction - No threading, pure event-driven"""
        global ad_loaded_successfully, ad_load_attempted
        
        # Skip if ad already loaded successfully
        if ad_loaded_successfully:
            return
        
        # Skip if ads not available or not mobile
        if not ADS_AVAILABLE or not is_mobile:
            return
        
        # Mark that we attempted to load
        ad_load_attempted = True
        print(f"Attempting to load banner ad... (attempt at {time.time()})")
        
        try:
            def on_ad_load(e):
                global ad_loaded_successfully
                print("✅ BannerAd loaded successfully! Will not reload.")
                ad_loaded_successfully = True
                try:
                    page.update()
                except Exception as update_error:
                    print(f"Error updating page after ad load: {update_error}")
            
            def on_ad_error(e):
                global ad_loaded_successfully
                if not ad_loaded_successfully:
                    error_msg = e.data if hasattr(e, 'data') else str(e)
                    print(f"❌ BannerAd error: {error_msg}")
                    print("   Will retry on next user interaction")
                    
                    # Update placeholder to inform user
                    try:
                        banner_ad_container.content = create_ad_placeholder("Tap anywhere to retry")
                        page.update()
                    except Exception as update_error:
                        print(f"Error updating placeholder: {update_error}")
            
            # Create new ad instance
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
            
            # Update container with new ad
            banner_ad_container.content = ft.Container(
                width=320,
                height=50,
                bgcolor=ft.Colors.TRANSPARENT,
                alignment=ft.alignment.center,
                content=new_ad,
            )
            page.update()
            
        except Exception as e:
            print(f"Exception creating banner ad: {e}")
            if not ad_loaded_successfully:
                try:
                    banner_ad_container.content = create_ad_placeholder("Tap anywhere to retry")
                    page.update()
                except Exception as update_error:
                    print(f"Error updating placeholder after exception: {update_error}")
    
    # Initial ad load attempt on app start
    if ADS_AVAILABLE and is_mobile:
        try_load_banner_ad()
    
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
                # Try to load ad on every interaction
                try_load_banner_ad()
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
                        size=24
                    ),
                    ft.Text(
                        label,
                        size=11,
                        color="#fbbf24" if is_active else "#64748b",
                        weight=ft.FontWeight.BOLD if is_active else ft.FontWeight.W_500
                    )
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=5
            ),
            padding=ft.padding.symmetric(horizontal=16, vertical=12),
            ink=True,
            on_click=on_nav_click,
            border_radius=14,
            bgcolor=ft.Colors.with_opacity(0.15, "#fbbf24") if is_active else None,
            animate=ft.Animation(250, ft.AnimationCurve.EASE_OUT),
        )
    
    nav_home = create_nav_button(ft.Icons.HOME_ROUNDED, "Home", "home", True)
    nav_browse = create_nav_button(ft.Icons.EXPLORE_ROUNDED, "Browse", "browse", False)
    nav_create = create_nav_button(ft.Icons.IMAGE_ROUNDED, "Create", "create", False)
    nav_about = create_nav_button(ft.Icons.INFO_ROUNDED, "About", "about", False)
    
    navbar = ft.Container(
        content=ft.Row(
            [nav_home, nav_browse, nav_create, nav_about],
            alignment=ft.MainAxisAlignment.SPACE_AROUND,
            spacing=0
        ),
        bgcolor=ft.Colors.with_opacity(0.98, "#1e293b"),
        padding=ft.padding.symmetric(vertical=10, horizontal=20),
        border=ft.border.only(top=ft.BorderSide(1.5, ft.Colors.with_opacity(0.3, "#475569"))),
        shadow=ft.BoxShadow(
            spread_radius=0,
            blur_radius=30,
            color=ft.Colors.with_opacity(0.5, ft.Colors.BLACK),
            offset=ft.Offset(0, -8)
        ),
    )
    
    def update_nav_active(active_page):
        try:
            for nav, page_name in [(nav_home, "home"), (nav_browse, "browse"), (nav_create, "create"), (nav_about, "about")]:
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
        size=18,
        color="#f8fafc",
        weight=ft.FontWeight.W_600,
        text_align=ft.TextAlign.CENTER,
        selectable=True,
        max_lines=None,
    )
    
    author_text = ft.Text(
        value="",
        size=14,
        color="#94a3b8",
        italic=True,
        text_align=ft.TextAlign.CENTER,
        selectable=True,
        weight=ft.FontWeight.W_600
    )
    
    source_badge = ft.Container(
        content=ft.Row(
            [
                ft.Icon(ft.Icons.AUTO_AWESOME_ROUNDED, size=16, color="#fbbf24"),
                ft.Text(
                    value="",
                    size=12,
                    color="#cbd5e1",
                    weight=ft.FontWeight.W_600,
                    text_align=ft.TextAlign.CENTER,
                )
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=8
        ),
        bgcolor="#1e293b",
        padding=ft.padding.symmetric(horizontal=18, vertical=8),
        border_radius=30,
        border=ft.border.all(1.5, "#334155"),
        shadow=ft.BoxShadow(
            spread_radius=0,
            blur_radius=10,
            color=ft.Colors.with_opacity(0.3, "#fbbf24"),
            offset=ft.Offset(0, 4)
        ),
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
                    color="#fcd34d",
                    expand=True,
                    text_align=ft.TextAlign.LEFT,
                    weight=ft.FontWeight.W_500
                )
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=8
        ),
        bgcolor=ft.Colors.with_opacity(0.1, "#fb923c"),
        border=ft.border.all(1, ft.Colors.with_opacity(0.3, "#fb923c")),
        padding=14,
        expand=True
    )
    
    def show_error(message):
        try:
            if error_container and error_container.content:
                error_container.content.controls[1].value = message
                error_container.visible=True
                snack_error = ft.SnackBar(
                    content=error_container,
                    bgcolor=ft.Colors.BLACK,
                    shape=None,
                    elevation=0,
                    margin=0,
                    padding=0,
                )
                page.open(snack_error)
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
            # Try to load ad on every interaction
            try_load_banner_ad()
            fetch_quote(get_random_quote)
        except Exception as ex:
            print(f"Error in random click handler: {ex}")
            show_error("Error loading random quote")
    
    def on_daily_click(e):
        try:
            # Try to load ad on every interaction
            try_load_banner_ad()
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
            # Try to load ad on every interaction
            try_load_banner_ad()
            if not current_quote.get("text"):
                show_error("No quote to copy")
                return
            
            # Format quote nicely with decorative elements
            quote_text_val = current_quote["text"]
            author = current_quote.get("author", "Unknown")
            
            # Create beautiful formatted text
            formatted_text = f'"{quote_text_val}"\n\n— {author}'
            
            page.set_clipboard(formatted_text)
            
            snackbar = ft.SnackBar(
                content=ft.Row(
                    [
                        ft.Icon(ft.Icons.CHECK_CIRCLE_ROUNDED, color="#10b981", size=20),
                        ft.Text("Quote Copied ", color="#fbbf24", size=14, weight=ft.FontWeight.W_500)
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
    
    def on_create_image_click(e):
        try:
            # Try to load ad on every interaction
            try_load_banner_ad()
            if not current_quote.get("text"):
                show_error("No quote available")
                return
            
            # Switch to create page
            switch_page("create")
            
            # Show success message
            snackbar = ft.SnackBar(
                content=ft.Row(
                    [
                        ft.Icon(ft.Icons.IMAGE_ROUNDED, color="#10b981", size=20),
                        ft.Text("Ready to create image!", color="#fbbf24", size=14, weight=ft.FontWeight.W_500)
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
            print(f"Error navigating to create: {ex}")
            show_error("Failed to navigate")
    
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
        padding=32,
        gradient=ft.LinearGradient(
            begin=ft.alignment.top_left,
            end=ft.alignment.bottom_right,
            colors=[
                ft.Colors.with_opacity(0.08, "#fbbf24"),
                ft.Colors.with_opacity(0.03, "#1e293b"),
                ft.Colors.with_opacity(0.05, "#60a5fa"),
            ]
        ),
        border=ft.border.all(1.5, ft.Colors.with_opacity(0.3, "#475569")),
        shadow=ft.BoxShadow(
            spread_radius=0,
            blur_radius=40,
            color=ft.Colors.with_opacity(0.4, ft.Colors.BLACK),
            offset=ft.Offset(0, 20)
        ),
        blur=ft.Blur(15, 15, ft.BlurTileMode.CLAMP),
        height=300,
    )
    
    # Action buttons with visual indicators
    def create_button(icon, label, on_click, is_primary=False, badge_text=None, gradient=False):
        button_content = ft.Column(
            [
                ft.Stack(
                    [
                        ft.Icon(
                            icon,
                            color="#0f172a" if is_primary else ("#fff" if gradient else "#fbbf24"),
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
                            padding=ft.padding.symmetric(horizontal=5, vertical=2),
                            right=-6,
                            top=-6,
                            visible=badge_text is not None
                        ) if badge_text else ft.Container(),
                    ],
                    width=24,
                    height=24,
                ),
                ft.Text(
                    label,
                    size=11,
                    color="#0f172a" if is_primary else ("#fff" if gradient else "#fbbf24"),
                    weight=ft.FontWeight.BOLD
                )
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=6
        )
        
        return ft.Container(
            content=button_content,
            bgcolor="#fbbf24" if is_primary and not gradient else (None if gradient else ft.Colors.with_opacity(0.05, "#1e293b")),
            gradient=ft.LinearGradient(
                begin=ft.alignment.top_left,
                end=ft.alignment.bottom_right,
                colors=["#a78bfa", "#ec4899", "#f59e0b"]
            ) if gradient else None,
            border=None if is_primary or gradient else ft.border.all(1.5, ft.Colors.with_opacity(0.6, "#fbbf24")),
            border_radius=14,
            padding=14,
            ink=True,
            on_click=on_click,
            expand=True,
            shadow=ft.BoxShadow(
                spread_radius=0,
                blur_radius=20 if (is_primary or gradient) else 8,
                color=ft.Colors.with_opacity(0.4 if (is_primary or gradient) else 0.2, "#fbbf24" if is_primary else "#a78bfa" if gradient else "#fbbf24"),
                offset=ft.Offset(0, 8 if (is_primary or gradient) else 4)
            ),
            animate=ft.Animation(200, ft.AnimationCurve.EASE_OUT),
        )
    
    button_random = create_button(ft.Icons.SHUFFLE_ROUNDED, "Random", on_random_click, False)
    button_daily = create_button(ft.Icons.TODAY_ROUNDED, "Daily", on_daily_click, True, "★")
    button_copy = create_button(ft.Icons.CONTENT_COPY_ROUNDED, "Copy", on_copy_click, False)
    button_create_img = create_button(ft.Icons.IMAGE_ROUNDED, "Create", on_create_image_click, False)
    
    # First row - Quote actions
    buttons_row_1 = ft.Row(
        [button_random, button_daily, button_copy, button_create_img],
        spacing=10,
        alignment=ft.MainAxisAlignment.CENTER
    )
    
    # Header
    header = ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Icon(ft.Icons.AUTO_STORIES_ROUNDED, size=40, color="#fbbf24", opacity=0.9),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
                ft.Container(height=8),
                ft.Text(
                    "Quote Explorer",
                    size=36,
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
                    padding=ft.padding.only(top=4)
                ),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=0
        ),
        padding=ft.padding.only(top=20, bottom=20, left=30, right=30)
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
                content=ft.Column(
                    [
                        ft.Container(
                            content=ft.Row(
                                [
                                    ft.Icon(ft.Icons.TOUCH_APP_ROUNDED, size=16, color="#fbbf24", opacity=0.8),
                                    ft.Text(
                                        "Quick Actions",
                                        size=14,
                                        weight=ft.FontWeight.BOLD,
                                        color="#94a3b8",
                                    ),
                                ],
                                spacing=6
                            ),
                            padding=ft.padding.only(bottom=12)
                        ),
                        buttons_row_1,
                        ft.Container(height=8),
                    ],
                    spacing=0
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
                # Try to load ad on every interaction
                try_load_banner_ad()
                
                quote_text_val = quote_data.get("q", "")
                author_val = quote_data.get("a", "Unknown")
                
                if not quote_text_val:
                    return
                
                # Format quote nicely with decorative elements
                formatted_text = f'"{quote_text_val}"\n\n— {author_val}'
                
                page.set_clipboard(formatted_text)
                
                snackbar = ft.SnackBar(
                    content=ft.Row(
                        [
                            ft.Icon(ft.Icons.CHECK_CIRCLE_ROUNDED, color="#10b981", size=18),
                            ft.Text("Copied beautifully!", color="#fbbf24", size=13, weight=ft.FontWeight.W_500)
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
        
        def create_image_from_card(e):
            try:
                # Try to load ad on every interaction
                try_load_banner_ad()
                
                quote_text_val = quote_data.get("q", "")
                author_val = quote_data.get("a", "Unknown")
                
                if not quote_text_val:
                    return
                
                # Update current quote and switch to create page
                current_quote["text"] = quote_text_val
                current_quote["author"] = author_val
                current_quote["source"] = "Browse Quote"
                
                # Switch to create page
                switch_page("create")
                
                # Show success message
                snackbar = ft.SnackBar(
                    content=ft.Row(
                        [
                            ft.Icon(ft.Icons.IMAGE_ROUNDED, color="#10b981", size=18),
                            ft.Text("Ready to create image!", color="#fbbf24", size=13, weight=ft.FontWeight.W_500)
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
                print(f"Error creating image from card: {ex}")
        
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
                            ft.Row(
                                [
                                    ft.IconButton(
                                        icon=ft.Icons.IMAGE_ROUNDED,
                                        icon_size=18,
                                        icon_color=ft.Colors.with_opacity(0.7, primary_color),
                                        on_click=create_image_from_card,
                                        tooltip="Create image"
                                    ),
                                    ft.IconButton(
                                        icon=ft.Icons.CONTENT_COPY,
                                        icon_size=18,
                                        icon_color=ft.Colors.with_opacity(0.6, "#94a3b8"),
                                        on_click=copy_quote,
                                        tooltip="Copy quote"
                                    ),
                                ],
                                spacing=0
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
            # Try to load ad on every interaction
            try_load_banner_ad()
            
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
                        # Try to load ad on every interaction
                        try_load_banner_ad()
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
                                on_click=lambda e: (try_load_banner_ad(), load_browse_quotes()),
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
    
    # =========================================================================
    # ENHANCED CREATE PAGE COMPONENTS
    # =========================================================================
    
# Enhanced Create Page Components - Simplified and Fixed
# Enhanced Create Page Components - Fixed Reference Order
    selected_theme = ft.Ref[ft.Text]()
    current_theme_key = "sunset"
    current_background_type = "gradient"
    preview_image = ft.Ref[ft.Image]()
    background_type_ref = ft.Ref[ft.Text]()

    # Store theme buttons for easy access
    theme_buttons = {}

    # Track if we have a valid quote for generation
    has_valid_quote = False

    # Define references FIRST before using them
    quote_text_ref = ft.Ref[ft.Text]()
    author_text_ref = ft.Ref[ft.Text]()

    # Status text for quote availability - Define this early
    quote_status_text = ft.Text(
        "ⓘ Get a quote from Home page first",
        size=12,
        color="#fbbf24",
        weight=ft.FontWeight.W_500,
        text_align=ft.TextAlign.CENTER,
    )

    # Current quote display - Define this early
    current_quote_display = ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Icon(ft.Icons.FORMAT_QUOTE_ROUNDED, size=16, color="#fbbf24"),
                        ft.Text(
                            "Current Quote",
                            size=14,
                            color="#f8fafc",
                            weight=ft.FontWeight.BOLD
                        )
                    ],
                    spacing=8
                ),
                ft.Container(height=12),
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text(
                                ref=quote_text_ref,
                                size=14,
                                color="#f8fafc",
                                weight=ft.FontWeight.W_500,
                                text_align=ft.TextAlign.CENTER,
                                selectable=True,
                            ),
                            ft.Container(height=6),
                            ft.Text(
                                ref=author_text_ref,
                                size=12,
                                color="#94a3b8",
                                italic=True,
                                text_align=ft.TextAlign.CENTER,
                                selectable=True,
                            ),
                        ],
                        spacing=0,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    padding=16,
                    bgcolor=ft.Colors.with_opacity(0.05, "#1e293b"),
                    border_radius=12,
                    border=ft.border.all(1, ft.Colors.with_opacity(0.2, "#475569")),
                ),
            ],
            spacing=0
        ),
        bgcolor=ft.Colors.with_opacity(0.02, "#1e293b"),
        border=ft.border.all(1, ft.Colors.with_opacity(0.1, "#334155")),
        border_radius=16,
        padding=20,
    )

    # Improved function to update current quote display
    def update_current_quote_display():
        global has_valid_quote
        try:
            if current_quote.get("text"):
                quote_text_ref.current.value = f'"{current_quote["text"]}"'
                author_text_ref.current.value = f"— {current_quote.get('author', 'Unknown')}"
                has_valid_quote = True
                
                # Enable generate button and show hint
                generate_btn_container.disabled = False
                quote_status_text.value = "✓ Ready to generate image"
                quote_status_text.color = "#10b981"
            else:
                quote_text_ref.current.value = "No quote selected"
                author_text_ref.current.value = "Go to Home page to get a quote"
                has_valid_quote = False
                
                # Disable generate button and show instruction
                generate_btn_container.disabled = True
                quote_status_text.value = "ⓘ Get a quote from Home page first"
                quote_status_text.color = "#fbbf24"
            
            if page_container.content == create_content:
                page.update()
        except Exception as e:
            print(f"Error updating quote display: {e}")

    # Background type selection handler
    def on_background_type_select(bg_type):
        def handler(e):
            nonlocal current_theme_key, current_background_type
            try:
                try_load_banner_ad()
                current_background_type = bg_type
                
                # Update button styles
                gradient_btn_container.border = ft.border.all(2, "#fbbf24" if bg_type == "gradient" else ft.Colors.with_opacity(0.3, "#475569"))
                gradient_btn_container.bgcolor = ft.Colors.with_opacity(0.15, "#fbbf24") if bg_type == "gradient" else ft.Colors.with_opacity(0.03, "#1e293b")
                gradient_btn_container.content.controls[0].color = "#fbbf24" if bg_type == "gradient" else "#64748b"
                gradient_btn_container.content.controls[1].color = "#fbbf24" if bg_type == "gradient" else "#64748b"
                
                photo_btn_container.border = ft.border.all(2, "#fbbf24" if bg_type == "photo" else ft.Colors.with_opacity(0.3, "#475569"))
                photo_btn_container.bgcolor = ft.Colors.with_opacity(0.15, "#fbbf24") if bg_type == "photo" else ft.Colors.with_opacity(0.03, "#1e293b")
                photo_btn_container.content.controls[0].color = "#fbbf24" if bg_type == "photo" else "#64748b"
                photo_btn_container.content.controls[1].color = "#fbbf24" if bg_type == "photo" else "#64748b"
                
                # Show/hide theme selection based on background type
                if bg_type == "photo":
                    current_theme_key = "random"
                    theme_selection_container.visible = False
                else:
                    current_theme_key = "sunset"
                    theme_selection_container.visible = True
                    update_theme_buttons_active_state()
                
                # Auto-generate if we have a valid quote
                if has_valid_quote:
                    generate_preview()
                
                page.update()
            except Exception as ex:
                print(f"Error selecting background type: {ex}")
        return handler

    # Theme selection handler
    def on_theme_select(theme_key):
        def handler(e):
            nonlocal current_theme_key
            try:
                try_load_banner_ad()
                current_theme_key = theme_key
                update_theme_buttons_active_state()
                
                # Auto-generate if we have a valid quote
                if has_valid_quote:
                    generate_preview()
                
                page.update()
            except Exception as ex:
                print(f"Error selecting theme: {ex}")
        return handler

    # Function to update theme buttons active state
    def update_theme_buttons_active_state():
        """Update the visual state of all theme buttons"""
        try:
            for theme_key, button in theme_buttons.items():
                is_active = theme_key == current_theme_key
                button.border = ft.border.all(2, "#fbbf24" if is_active else ft.Colors.with_opacity(0.3, "#475569"))
                button.bgcolor = ft.Colors.with_opacity(0.15, "#fbbf24") if is_active else ft.Colors.with_opacity(0.03, "#1e293b")
                
                if hasattr(button.content, 'controls') and len(button.content.controls) >= 2:
                    button.content.controls[0].color = "#fbbf24" if is_active else "#64748b"
                    button.content.controls[1].color = "#fbbf24" if is_active else "#64748b"
        except Exception as e:
            print(f"Error updating theme buttons: {e}")

    # Improved generate preview function with better logic
    def generate_preview():
        try:
            if not PILLOW_AVAILABLE:
                show_error("Pillow library not available. Install with: pip install Pillow")
                return
            
            if not current_quote.get("text"):
                show_error("No quote available. Please get a quote first from the Home page.")
                return
            
            # Show loading state
            create_loading.visible = True
            generating_text.visible = True
            preview_placeholder.visible = False
            if preview_image.current:
                preview_image.current.visible = False
            if download_button_ref.current:
                download_button_ref.current.visible = False
            generate_btn_container.disabled = True
            page.update()
            
            # Generate image
            img_base64 = create_quote_image(
                current_quote["text"],
                current_quote.get("author", "Unknown"),
                current_theme_key
            )
            
            create_loading.visible = False
            generating_text.visible = False
            generate_btn_container.disabled = False
            
            if img_base64 and preview_image.current:
                preview_image.current.src_base64 = img_base64
                preview_image.current.visible = True
                preview_placeholder.visible = False
                if download_button_ref.current:
                    download_button_ref.current.visible = True
                
                # Show success message
                snackbar = ft.SnackBar(
                    content=ft.Row(
                        [
                            ft.Icon(ft.Icons.CHECK_CIRCLE_ROUNDED, color="#10b981", size=20),
                            ft.Text("Image generated successfully!", color="#fbbf24", size=14, weight=ft.FontWeight.W_500)
                        ],
                        spacing=8
                    ),
                    bgcolor="#1e293b",
                    duration=2000,
                )
                page.overlay.append(snackbar)
                snackbar.open = True
            else:
                show_error("Failed to generate image. Please check your internet connection.")
                preview_placeholder.visible = True
            
            page.update()
        except Exception as e:
            print(f"Error generating preview: {e}")
            create_loading.visible = False
            generating_text.visible = False
            generate_btn_container.disabled = False
            preview_placeholder.visible = True
            show_error("Error generating image preview")
            page.update()

    # Generate button handler with improved logic
    def on_generate_click(e):
        try:
            try_load_banner_ad()
            
            # If no quote available, show helpful message
            if not current_quote.get("text"):
                show_error("No quote available. Please:\n1. Go to Home page\n2. Get a Daily or Random quote\n3. Return here to create an image")
                return
            
            generate_preview()
        except Exception as ex:
            print(f"Error in generate click: {ex}")

    # Download button handler
    def on_download_click(e):
        try:
            try_load_banner_ad()
            if not preview_image.current or not preview_image.current.src_base64:
                show_error("Please generate an image first")
                return
            
            # Show downloading state
            download_button_ref.current.content = ft.Row(
                [
                    ft.ProgressRing(width=16, height=16, stroke_width=2, color="#10b981"),
                    ft.Text("Downloading...", size=14, color="#10b981", weight=ft.FontWeight.BOLD)
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=8
            )
            page.update()
            
            # Get the base64 image data
            img_base64 = preview_image.current.src_base64
            import base64
            import datetime
            img_bytes = base64.b64decode(img_base64)
            
            # Create filename with timestamp
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"inspirational_quote_{timestamp}.png"
            
            # Save the image
            def save_result(e: ft.FilePickerResultEvent):
                # Reset download button
                download_button_ref.current.content = ft.Row(
                    [
                        ft.Icon(ft.Icons.DOWNLOAD_ROUNDED, color="#10b981", size=20),
                        ft.Text("Download Image", size=14, color="#10b981", weight=ft.FontWeight.BOLD)
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=8
                )
                
                if e.path:
                    try:
                        save_path = e.path if e.path.endswith('.png') else f"{e.path}.png"
                        with open(save_path, 'wb') as f:
                            f.write(img_bytes)
                        
                        snackbar = ft.SnackBar(
                            content=ft.Row(
                                [
                                    ft.Icon(ft.Icons.DOWNLOAD_DONE_ROUNDED, color="#10b981", size=20),
                                    ft.Text("Image saved successfully!", color="#fbbf24", size=14, weight=ft.FontWeight.W_500)
                                ],
                                spacing=8
                            ),
                            bgcolor="#1e293b",
                            duration=3000,
                        )
                        page.overlay.append(snackbar)
                        snackbar.open = True
                    except Exception as ex:
                        print(f"Error saving file: {ex}")
                        show_error("Failed to save image")
                page.update()
            
            file_picker = ft.FilePicker(on_result=save_result)
            page.overlay.append(file_picker)
            file_picker.save_file(file_name=filename, allowed_extensions=["png"])
            
        except Exception as ex:
            print(f"Error downloading image: {ex}")
            show_error(f"Download error: {str(ex)[:50]}")
            
            # Reset download button on error
            if download_button_ref.current:
                download_button_ref.current.content = ft.Row(
                    [
                        ft.Icon(ft.Icons.DOWNLOAD_ROUNDED, color="#10b981", size=20),
                        ft.Text("Download Image", size=14, color="#10b981", weight=ft.FontWeight.BOLD)
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=8
                )
                page.update()

    # Loading indicator
    create_loading = ft.Container(
        content=ft.Column(
            [
                ft.ProgressRing(
                    color="#fbbf24",
                    width=40,
                    height=40,
                    stroke_width=3
                ),
                ft.Container(height=8),
                ft.Text(
                    "Creating your image...",
                    size=12,
                    color="#64748b",
                    weight=ft.FontWeight.W_500
                )
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=0
        ),
        visible=False,
        alignment=ft.alignment.center
    )

    generating_text = ft.Text(
        "This may take a few seconds",
        size=11,
        color="#64748b",
        weight=ft.FontWeight.W_400,
        visible=False
    )

    # Background type selection buttons
    gradient_btn_container = ft.Container(
        content=ft.Column(
            [
                ft.Icon(ft.Icons.GRADIENT_ROUNDED, size=24, color="#fbbf24"),
                ft.Text("Gradient", size=11, color="#fbbf24", weight=ft.FontWeight.BOLD)
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=6
        ),
        border=ft.border.all(2, "#fbbf24"),
        bgcolor=ft.Colors.with_opacity(0.15, "#fbbf24"),
        border_radius=12,
        padding=14,
        ink=True,
        on_click=on_background_type_select("gradient"),
    )

    photo_btn_container = ft.Container(
        content=ft.Column(
            [
                ft.Icon(ft.Icons.PHOTO_ROUNDED, size=24, color="#64748b"),
                ft.Text("Photo", size=11, color="#64748b", weight=ft.FontWeight.BOLD)
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=6
        ),
        border=ft.border.all(1.5, ft.Colors.with_opacity(0.3, "#475569")),
        bgcolor=ft.Colors.with_opacity(0.03, "#1e293b"),
        border_radius=12,
        padding=14,
        ink=True,
        on_click=on_background_type_select("photo"),
    )

    # Theme selection grid
    def create_theme_button(theme_key, theme_data):
        is_active = theme_key == current_theme_key
        button = ft.Container(
            content=ft.Column(
                [
                    ft.Text(
                        theme_data["icon_emoji"],
                        size=20,
                        color="#fbbf24" if is_active else "#64748b"
                    ),
                    ft.Text(
                        theme_data["name"],
                        size=10,
                        color="#fbbf24" if is_active else "#64748b",
                        weight=ft.FontWeight.BOLD,
                        text_align=ft.TextAlign.CENTER
                    )
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=6
            ),
            bgcolor=ft.Colors.with_opacity(0.15, "#fbbf24") if is_active else ft.Colors.with_opacity(0.03, "#1e293b"),
            border=ft.border.all(2, "#fbbf24" if is_active else ft.Colors.with_opacity(0.3, "#475569")),
            border_radius=10,
            padding=12,
            ink=True,
            on_click=on_theme_select(theme_key),
            tooltip=theme_data["description"]
        )
        
        theme_buttons[theme_key] = button
        return button

    # Create theme buttons
    theme_buttons_list = [create_theme_button(key, theme) for key, theme in ENHANCED_BACKGROUND_THEMES.items() if key != "random"]

    theme_selection_container = ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Icon(ft.Icons.PALETTE_ROUNDED, size=16, color="#fbbf24"),
                        ft.Text(
                            "Choose Theme",
                            size=14,
                            color="#f8fafc",
                            weight=ft.FontWeight.BOLD
                        )
                    ],
                    spacing=8
                ),
                ft.Container(height=12),
                ft.GridView(
                    theme_buttons_list,
                    runs_count=3,
                    spacing=8,
                    run_spacing=8,
                    max_extent=80,
                )
            ],
            spacing=0
        ),
        visible=True
    )

    # Preview section
    preview_placeholder = ft.Container(
        content=ft.Column(
            [
                ft.Icon(ft.Icons.IMAGE_ROUNDED, size=48, color=ft.Colors.with_opacity(0.3, "#64748b")),
                ft.Container(height=12),
                ft.Text(
                    "Image Preview",
                    size=14,
                    color="#64748b",
                    weight=ft.FontWeight.W_500,
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.Container(height=6),
                ft.Text(
                    "Generate an image to see preview",
                    size=12,
                    color="#64748b",
                    text_align=ft.TextAlign.CENTER,
                ),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
        ),
        alignment=ft.alignment.center,
        height=250,
        bgcolor=ft.Colors.with_opacity(0.03, "#1e293b"),
        border=ft.border.all(1, ft.Colors.with_opacity(0.2, "#475569")),
        border_radius=12,
    )

    preview_image_container = ft.Container(
        content=ft.Stack(
            [
                preview_placeholder,
                ft.Image(
                    ref=preview_image,
                    width=280,
                    height=250,
                    fit=ft.ImageFit.CONTAIN,
                    border_radius=12,
                    visible=False,
                ),
                create_loading,
            ]
        ),
        alignment=ft.alignment.center,
        height=250,
    )

    # Generate button - now dynamically enabled/disabled
    generate_btn_container = ft.Container(
        content=ft.Row(
            [
                ft.Icon(ft.Icons.AUTO_AWESOME_ROUNDED, color="#fbbf24", size=20),
                ft.Text(
                    "Generate Image",
                    size=14,
                    color="#fbbf24",
                    weight=ft.FontWeight.BOLD
                )
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=8
        ),
        bgcolor=ft.Colors.with_opacity(0.1, "#fbbf24"),
        border=ft.border.all(1.5, ft.Colors.with_opacity(0.6, "#fbbf24")),
        border_radius=12,
        padding=16,
        ink=True,
        on_click=on_generate_click,
        disabled=True,  # Initially disabled until we have a quote
    )

    # Download button
    download_button_ref = ft.Ref[ft.Container]()
    download_button = ft.Container(
        ref=download_button_ref,
        content=ft.Row(
            [
                ft.Icon(ft.Icons.DOWNLOAD_ROUNDED, color="#10b981", size=20),
                ft.Text(
                    "Download Image",
                    size=14,
                    color="#10b981",
                    weight=ft.FontWeight.BOLD
                )
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=8
        ),
        bgcolor=ft.Colors.with_opacity(0.1, "#10b981"),
        border=ft.border.all(1.5, ft.Colors.with_opacity(0.6, "#10b981")),
        border_radius=12,
        padding=16,
        ink=True,
        on_click=on_download_click,
        visible=False,
    )

    # Improved create page content
    create_content = ft.Column(
        [
            ft.Container(
                content=ft.Column(
                    [
                        ft.Row(
                            [
                                ft.Icon(ft.Icons.IMAGE_ROUNDED, size=28, color="#fbbf24"),
                                ft.Text(
                                    "Create Quote Image",
                                    size=24,
                                    weight=ft.FontWeight.BOLD,
                                    color="#f8fafc",
                                ),
                            ],
                            spacing=12,
                            alignment=ft.MainAxisAlignment.CENTER,
                        ),
                        ft.Container(height=4),
                        ft.Text(
                            "Transform quotes into beautiful images",
                            size=13,
                            color="#64748b",
                            text_align=ft.TextAlign.CENTER,
                        ),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=0
                ),
                padding=ft.padding.only(top=20, bottom=16, left=30, right=30)
            ),
            
            # Current Quote Section
            ft.Container(
                content=current_quote_display,
                padding=ft.padding.symmetric(horizontal=20)
            ),
            ft.Container(height=8),
            
            # Quote status indicator
            ft.Container(
                content=quote_status_text,
                padding=ft.padding.symmetric(horizontal=20),
                alignment=ft.alignment.center,
            ),
            ft.Container(height=16),
            
            # Background Type Selection
            ft.Container(
                content=ft.Column(
                    [
                        ft.Text(
                            "Background Style",
                            size=14,
                            color="#f8fafc",
                            weight=ft.FontWeight.BOLD,
                            text_align=ft.TextAlign.CENTER
                        ),
                        ft.Container(height=12),
                        ft.Row(
                            [gradient_btn_container, photo_btn_container],
                            spacing=12,
                            alignment=ft.MainAxisAlignment.CENTER
                        ),
                    ],
                    spacing=0
                ),
                padding=ft.padding.symmetric(horizontal=20)
            ),
            ft.Container(height=16),
            
            # Theme Selection
            ft.Container(
                content=theme_selection_container,
                padding=ft.padding.symmetric(horizontal=20)
            ),
            ft.Container(height=16),
            
            # Generate Button with status
            ft.Container(
                content=ft.Column(
                    [
                        generate_btn_container,
                        ft.Container(height=8),
                        generating_text,
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=0
                ),
                padding=ft.padding.symmetric(horizontal=20)
            ),
            ft.Container(height=16),
            
            # Preview Area
            ft.Container(
                content=ft.Column(
                    [
                        ft.Text(
                            "Preview",
                            size=14,
                            color="#f8fafc",
                            weight=ft.FontWeight.BOLD,
                            text_align=ft.TextAlign.CENTER
                        ),
                        ft.Container(height=12),
                        preview_image_container,
                        ft.Container(height=12),
                        download_button,
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=0
                ),
                padding=ft.padding.symmetric(horizontal=20)
            ),
            ft.Container(height=20),
        ],
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        spacing=0,
        scroll=ft.ScrollMode.ADAPTIVE,
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
                            "Version 3.0",
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
                                    ft.Text("• Create beautiful quote images", size=13, color="#94a3b8"),
                                    ft.Text("• 8 stunning background themes", size=13, color="#94a3b8"),
                                    ft.Text("• Download generated images", size=13, color="#94a3b8"),
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
        """Switch between pages with ad retry on every navigation"""
        try:
            # Try to load ad when switching pages
            try_load_banner_ad()
            
            if page_name == "home":
                page_container.content = home_content
                update_nav_active("home")
            elif page_name == "browse":
                page_container.content = browse_content
                update_nav_active("browse")
                load_browse_quotes()
            elif page_name == "create":
                page_container.content = create_content
                update_nav_active("create")
                update_current_quote_display()
            elif page_name == "about":
                page_container.content = about_content
                update_nav_active("about")
            page.update()
        except Exception as e:
            print(f"Critical error switching page: {e}")
            show_error(f"Navigation error: {str(e)[:50]}")
    
    # Enhanced update quote display to handle create page
    original_update_quote_display = update_quote_display
    
    def enhanced_update_quote_display(quote_data):
        """Enhanced update quote display that also updates create page"""
        original_update_quote_display(quote_data)
        update_current_quote_display()
    
    update_quote_display = enhanced_update_quote_display
    
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
        
        # Initialize the quote display
        update_current_quote_display()
        
        # Load initial quote - prioritize daily quote on app start
        try_load_banner_ad()  # Try to load ad
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
    ft.app(target=main, assets_dir="assets")