# import flet as ft
# import requests
# import time
# import random


# # Rate limiting and caching
# last_request_time = 0
# request_delay = 5.0
# quote_cache = []
# cache_index = 0
# daily_quote_cache = None
# daily_quote_date = None

# OFFLINE_QUOTES = [
#     {"q": "The only way to do great work is to love what you do.", "a": "Steve Jobs"},
#     {"q": "Innovation distinguishes between a leader and a follower.", "a": "Steve Jobs"},
#     {"q": "Life is what happens when you're busy making other plans.", "a": "John Lennon"},
#     {"q": "The future belongs to those who believe in the beauty of their dreams.", "a": "Eleanor Roosevelt"},
#     {"q": "It is during our darkest moments that we must focus to see the light.", "a": "Aristotle"},
#     {"q": "The only impossible journey is the one you never begin.", "a": "Tony Robbins"},
#     {"q": "In the middle of difficulty lies opportunity.", "a": "Albert Einstein"},
#     {"q": "Success is not final, failure is not fatal: it is the courage to continue that counts.", "a": "Winston Churchill"},
#     {"q": "Believe you can and you're halfway there.", "a": "Theodore Roosevelt"},
#     {"q": "The best time to plant a tree was 20 years ago. The second best time is now.", "a": "Chinese Proverb"},
#     {"q": "Your time is limited, don't waste it living someone else's life.", "a": "Steve Jobs"},
#     {"q": "The way to get started is to quit talking and begin doing.", "a": "Walt Disney"},
#     {"q": "Don't watch the clock; do what it does. Keep going.", "a": "Sam Levenson"},
#     {"q": "The future depends on what you do today.", "a": "Mahatma Gandhi"},
#     {"q": "Everything you've ever wanted is on the other side of fear.", "a": "George Addair"},
#     {"q": "Believe in yourself. You are braver than you think.", "a": "Unknown"},
#     {"q": "What we think, we become.", "a": "Buddha"},
#     {"q": "The journey of a thousand miles begins with one step.", "a": "Lao Tzu"},
#     {"q": "Life is 10% what happens to you and 90% how you react to it.", "a": "Charles R. Swindoll"},
#     {"q": "Change your thoughts and you change your world.", "a": "Norman Vincent Peale"},
# ]


# def can_make_request():
#     global last_request_time
#     current_time = time.time()
#     time_since_last = current_time - last_request_time
    
#     if time_since_last < request_delay:
#         return False, request_delay - time_since_last
#     return True, 0


# def safe_api_request(url, timeout=8):
#     global last_request_time
    
#     can_request, wait_time = can_make_request()
    
#     if not can_request:
#         print(f"Rate limited: waiting {wait_time:.1f}s before next request")
#         return None
    
#     try:
#         response = requests.get(url, timeout=timeout)
#         last_request_time = time.time()
        
#         if response.status_code == 429:
#             print("Rate limit hit (429), using cache/offline quotes")
#             return None
        
#         response.raise_for_status()
#         return response
#     except Exception as e:
#         print(f"API request failed: {e}")
#         return None


# def get_random_quote():
#     global quote_cache, cache_index
    
#     if quote_cache and cache_index < len(quote_cache):
#         quote = quote_cache[cache_index]
#         cache_index += 1
#         return {
#             "text": quote['q'],
#             "author": quote['a'],
#             "source": "Random Quote",
#             "success": True
#         }
    
#     response = safe_api_request("https://zenquotes.io/api/quotes")
    
#     if response:
#         try:
#             data = response.json()
#             if data and isinstance(data, list):
#                 quote_cache = data
#                 cache_index = 0
#                 quote = random.choice(data)
#                 return {
#                     "text": quote['q'],
#                     "author": quote['a'],
#                     "source": "Random Quote",
#                     "success": True
#                 }
#         except Exception as e:
#             print(f"Failed to parse response: {e}")
    
