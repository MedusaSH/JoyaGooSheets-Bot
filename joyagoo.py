import os
import time
import requests
import re

import io
import json
from bs4 import BeautifulSoup
from colorama import Fore, Back, Style
from selenium import webdriver
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from urllib.parse import urljoin
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, ConversationHandler
from concurrent.futures import ThreadPoolExecutor




CHOOSING_CATEGORY, BROWSING_PRODUCTS, VIEWING_PRODUCT = range(3)

class JoyaGooScraper:

    
    def __init__(self):
   
        self.base_url = "https://www.joyagoosheets.com"
        self.data_folder = "telegram_cache"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
       
        self.firefox_options = FirefoxOptions()
        self.firefox_options.add_argument("--headless")
        self.firefox_options.add_argument("--no-sandbox")
        self.firefox_options.add_argument("--disable-dev-shm-usage")
        self.firefox_options.add_argument("--disable-gpu")
        self.firefox_options.add_argument("--disable-extensions")
        self.firefox_options.add_argument("--disable-software-rasterizer")
        self.firefox_options.add_argument("--disable-dev-tools")
        self.firefox_options.add_argument("--no-zygote")
        self.firefox_options.add_argument("--single-process")
   
        self.firefox_options.set_preference("javascript.enabled", False)  
        
        if not os.path.exists(self.data_folder):
            os.makedirs(self.data_folder)
            print(f"Dossier {self.data_folder} créé.")
        
        
        self.categories_cache = {}
        self.products_cache = {}
    
    def slugify(self, text):
        
        text = text.lower().strip()
        text = re.sub(r'[^\w\s-]', '', text)
        text = re.sub(r'[\s_-]+', '-', text)
        return text
    
    def get_dynamic_content(self, url):
       
        driver = None
        try:
         
            firefox_options = self.firefox_options
            
            try:
                driver = webdriver.Firefox(options=firefox_options)
                print(Fore.GREEN + "Driver Firefox initialisé avec succès." + Style.RESET_ALL)
            except Exception as e:
                print(Fore.RED + f"Erreur avec Firefox par défaut: {e}" + Style.RESET_ALL)
                print("Tentative avec le chemin explicite du driver...")
                
               
                gecko_path = "./geckodriver"  
                service = FirefoxService(executable_path=gecko_path)
                driver = webdriver.Firefox(service=service, options=firefox_options)
                print("Driver Firefox initialisé avec le chemin explicite.")
            
            
            driver.get(url)
            print(Fore.GREEN + f"Navigation vers: {url}" + Style.RESET_ALL)
            
            
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)  
            
            
            page_content = driver.page_source
            
            
            driver.quit()
            print(Fore.RED + "Driver Firefox fermé avec succès." + Style.RESET_ALL)
            
            
            return BeautifulSoup(page_content, 'html.parser')
        
        except Exception as e:
            print(f"Erreur lors du chargement dynamique de {url}: {e}")
            return None
        
        finally:
            
            if driver:
                try:
                    driver.quit()
                    print(Fore.RED +"Driver Firefox fermé dans finally.")
                except Exception as e:
                    print(Fore.RED +f"Erreur lors de la fermeture du driver dans finally: {e}")
    
    def __del__(self):
        
        try:
            if hasattr(self, 'driver'):
                self.driver.quit()
                print(Fore.RED +"Driver Firefox fermé.")
        except Exception as e:
            print(Fore.RED +f"Erreur lors de la fermeture du driver: {e}")
    
    def close_driver(self):
        
        try:
            if hasattr(self, 'driver'):
                self.driver.quit()
                delattr(self, 'driver')
                print(Fore.RED + "Driver Firefox fermé manuellement.")
        except Exception as e:
            print(Fore.RED +f"Erreur lors de la fermeture manuelle du driver: {e}")
    
    def get_category_links(self):
        
        print(Fore.GREEN + "Récupération des liens de catégories..." + Style.RESET_ALL)
        
        
        if self.categories_cache:
            print("Utilisation des catégories en cache.")
            return self.categories_cache
        
        soup = self.get_dynamic_content(self.base_url)
        if not soup:
            return {}
        
        category_links = {}
        
        
        nav_links = soup.find_all('a', href=re.compile(r'/item-type/'))
        
        for link in nav_links:
            href = link.get('href')
            if href:
                full_url = urljoin(self.base_url, href)
               
                category_name = href.split('/')[-1].replace('-', ' ').title()
                category_links[category_name] = full_url
                
        
        
        self.categories_cache = category_links
        
        return category_links
    
    def get_product_links(self, category_url):
        
        print(Fore.GREEN + f"Récupération des produits de la catégorie: {category_url}" + Style.RESET_ALL)
        
        
        if category_url in self.products_cache:
            print("Utilisation des produits en cache.")
            return self.products_cache[category_url]
        
        soup = self.get_dynamic_content(category_url)
        if not soup:
            return []
        
        products = []
        
        
        product_links = soup.find_all('a', href=re.compile(r'/products/|/product/|/item/'))
        
       
        product_cards = soup.find_all(['div', 'article'], class_=lambda x: x and ('product' in x.lower() or 'item' in x.lower()))
        
       
        for link in product_links:
            href = link.get('href')
            if href and '/products/' in href:
                full_url = urljoin(self.base_url, href)
                
                product_name = href.split('/')[-1].replace('-', ' ').title()
                
             
                if not any(p['url'] == full_url for p in products):
                    products.append({
                        'name': product_name,
                        'url': full_url
                    })
                    
        

        for card in product_cards:
            
            link = card.find('a', href=True)
            if link and link.get('href'):
                href = link.get('href')
                full_url = urljoin(self.base_url, href)
                
                
                name_elem = card.find(['h2', 'h3', 'h4', 'span', 'div'], 
                                    class_=lambda x: x and ('title' in x.lower() or 'name' in x.lower()))
                
                if name_elem:
                    product_name = name_elem.text.strip()
                else:
                    product_name = href.split('/')[-1].replace('-', ' ').title()
                
                
                if not any(p['url'] == full_url for p in products):
                    products.append({
                        'name': product_name,
                        'url': full_url
                    })
                    print(Fore.GREEN + f"Produit trouvé (carte): {product_name} ({full_url})" + Style.RESET_ALL)
        
       
        if not products:
           
            product_containers = soup.find_all(['div', 'article', 'section'], 
                                             class_=lambda x: x and any(term in x.lower() 
                                             for term in ['product', 'item', 'goods', 'merchandise']))
            
            for container in product_containers:
                link = container.find('a', href=True)
                if link and link.get('href'):
                    href = link.get('href')
                    if '/products/' in href or '/product/' in href:
                        full_url = urljoin(self.base_url, href)
                        product_name = href.split('/')[-1].replace('-', ' ').title()
                        
                        if not any(p['url'] == full_url for p in products):
                            products.append({
                                'name': product_name,
                                'url': full_url
                            })
                            print(Fore.GREEN + f"Produit trouvé (méthode alternative): {product_name} ({full_url})" + Style.RESET_ALL)
        
        
        self.products_cache[category_url] = products
        
        print(Fore.GREEN + f"Nombre total de produits trouvés: {len(products)}" + Style.RESET_ALL)
        return products
    
    def extract_product_info(self, product_url):
        
        print(Fore.GREEN + f"Extraction des informations du produit: {product_url}" + Style.RESET_ALL)
        soup = self.get_dynamic_content(product_url)
        if not soup:
            return None
        
        
        product_name = None
        title_element = soup.find('h1')
        if title_element:
            product_name = title_element.text.strip()
        
        if not product_name:
            
            product_name = product_url.split('/')[-1].replace('-', ' ').title()
        
        
        price = "Prix non disponible"
        
        
        price_elements = soup.find_all(lambda tag: (
            tag.get('class', []) and any('price' in c.lower() for c in tag.get('class', []) if isinstance(c, str)) or
            tag.get('id', '').lower() and 'price' in tag.get('id', '').lower()
        ))
        
        
        if not price_elements:
            price_elements = soup.find_all(text=re.compile(r'(\$|€|£|\d+[.,]\d{2})'))
        
       
        if not price_elements:
            price_elements = soup.find_all(text=re.compile(r'\d+[.,]\d{2}'))
        
        if price_elements:
            for element in price_elements:
                
                if hasattr(element, 'text'):
                    price_text = element.text.strip()
                else:
                    
                    price_text = str(element).strip()
                
                
                if re.search(r'(\$|€|£|\d+[.,]\d{2})', price_text):
                    price = price_text
                    break
        
       
        description = "Description non disponible"
        desc_element = soup.find(['div', 'p'], class_=lambda c: c and ('description' in c.lower() or 'product-details' in c.lower()))
        if desc_element:
            description = desc_element.text.strip()
        
        
        image_links = []
        
        
        
        image_elements = soup.find_all('img')
        for img in image_elements:
            src = img.get('src')
            if src and not src.startswith('data:'):
                
                if not src.lower().endswith('.svg'):
                    full_img_url = urljoin(self.base_url, src)
                    if full_img_url not in image_links:
                        image_links.append(full_img_url)
        
        
        style_elements = soup.find_all(lambda tag: tag.has_attr('style') and 'background-image' in tag['style'])
        for element in style_elements:
            style = element['style']
            url_match = re.search(r'url\([\'"]?(.*?)[\'"]?\)', style)
            if url_match:
                img_url = url_match.group(1)
               
                if not img_url.lower().endswith('.svg'):
                    full_img_url = urljoin(self.base_url, img_url)
                    if full_img_url not in image_links:
                        image_links.append(full_img_url)
        
        data_src_elements = soup.find_all(lambda tag: tag.has_attr('data-src'))
        for element in data_src_elements:
            data_src = element['data-src']
            # Ignorer les SVG
            if not data_src.lower().endswith('.svg'):
                full_img_url = urljoin(self.base_url, data_src)
                if full_img_url not in image_links:
                    image_links.append(full_img_url)
        
       
        filtered_images = []
        for img_url in image_links:
           
            if not any(keyword in img_url.lower() for keyword in ['icon', 'logo', 'favicon', '.svg']):
                filtered_images.append(img_url)
        
        print(Fore.GREEN + f"Nombre d'images trouvées pour {product_name}: {len(filtered_images)}" + Style.RESET_ALL)
        
     
        purchase_links = []
        external_links = soup.find_all('a', target='_blank')
        for link in external_links:
            href = link.get('href')
            if href and not href.startswith(self.base_url) and not href.startswith('/'):
                purchase_links.append(href)
        
        return {
            'name': product_name,
            'url': product_url,
            'price': price,
            'description': description,
            'images': filtered_images,
            'purchase_links': purchase_links
        }
    
    def get_image_bytes(self, image_url):
        
        try:
            response = requests.get(image_url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            
            content_type = response.headers.get('Content-Type', '')
            if not content_type.startswith('image/'):
                logger.warning(f"Contenu non-image ignoré: {image_url} (type: {content_type})")
                return None
            
            
            if content_type == 'image/svg+xml' or image_url.lower().endswith('.svg'):
                logger.warning(f"Image SVG ignorée: {image_url}")
                return None
            
            return io.BytesIO(response.content)
        except Exception as e:
            print(Fore.RED + f"Erreur lors du téléchargement de l'image {image_url}: {e}" + Style.RESET_ALL)
            return None
    
    def download_image(self, image_url):
        
        try:
            response = requests.get(image_url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            
            content_type = response.headers.get('Content-Type', '')
            if not content_type.startswith('image/'):
                logger.warning(f"Contenu non-image ignoré: {image_url} (type: {content_type})")
                return None
            
            if content_type == 'image/svg+xml' or image_url.lower().endswith('.svg'):
                logger.warning(f"Image SVG ignorée: {image_url}")
                return None
            
           
            extension = '.jpg'  
            if content_type == 'image/png':
                extension = '.png'
            elif content_type == 'image/gif':
                extension = '.gif'
            elif content_type == 'image/webp':
                extension = '.webp'
            
            
            filename = f"{self.slugify(image_url)}_{int(time.time())}{extension}"
            filepath = os.path.join(self.data_folder, filename)
            
            with open(filepath, 'wb') as f:
                f.write(response.content)
            
            print(Fore.GREEN + f"Image téléchargée: {filepath}" + Style.RESET_ALL)
            return filepath
        except Exception as e:
            print(Fore.RED + f"Erreur lors du téléchargement de l'image {image_url}: {e}" + Style.RESET_ALL)
            return None


scraper = JoyaGooScraper()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
   
    if 'scraper' not in context.bot_data:
        context.bot_data['scraper'] = JoyaGooScraper()
    
    
    scraper = context.bot_data['scraper']
    categories = scraper.get_category_links()
    
    
    context.user_data['categories'] = list(categories.items())
    
    
    keyboard = []
    for i, (category_name, category_url) in enumerate(categories.items()):
        keyboard.append([InlineKeyboardButton(category_name, callback_data=f"category_{i}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    message_text = "👋 *Bienvenue!*\n\nChoisissez une catégorie pour voir les produits disponibles:"

    if update.message:
        await update.message.reply_text(
            text=message_text,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    elif update.callback_query:
        
        query = update.callback_query
        try:
            
            await query.message.delete()
        except Exception as e:
            print(f"Erreur lors de la suppression du message: {e}")
        
        
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=message_text,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    
    return CHOOSING_CATEGORY

async def category_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
   
    query = update.callback_query
    await query.answer()
    
    
    category_idx = int(query.data.replace("category_", ""))
    
   
    categories = context.user_data['categories']
    category_name, category_url = categories[category_idx]
    
   
    await query.edit_message_text(f"Récupération des produits de la catégorie {category_name}...")
    
    
    products = scraper.get_product_links(category_url)
    
    if not products:
        await query.edit_message_text(
            f"Aucun produit trouvé dans la catégorie {category_name}."
        )
        return CHOOSING_CATEGORY
    
   
    context.user_data['products'] = products
    context.user_data['category_name'] = category_name
    context.user_data['current_page'] = 0
    
  
    await show_products_page(query, context)
    
    return BROWSING_PRODUCTS

async def show_products_page(query, context):
   
    try:
        products = context.user_data.get('products', [])
        current_page = context.user_data.get('current_page', 0)
        items_per_page = 5
        
        start_idx = current_page * items_per_page
        end_idx = start_idx + items_per_page
        current_products = products[start_idx:end_idx]
        
        message_text = "🛍️ *Produits disponibles:*\n\n"
        keyboard = []
        
        
        for idx, product in enumerate(current_products, start=start_idx):
            message_text += f"{idx + 1}. {product['name']}\n"
            keyboard.append([InlineKeyboardButton(f"Voir {product['name']}", callback_data=f"product_{idx}")])
        
      
        nav_buttons = []
        if current_page > 0:
            nav_buttons.append(InlineKeyboardButton("⬅️ Précédent", callback_data="prev_page"))
        if end_idx < len(products):
            nav_buttons.append(InlineKeyboardButton("Suivant ➡️", callback_data="next_page"))
        if nav_buttons:
            keyboard.append(nav_buttons)
        
       
        keyboard.append([InlineKeyboardButton("🔙 Retour aux catégories", callback_data="back_to_categories")])
        
        try:
           
            if hasattr(query, 'message'):
                await query.message.delete()
        except Exception as e:
            print(Fore.RED + f"Erreur lors de la suppression du message: {e}" + Style.RESET_ALL)
        
        
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=message_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        
    except Exception as e:
        print(Fore.RED + f"Erreur dans show_products_page: {e}" + Style.RESET_ALL)
        try:
            if hasattr(query, 'message'):
                await query.message.delete()
        except Exception as delete_error:
            print(Fore.RED + f"Erreur lors de la suppression du message: {delete_error}" + Style.RESET_ALL)
            
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="Une erreur s'est produite lors de l'affichage des produits.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Retour aux catégories", callback_data="back_to_categories")
            ]]),
            parse_mode="Markdown"
        )

async def navigate_products(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
   
    query = update.callback_query
    await query.answer()
    
    if query.data == "prev_page":
        context.user_data['current_page'] -= 1
    elif query.data == "next_page":
        context.user_data['current_page'] += 1
    elif query.data == "back_to_categories":
        return await start(update, context)
    
    await show_products_page(query, context)
    return BROWSING_PRODUCTS

async def product_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    
    query = update.callback_query
    await query.answer()
    
    
    product_idx = int(query.data.replace("product_", ""))
    
   
    products = context.user_data['products']
    product_url = products[product_idx]['url']
    
    
    await query.edit_message_text("Récupération des détails du produit en cours...")
    
    
    product_info = scraper.extract_product_info(product_url)
    
    if not product_info:
        await query.edit_message_text(
            f"Désolé, je n'ai pas pu récupérer les détails du produit."
        )
        return BROWSING_PRODUCTS
    
    
    context.user_data['current_product'] = product_info
    context.user_data['current_product_idx'] = product_idx
    
    
    caption = f"📦 *{product_info['name']}*\n\n"
    caption += f"💰 *Prix:* {product_info['price']}\n\n"
    
    if product_info['description'] != "Description non disponible":
        
        description = product_info['description']
        if len(description) > 200:
            description = description[:197] + "..."
        caption += f"📝 *Description:* {description}\n\n"
    
    if product_info['purchase_links']:
        caption += f"🛒 *Liens d'achat:* {len(product_info['purchase_links'])} disponibles"
    
    
    keyboard = []
    
    
    if product_info['purchase_links']:
        keyboard.append([InlineKeyboardButton("🛒 Voir les liens d'achat", callback_data=f"purchase_{product_idx}")])
    
    
    keyboard.append([InlineKeyboardButton("🔙 Retour aux produits", callback_data="back_to_products")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    
    if product_info['images']:
        image_url = product_info['images'][0]
        image_bytes = scraper.get_image_bytes(image_url)
        
        if image_bytes:
            
            await query.delete_message()
            
            
            await query.message.reply_photo(
                photo=image_bytes,
                caption=caption,
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
        else:
            
            await query.edit_message_text(
                caption,
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
    else:
       
        await query.edit_message_text(
            caption,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    
    return VIEWING_PRODUCT

async def handle_product_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    
    query = update.callback_query
    await query.answer()
    
    try:
        if query.data == "back_to_products":
            
            if 'current_page' not in context.user_data:
                context.user_data['current_page'] = 0
                
            try:
                await query.message.delete()
            except Exception as e:
                print(Fore.RED + f"Erreur lors de la suppression du message: {e}" + Style.RESET_ALL)
            
            
            await show_products_page(query, context)
            return BROWSING_PRODUCTS
        
        elif query.data.startswith("purchase_"):
            product_info = context.user_data['current_product']
            message = f"🛒 *Liens d'achat pour {product_info['name']}:*\n\n"
            
            for i, link in enumerate(product_info['purchase_links']):
                message += f"{i+1}. [{link[:30]}...]({link})\n"
            
            keyboard = [[InlineKeyboardButton("🔙 Retour au produit", callback_data="back_to_details")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            try:
                
                await query.message.delete()
            except Exception as e:
                print(Fore.RED + f"Erreur lors de la suppression du message: {e}" + Style.RESET_ALL)
            
            
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=message,
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
            
            return VIEWING_PRODUCT
        
        elif query.data == "back_to_details":
            product_info = context.user_data.get('current_product')
            if not product_info:
                try:
                    await query.message.delete()
                except Exception as e:
                    print(f"Erreur lors de la suppression du message: {e}")
                await show_products_page(query, context)
                return BROWSING_PRODUCTS
            
            caption = f"📦 *{product_info['name']}*\n\n"
            caption += f"💰 *Prix:* {product_info['price']}\n\n"
            
            if product_info.get('description') and product_info['description'] != "Description non disponible":
                description = product_info['description']
                if len(description) > 200:
                    description = description[:197] + "..."
                caption += f"📝 *Description:* {description}\n\n"
            
            if product_info.get('purchase_links'):
                caption += f"🛒 *Liens d'achat:* {len(product_info['purchase_links'])} disponibles"
            
            keyboard = []
            if product_info.get('purchase_links'):
                keyboard.append([InlineKeyboardButton("🛒 Voir les liens d'achat", 
                              callback_data=f"purchase_{context.user_data.get('current_product_idx', 0)}")])
            keyboard.append([InlineKeyboardButton("🔙 Retour aux produits", callback_data="back_to_products")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            try:
                
                await query.message.delete()
            except Exception as e:
                print(f"Erreur lors de la suppression du message: {e}")
            
            
            if product_info.get('images'):
                image_url = product_info['images'][0]
                image_bytes = context.bot_data.get('scraper').get_image_bytes(image_url)
                
                if image_bytes:
                    await context.bot.send_photo(
                        chat_id=query.message.chat_id,
                        photo=image_bytes,
                        caption=caption,
                        reply_markup=reply_markup,
                        parse_mode="Markdown"
                    )
                else:
                    await context.bot.send_message(
                        chat_id=query.message.chat_id,
                        text=caption,
                        reply_markup=reply_markup,
                        parse_mode="Markdown"
                    )
            else:
                await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text=caption,
                    reply_markup=reply_markup,
                    parse_mode="Markdown"
                )
            
            return VIEWING_PRODUCT
        
        return VIEWING_PRODUCT
        
    except Exception as e:
        print(Fore.RED + f"Erreur générale dans handle_product_action: {e}" + Style.RESET_ALL)
        try:
            await query.message.delete()
        except Exception as delete_error:
            print(Fore.RED + f"Erreur lors de la suppression du message: {delete_error}" + Style.RESET_ALL)
        
       
        await show_products_page(query, context)
        return BROWSING_PRODUCTS

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    
    await update.message.reply_text(
        "Au revoir! N'hésitez pas à revenir pour découvrir de nouveaux produits."
    )
    return ConversationHandler.END

def main():
   
    application = Application.builder().token("7868473905:AAGreRZ0JUbFC57IusSr8g5GkMIIWm01z9Y").build()
    
    
    scraper = JoyaGooScraper()
    application.bot_data['scraper'] = scraper
    
    
    application.bot_data['executor'] = ThreadPoolExecutor(max_workers=4)
    
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSING_CATEGORY: [
                CallbackQueryHandler(category_selected, pattern=r"^category_")
            ],
            BROWSING_PRODUCTS: [
                CallbackQueryHandler(product_selected, pattern=r"^product_"),
                CallbackQueryHandler(navigate_products, pattern=r"^(prev_page|next_page|back_to_categories)$")
            ],
            VIEWING_PRODUCT: [
                CallbackQueryHandler(handle_product_action)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    
    application.add_handler(conv_handler)
    
   
    application.run_polling()

if __name__ == "__main__":
    main() 
