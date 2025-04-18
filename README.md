# JoyaGooSheets Telegram Bot 🤖🛍️

[![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Telegram](https://img.shields.io/badge/Telegram-Bot-blue)](https://core.telegram.org/bots)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Contributions Welcome](https://img.shields.io/badge/contributions-welcome-brightgreen.svg)](https://github.com/MedusaSH/JoyaGooSheets-Bot/issues)

Un bot Telegram intelligent pour naviguer et découvrir les produits disponibles sur JoyaGooSheets.com.

## Fonctionnalités Clés ✨
- Navigation intuitive par catégories
- Affichage des produits avec images
- Prix et descriptions des produits
- Liens d'achat directs
- Système de cache intelligent
- Interface avec boutons interactifs

## Technologies Utilisées 🛠️
- Python 3.8+
- python-telegram-bot
- Selenium
- BeautifulSoup4
- Requests
- Firefox Headless

## Installation Complète 💻

### Prérequis
1. Compte Telegram avec token de bot (obtenu via @BotFather)
2. Python 3.8+ installé
3. Geckodriver installé (https://github.com/mozilla/geckodriver/releases)

### Installation Pas à Pas

1. Cloner le dépôt :
git clone https://github.com/MedusaSH/JoyaGooSheets-Bot.git
cd JoyaGooSheets-Bot

2. Installer les dépendances :
pip install -r requirements.txt

3. Configurer le bot :
cp config.example.py config.py
Editer config.py avec votre token Telegram

4. Lancer le bot :
python main.py

## Structure des Fichiers
main.py - Point d'entrée principal
scraper.py - Module de scraping
handlers.py - Gestionnaires Telegram
config.py - Fichier de configuration
requirements.txt - Dépendances
telegram_cache/ - Dossier de cache

## Comment Contribuer 🤝
1. Forker le projet
2. Créer une branche (git checkout -b feature/NouvelleFonctionnalite)
3. Committer vos changements (git commit -m 'Ajout dune fonctionnalité')
4. Pousser vers la branche (git push origin feature/NouvelleFonctionnalite)
5. Ouvrir une Pull Request

## Licence 📜
MIT License - voir le fichier LICENSE

## Auteur 👤
MedusaSH - GitHub: https://github.com/MedusaSH

## Roadmap 🗺️
- ✓ Scraping de base
- ✓ Interface Telegram
- ☐ Recherche textuelle
- ☐ Système de favoris
- ☐ Notifications