#     quote = random.choice(OFFLINE_QUOTES)
#     return {
#         "text": quote['q'],
#         "author": quote['a'],
#         "source": "Offline Quote",
#         "success": True
#     }


# def get_quote_of_day():
#     global daily_quote_cache, daily_quote_date
    
#     import datetime
#     today = datetime.date.today().isoformat()
    
#     if daily_quote_cache and daily_quote_date == today:
#         return daily_quote_cache
    
#     response = safe_api_request("https://zenquotes.io/api/today")
    
#     if response:
#         try:
#             data = response.json()
#             if data and isinstance(data, list):
#                 result = {
#                     "text": data[0]['q'],
#                     "author": data[0]['a'],
#                     "source": "✨ Quote of the Day",
#                     "success": True
#                 }
#                 daily_quote_cache = result
#                 daily_quote_date = today
#                 return result
#         except Exception as e:
#             print(f"Failed to parse daily quote: {e}")
    
#     return get_random_quote()


# def main(page: ft.Page):
#     page.title = "Quote Explorer"
#     page.theme_mode = ft.ThemeMode.DARK
#     page.window.width = 580
#     page.window.height = 780
#     page.padding = 0
#     page.bgcolor = "#0a0e1a"
    
#     current_quote = {"text": "", "author": "", "source": ""}
    
#     # Animated decorative elements
#     deco_circle_1 = ft.Container(
#         width=400,
#         height=400,
#         border_radius=200,
#         bgcolor=ft.Colors.with_opacity(0.03, "#fbbf24"),
#         blur=ft.Blur(50, 50, ft.BlurTileMode.CLAMP),
#     )
    
#     deco_circle_2 = ft.Container(
#         width=300,
#         height=300,
#         border_radius=150,
#         bgcolor=ft.Colors.with_opacity(0.02, "#60a5fa"),
#         blur=ft.Blur(40, 40, ft.BlurTileMode.CLAMP),
#     )
    
#     # UI Components with enhanced styling
#     quote_icon = ft.Icon(
#         ft.Icons.FORMAT_QUOTE_ROUNDED,
#         size=56,
#         color="#fbbf24",
#         opacity=0.15
#     )
    
#     quote_text = ft.Text(
#         value="",
#         size=26,
#         color="#f8fafc",
#         weight=ft.FontWeight.W_500,
#         text_align=ft.TextAlign.CENTER,
#         selectable=True,
#         max_lines=None,
#         font_family="SF Pro Display"
#     )
    
#     author_text = ft.Text(
#         value="",
#         size=17,
#         color="#94a3b8",
#         italic=True,
#         text_align=ft.TextAlign.CENTER,
#         selectable=True,
#         weight=ft.FontWeight.W_500
#     )
    
#     source_badge = ft.Container(
#         content=ft.Row(
#             [
#                 ft.Icon(ft.Icons.AUTO_AWESOME_ROUNDED, size=14, color="#fbbf24"),
#                 ft.Text(
#                     value="",
#                     size=11,
#                     color="#cbd5e1",
#                     weight=ft.FontWeight.W_600,
#                     text_align=ft.TextAlign.CENTER,
#                 )
#             ],
#             alignment=ft.MainAxisAlignment.CENTER,
#             spacing=6
#         ),
#         bgcolor="#1e293b",
#         padding=ft.padding.symmetric(horizontal=16, vertical=7),
#         border_radius=25,
#         border=ft.border.all(1, "#334155"),
#         visible=False
#     )
    
#     loading_ring = ft.ProgressRing(
#         color="#fbbf24",
#         width=50,
#         height=50,
#         stroke_width=3.5
#     )
    
#     loading_container = ft.Container(
#         content=ft.Column(
#             [
#                 loading_ring,
#                 ft.Text(
#                     "Fetching inspiration...",
#                     size=13,
#                     color="#64748b",
#                     text_align=ft.TextAlign.CENTER,
#                     weight=ft.FontWeight.W_500
#                 )
#             ],
#             horizontal_alignment=ft.CrossAxisAlignment.CENTER,
#             spacing=16
#         ),
#         visible=False
#     )
    
#     error_container = ft.Container(
#         content=ft.Row(
#             [
#                 ft.Icon(ft.Icons.ERROR_OUTLINE_ROUNDED, color="#fb923c", size=18),
#                 ft.Text(
#                     value="",
#                     size=12,
#                     color="#fcd34d",
#                     expand=True,
#                     text_align=ft.TextAlign.CENTER,
#                     weight=ft.FontWeight.W_500
#                 )
#             ],
#             alignment=ft.MainAxisAlignment.CENTER,
#             spacing=8
#         ),
#         bgcolor=ft.Colors.with_opacity(0.1, "#fb923c"),
#         border=ft.border.all(1, ft.Colors.with_opacity(0.3, "#fb923c")),
#         padding=14,
#         border_radius=12,
#         visible=False
#     )
    
#     def show_error(message):
#         error_container.content.controls[1].value = message
#         error_container.visible = True
#         page.update()
    
#     def hide_error():
#         error_container.visible = False
#         page.update()
    
#     def update_quote_display(quote_data):
#         loading_container.visible = False
        
#         if quote_data.get("success"):
#             hide_error()
#             current_quote.update(quote_data)
#             quote_text.value = f'"{quote_data["text"]}"'
#             author_text.value = f"— {quote_data['author']}"
#             source_badge.content.controls[1].value = quote_data.get('source', '')
#             source_badge.visible = True
#             quote_text.visible = True
#             author_text.visible = True
#         else:
#             quote_text.visible = False
#             author_text.visible = False
#             source_badge.visible = False
#             show_error(quote_data.get("error", "Unable to load quote"))
        
#         page.update()
    
#     def fetch_quote(fetch_function, *args):
#         hide_error()
#         quote_text.visible = False
#         author_text.visible = False
#         source_badge.visible = False
#         loading_container.visible = True
#         page.update()
        
#         quote_data = fetch_function(*args)
#         update_quote_display(quote_data)
    
#     def on_random_click(e):
#         fetch_quote(get_random_quote)
    
#     def on_daily_click(e):
#         fetch_quote(get_quote_of_day)
    
#     def on_copy_click(e):
#         if not current_quote.get("text"):
#             show_error("⚠️ No quote to copy")
#             return
        
#         full_text = f'{current_quote["text"]}\n— {current_quote["author"]}'
#         page.set_clipboard(full_text)
        
#         snackbar = ft.SnackBar(
#             content=ft.Row(
#                 [
#                     ft.Icon(ft.Icons.CHECK_CIRCLE_ROUNDED, color="#10b981", size=20),
#                     ft.Text("Quote copied!", color=ft.Colors.ORANGE, size=14, weight=ft.FontWeight.W_500)
#                 ],
#                 spacing=8
#             ),
#             bgcolor="#1e293b",
#             duration=2000,
#             behavior=ft.SnackBarBehavior.FLOATING,
#         )
#         page.overlay.append(snackbar)
#         snackbar.open = True
#         page.update()
    

    
#     # Quote display container with glassmorphism and scroll support
#     quote_content = ft.Column(
#         [
#             quote_icon,
#             ft.Container(height=8),
#             quote_text,
#             ft.Container(height=12),
#             author_text,
#             ft.Container(height=8),
#             loading_container,
#             source_badge,
#         ],
#         horizontal_alignment=ft.CrossAxisAlignment.CENTER,
#         alignment=ft.MainAxisAlignment.CENTER,
#         spacing=0,
#         scroll=ft.ScrollMode.ADAPTIVE,
#     )
    
#     quote_container = ft.Container(
#         content=quote_content,
#         border_radius=24,
#         bgcolor=ft.Colors.with_opacity(0.9, "#1e293b"),
#         padding=40,
#         gradient=ft.LinearGradient(
#             begin=ft.alignment.top_left,
#             end=ft.alignment.bottom_right,
#             colors=[
#                 ft.Colors.with_opacity(0.05, "#fbbf24"),
#                 ft.Colors.with_opacity(0.02, "#1e293b")
#             ]
#         ),
#         border=ft.border.all(1, ft.Colors.with_opacity(0.2, "#475569")),
#         shadow=ft.BoxShadow(
#             spread_radius=0,
#             blur_radius=30,
#             color=ft.Colors.with_opacity(0.3, ft.Colors.BLACK),
#             offset=ft.Offset(0, 15)
#         ),
#         blur=ft.Blur(10, 10, ft.BlurTileMode.CLAMP),
#         height=420,
#     )
    
#     # Enhanced action buttons
#     def create_button(icon, label, on_click, is_primary=False):
#         return ft.Container(
#             content=ft.Column(
#                 [
#                     ft.Icon(
#                         icon,
#                         color="#0f172a" if is_primary else "#fbbf24",
#                         size=26
#                     ),
#                     ft.Text(
#                         label,
#                         size=12,
#                         color="#0f172a" if is_primary else "#fbbf24",
#                         weight=ft.FontWeight.BOLD
#                     )
#                 ],
#                 horizontal_alignment=ft.CrossAxisAlignment.CENTER,
#                 spacing=8
#             ),
#             bgcolor="#fbbf24" if is_primary else ft.Colors.with_opacity(0.05, "#1e293b"),
#             border=None if is_primary else ft.border.all(1.5, ft.Colors.with_opacity(0.6, "#fbbf24")),
#             border_radius=16,
#             padding=20,
#             ink=True,
#             on_click=on_click,
#             expand=True,
#             shadow=ft.BoxShadow(
#                 spread_radius=0,
#                 blur_radius=15 if is_primary else 8,
#                 color=ft.Colors.with_opacity(0.35 if is_primary else 0.2, "#fbbf24"),
#                 offset=ft.Offset(0, 6)
#             ) if is_primary else None,
#             animate=ft.Animation(150, ft.AnimationCurve.EASE_OUT),
#         )
    
#     button_random = create_button(ft.Icons.SHUFFLE_ROUNDED, "Random", on_random_click, True)
#     button_daily = create_button(ft.Icons.TODAY_ROUNDED, "Daily", on_daily_click, False)
#     button_copy = create_button(ft.Icons.CONTENT_COPY_ROUNDED, "Copy", on_copy_click, False)
    
#     buttons_row = ft.Row(
#         [button_random, button_daily, button_copy],
#         spacing=12,
#         alignment=ft.MainAxisAlignment.CENTER
#     )
    
#     # Header with better typography
#     header = ft.Container(
#         content=ft.Column(
#             [
#                 ft.Text(
#                     "Quote Explorer",
#                     size=42,
#                     weight=ft.FontWeight.BOLD,
#                     color="#f8fafc",
#                     text_align=ft.TextAlign.CENTER,
#                 ),
#                 ft.Container(
#                     content=ft.Text(
#                         "Daily inspiration at your fingertips",
#                         size=14,
#                         color="#64748b",
#                         text_align=ft.TextAlign.CENTER,
#                         weight=ft.FontWeight.W_500
#                     ),
#                     padding=ft.padding.only(top=2)
#                 ),
#             ],
#             horizontal_alignment=ft.CrossAxisAlignment.CENTER,
#             spacing=4
#         ),
#         padding=ft.padding.only(top=35, bottom=25, left=30, right=30)
#     )
    
#     # Main scrollable content with improved scroll behavior
#     main_content = ft.Column(
#         [
#             header,
#             ft.Container(
#                 content=quote_container,
#                 padding=ft.padding.symmetric(horizontal=30)
#             ),
#             ft.Container(
#                 content=error_container,
#                 padding=ft.padding.only(top=16, bottom=8, left=30, right=30)
#             ),
#             ft.Container(
#                 content=ft.Column(
#                     [
#                         ft.Container(
#                             content=ft.Text(
#                                 "Quick Actions",
#                                 size=15,
#                                 weight=ft.FontWeight.BOLD,
#                                 color="#94a3b8",
#                             ),
#                             padding=ft.padding.only(bottom=12)
#                         ),
#                         buttons_row,
#                     ],
#                     spacing=14
#                 ),
#                 padding=ft.padding.only(top=20, bottom=35, left=30, right=30)
#             ),
#         ],
#         horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
#         spacing=0,
#         scroll=ft.ScrollMode.ADAPTIVE,
#         auto_scroll=False,
#         expand=True,
#     )
    
#     # Stack with decorative background
#     page.add(
#         ft.Stack(
#             [
#                 ft.Container(
#                     content=ft.Stack(
#                         [
#                             ft.Container(
#                                 content=deco_circle_1,
#                                 left=-100,
#                                 top=-150
#                             ),
#                             ft.Container(
#                                 content=deco_circle_2,
#                                 right=-80,
#                                 bottom=-100
#                             ),
#                         ]
#                     ),
#                     expand=True
#                 ),
#                 main_content
#             ],
#             expand=True
#         )
#     )
    
#     # Load initial quote
#     fetch_quote(get_random_quote)


# if __name__ == "__main__":
#     ft.app(target=main)


import flet as ft

import flet_ads as ads


def main(page: ft.Page):
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

    id_interstitial = (
        "ca-app-pub-3940256099942544/1033173712"
        if page.platform == ft.PagePlatform.ANDROID
        else "ca-app-pub-3940256099942544/4411468910"
    )

    id_banner = (
        "ca-app-pub-3940256099942544/6300978111"
        if page.platform == ft.PagePlatform.ANDROID
        else "ca-app-pub-3940256099942544/2934735716"
    )

    def handle_interstitial_close(e):
        nonlocal iad
        print("InterstitialAd closed")
        page.overlay.remove(e.control)
        page.overlay.append(iad := get_new_interstitial_ad())
        page.update()

    def get_new_interstitial_ad():
        return ads.InterstitialAd(
            unit_id=id_interstitial,
            on_load=lambda e: print("InterstitialAd loaded"),
            on_error=lambda e: print("InterstitialAd error", e.data),
            on_open=lambda e: print("InterstitialAd opened"),
            on_close=handle_interstitial_close,
            on_impression=lambda e: print("InterstitialAd impression"),
            on_click=lambda e: print("InterstitialAd clicked"),
        )

    def display_new_banner_ad():
        page.add(
            ft.Container(
                content=ads.BannerAd(
                    unit_id=id_banner,
                    on_click=lambda e: print("BannerAd clicked"),
                    on_load=lambda e: print("BannerAd loaded"),
                    on_error=lambda e: print("BannerAd error", e.data),
                    on_open=lambda e: print("BannerAd opened"),
                    on_close=lambda e: print("BannerAd closed"),
                    on_impression=lambda e: print("BannerAd impression"),
                    on_will_dismiss=lambda e: print("BannerAd will dismiss"),
                ),
                width=320,
                height=50,
                bgcolor=ft.Colors.TRANSPARENT,
            )
        )

    page.overlay.append(iad := get_new_interstitial_ad())
    page.appbar = ft.AppBar(
        adaptive=True,
        title=ft.Text("Mobile Ads Playground"),
        bgcolor=ft.Colors.LIGHT_BLUE_300,
    )
    page.add(
        ft.OutlinedButton("Show InterstitialAd", on_click=lambda e: iad.show()),
        ft.OutlinedButton("Show BannerAd", on_click=lambda e: display_new_banner_ad()),
    )


ft.app(main)