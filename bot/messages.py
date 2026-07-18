_LANG_MAP = {
    "ru": "ru", "be": "ru", "uk": "ru",
    "he": "he", "iw": "he",
    "es": "es",
}

MSG: dict[str, dict[str, str]] = {
    "en": {
        "welcome": (
            "💃 <b>Milonga Finder</b>\n\n"
            "I'll help you find tango milongas in any city for today."
        ),
        "menu_prompt": "What would you like to do?",
        "btn_find": "🔍 Find milongas today",
        "btn_donate": "☕ Support the project",
        "ask_city": "🏙 <b>Enter the city name:</b>\n<i>e.g. Budapest, Tel Aviv, Buenos Aires</i>",
        "searching": "🔍 Searching for milongas in <b>{city}</b>…\n<i>This may take a few minutes while we search the web.</i>",
        "no_events": (
            "😕 No milongas or practicas found in <b>{city}</b> today.\n\n"
            "Try another city or check back tomorrow."
        ),
        "city_not_found": (
            "🌍 City <b>{city}</b> not found.\n\n"
            "Please check the spelling or try in English (e.g. <i>Moscow</i>, <i>Tbilisi</i>)."
        ),
        "events_header": "💃 <b>Tango in {city}</b>\n📅 {date}\n",
        "back": "↩️ Back",
        "donate_text": (
            "☕ <b>Support Milonga Finder</b>\n\n"
            "If this bot helps you dance more — buy me a coffee!\n"
            "Every ⭐ Star keeps the project running."
        ),
        "donate_title": "Support Milonga Finder",
        "donate_50": "☕ 50 ⭐",
        "donate_250": "🥐 250 ⭐",
        "donate_500": "🌟 500 ⭐",
        "donate_custom": "✏️ Any amount",
        "ask_stars_amount": "Enter the amount in Stars (minimum 50):",
        "invalid_stars": "⚠️ Please enter a valid number (minimum 50 Stars).",
        "close": "✖ Close",
        "donate_desc_tip": "A small tip to support Milonga Finder ☕",
        "donate_desc_30": "Unlock 30 days of unlimited searches in Milonga Finder",
        "donate_desc_90": "Unlock 90 days of unlimited searches in Milonga Finder",
        "donate_thanks": "🙏 Thank you so much! Your support means a lot. ❤️",
        "paywall_button": "🔓 Unlock 24h — {stars} ⭐",
        "paywall_invoice_title": "24-hour unlimited access",
        "paywall_invoice_desc": "Unlock unlimited milonga searches for 24 hours",
        "paywall_thanks": "✅ Unlimited access unlocked for 24 hours!\nSearching in <b>{city}</b>…",
        "paywall_unlocked": "✅ Unlimited access unlocked for 24 hours! Send me a city to search.",
        "rate_limit": (
            "⏳ Your one free trial search is already used.\n\n"
            "Unlock unlimited searches for 24 hours for {stars} ⭐."
        ),
        "premium_granted": (
            "🎉 Thank you! Unlimited searches unlocked for <b>{days} days</b> (until {until}). ❤️"
        ),
        "status_premium": "⭐ <b>Status:</b> Premium until <b>{until}</b>. Unlimited searches.",
        "status_free_available": "🔍 <b>Status:</b> You have your one free trial search available.",
        "status_free_used": "🔍 <b>Status:</b> Free trial search already used. Unlock 24h unlimited for {stars} ⭐.",
        "free_trial_used": "\n\n<i>✅ That was a test search. Next time, unlock 24h unlimited for {stars} ⭐.</i>",
        "disclaimer": "ℹ️ <i>AI-powered bot — info may be incomplete. Always verify with the organizer.</i>",
        "error": "⚠️ Something went wrong. Please try again.",
        # Partner finder
        "btn_partner": "🤝 Find a practice partner",
        "partner_ask_role": "🕺 <b>What's your role?</b>",
        "partner_role_leader": "Leader",
        "partner_role_follower": "Follower",
        "partner_role_both": "Can do both",
        "partner_role_label_leader": "leader",
        "partner_role_label_follower": "follower",
        "partner_role_label_both": "leader/follower",
        "partner_ask_city": (
            "🏙 <b>Which city are you heading to for practice?</b>\n\n"
            "<i>Share your location or type the city name.</i>"
        ),
        "partner_city_use_last": "Use {city}",
        "partner_city_type": "Enter city",
        "partner_share_location": "Share location",
        "partner_ask_note": (
            "✏️ <b>A word about yourself?</b>\n"
            "<i>Level, style, anything useful — optional.</i>"
        ),
        "partner_note_skip": "Skip",
        "partner_list_header": "🤝 <b>Looking for a partner in {city} today:</b>\n",
        "partner_list_empty": (
            "🤝 No one else is looking in <b>{city}</b> right now.\n\n"
            "Your request is saved — I'll notify you when someone shows up."
        ),
        "partner_remove_btn": "Found a partner ✓",
        "partner_refresh_btn": "Refresh",
        "partner_removed": "Your request has been removed.",
        "partner_already": (
            "You already have an active request in <b>{city}</b> as {role}.\n\n"
            "Update it or remove it first."
        ),
        "partner_notify_msg": (
            "👋 Someone is looking for a practice partner in <b>{city}</b> today!\n"
            "Open the bot to see the list: /partner"
        ),
        "partner_nudge_msg": (
            "Did you find a practice partner in <b>{city}</b>?\n\n"
            "If yes — tap below so others know the spot is taken."
        ),
        "partner_nudge_yes": "Yes, remove me ✓",
        "partner_nudge_no": "Still looking",
        "partner_nudge_still": "Got it — still in the list.",
        "partner_no_username": (
            "⚠️ You don't have a Telegram username set.\n"
            "Others won't be able to contact you directly.\n\n"
            "You can set one in Telegram Settings → Edit Profile → Username."
        ),
        "partner_location_failed": "Couldn't detect city from your location. Please type the city name:",
        "partner_city_failed": "Couldn't verify the city name right now. Please try again:",
    },
    "ru": {
        "welcome": (
            "💃 <b>Milonga Finder</b>\n\n"
            "Помогу найти танго-милонги в любом городе на сегодня."
        ),
        "menu_prompt": "Что хотите сделать?",
        "btn_find": "🔍 Найти милонги сегодня",
        "btn_donate": "☕ Поддержать проект",
        "ask_city": "🏙 <b>Введите название города:</b>\n<i>например: Budapest, Tel Aviv, Buenos Aires</i>",
        "searching": "🔍 Ищу милонги в <b>{city}</b>…\n<i>Это может занять несколько минут — ищем в интернете.</i>",
        "no_events": (
            "😕 Милонги и практики в <b>{city}</b> сегодня не найдены.\n\n"
            "Попробуйте другой город или загляните завтра."
        ),
        "city_not_found": (
            "🌍 Город <b>{city}</b> не найден.\n\n"
            "Проверьте написание или попробуйте на английском (например: <i>Moscow</i>, <i>Tbilisi</i>)."
        ),
        "events_header": "💃 <b>Танго в {city}</b>\n📅 {date}\n",
        "back": "↩️ Назад",
        "donate_text": (
            "☕ <b>Поддержать Milonga Finder</b>\n\n"
            "Если бот помогает вам танцевать — угостите меня кофе!\n"
            "Каждая ⭐ Звезда помогает держать проект живым."
        ),
        "donate_title": "Поддержать Milonga Finder",
        "donate_50": "☕ 50 ⭐",
        "donate_250": "🥐 250 ⭐",
        "donate_500": "🌟 500 ⭐",
        "donate_custom": "✏️ Любая сумма",
        "ask_stars_amount": "Введите сумму в Stars (минимум 50):",
        "invalid_stars": "⚠️ Введите корректное число (минимум 50 Stars).",
        "close": "✖ Закрыть",
        "donate_desc_tip": "Небольшие чаевые для поддержки Milonga Finder ☕",
        "donate_desc_30": "30 дней безлимитного поиска в Milonga Finder",
        "donate_desc_90": "90 дней безлимитного поиска в Milonga Finder",
        "donate_thanks": "🙏 Большое спасибо! Ваша поддержка очень важна. ❤️",
        "paywall_button": "🔓 Открыть на сутки — {stars} ⭐",
        "paywall_invoice_title": "Безлимит на 24 часа",
        "paywall_invoice_desc": "Безлимитный поиск милонг в течение 24 часов",
        "paywall_thanks": "✅ Безлимит открыт на 24 часа!\nИщу в <b>{city}</b>…",
        "paywall_unlocked": "✅ Безлимит открыт на 24 часа! Отправьте город для поиска.",
        "rate_limit": (
            "⏳ Ваш единственный бесплатный поиск уже использован.\n\n"
            "Откройте безлимит на 24 часа за {stars} ⭐."
        ),
        "premium_granted": (
            "🎉 Спасибо! Безлимит активирован на <b>{days} дней</b> (до {until}). ❤️"
        ),
        "status_premium": "⭐ <b>Статус:</b> Премиум до <b>{until}</b>. Безлимитный поиск.",
        "status_free_available": "🔍 <b>Статус:</b> У вас есть один бесплатный пробный поиск.",
        "status_free_used": "🔍 <b>Статус:</b> Бесплатный поиск уже использован. Доступ на сутки — {stars} ⭐.",
        "free_trial_used": "\n\n<i>✅ Это был тестовый поиск. В следующий раз — {stars} ⭐ за сутки безлимита.</i>",
        "disclaimer": "ℹ️ <i>Бот на основе ИИ — информация может быть неполной. Уточняйте у организаторов.</i>",
        "error": "⚠️ Что-то пошло не так. Попробуйте ещё раз.",
        # Partner finder
        "btn_partner": "🤝 Найти партнёра для практики",
        "partner_ask_role": "🕺 <b>Какая у тебя роль?</b>",
        "partner_role_leader": "Лидер",
        "partner_role_follower": "Фолловер",
        "partner_role_both": "Могу обе",
        "partner_role_label_leader": "лидер",
        "partner_role_label_follower": "фолловер",
        "partner_role_label_both": "лидер/фолловер",
        "partner_ask_city": (
            "🏙 <b>В какой город едешь на практику?</b>\n\n"
            "<i>Поделись геолокацией или введи название города.</i>"
        ),
        "partner_city_use_last": "Использовать {city}",
        "partner_city_type": "Ввести город",
        "partner_share_location": "Поделиться геолокацией",
        "partner_ask_note": (
            "✏️ <b>Пару слов о себе?</b>\n"
            "<i>Уровень, стиль, что угодно — необязательно.</i>"
        ),
        "partner_note_skip": "Пропустить",
        "partner_list_header": "🤝 <b>Ищут партнёра в {city} сегодня:</b>\n",
        "partner_list_empty": (
            "🤝 Сейчас никто не ищет партнёра в <b>{city}</b>.\n\n"
            "Заявка сохранена — пришлю уведомление, когда кто-то появится."
        ),
        "partner_remove_btn": "Нашёл партнёра ✓",
        "partner_refresh_btn": "Обновить",
        "partner_removed": "Заявка удалена.",
        "partner_already": (
            "У тебя уже есть активная заявка в <b>{city}</b> как {role}.\n\n"
            "Обнови или удали её сначала."
        ),
        "partner_notify_msg": (
            "👋 Кто-то ищет партнёра для практики в <b>{city}</b> сегодня!\n"
            "Открой бота, чтобы увидеть список: /partner"
        ),
        "partner_nudge_msg": (
            "Ты нашёл партнёра для практики в <b>{city}</b>?\n\n"
            "Если да — нажми ниже, чтобы убрать заявку."
        ),
        "partner_nudge_yes": "Да, убрать меня ✓",
        "partner_nudge_no": "Ещё ищу",
        "partner_nudge_still": "Понял — остаёшься в списке.",
        "partner_no_username": (
            "⚠️ У тебя не задан username в Telegram.\n"
            "Другие не смогут написать тебе напрямую.\n\n"
            "Задать можно в Настройки Telegram → Изменить профиль → Имя пользователя."
        ),
        "partner_location_failed": "Не удалось определить город по геолокации. Введи название города:",
        "partner_city_failed": "Не получилось обработать название города. Попробуй ещё раз:",
    },
    "he": {
        "welcome": (
            "💃 <b>Milonga Finder</b>\n\n"
            "אמצא עבורך מילונגות טנגו בכל עיר להיום."
        ),
        "menu_prompt": "מה תרצה לעשות?",
        "btn_find": "🔍 מצא מילונגות להיום",
        "btn_donate": "☕ תמוך בפרויקט",
        "ask_city": "🏙 <b>הכנס שם עיר:</b>\n<i>לדוגמה: Budapest, Tel Aviv, Buenos Aires</i>",
        "searching": "🔍 מחפש מילונגות ב-<b>{city}</b>…\n<i>זה עשוי לקחת כמה דקות — אנחנו מחפשים באינטרנט.</i>",
        "no_events": (
            "😕 לא נמצאו מילונגות ופרקטיקות ב-<b>{city}</b> היום.\n\n"
            "נסה עיר אחרת או חזור מחר."
        ),
        "city_not_found": (
            "🌍 העיר <b>{city}</b> לא נמצאה.\n\n"
            "בדוק את האיות או נסה באנגלית (לדוגמה: <i>Moscow</i>, <i>Tbilisi</i>)."
        ),
        "events_header": "💃 <b>טנגו ב-{city}</b>\n📅 {date}\n",
        "back": "↩️ חזרה",
        "donate_text": (
            "☕ <b>תמוך ב-Milonga Finder</b>\n\n"
            "אם הבוט עוזר לך לרקוד יותר — קנה לי קפה!\n"
            "כל ⭐ כוכב עוזר להמשיך את הפרויקט."
        ),
        "donate_title": "תמוך ב-Milonga Finder",
        "donate_50": "☕ 50 ⭐",
        "donate_250": "🥐 250 ⭐",
        "donate_500": "🌟 500 ⭐",
        "donate_custom": "✏️ סכום חופשי",
        "ask_stars_amount": "הכנס סכום בכוכבים (מינימום 50):",
        "invalid_stars": "⚠️ הכנס מספר תקין (מינימום 50 כוכבים).",
        "close": "✖ סגור",
        "donate_desc_tip": "טיפ קטן לתמיכה ב-Milonga Finder ☕",
        "donate_desc_30": "30 ימי חיפוש ללא הגבלה ב-Milonga Finder",
        "donate_desc_90": "90 ימי חיפוש ללא הגבלה ב-Milonga Finder",
        "donate_thanks": "🙏 תודה רבה! התמיכה שלך מאוד חשובה. ❤️",
        "paywall_button": "🔓 פתח ל-24 שעות — {stars} ⭐",
        "paywall_invoice_title": "גישה ללא הגבלה ל-24 שעות",
        "paywall_invoice_desc": "פתח חיפוש מילונגות ללא הגבלה למשך 24 שעות",
        "paywall_thanks": "✅ הגישה נפתחה ל-24 שעות!\nמחפש ב-<b>{city}</b>…",
        "paywall_unlocked": "✅ הגישה נפתחה ל-24 שעות! שלח שם עיר לחיפוש.",
        "rate_limit": (
            "⏳ החיפוש החינמי היחיד שלך כבר נוצל.\n\n"
            "פתח חיפוש ללא הגבלה ל-24 שעות תמורת {stars} ⭐."
        ),
        "premium_granted": (
            "🎉 תודה! חיפוש ללא הגבלה פעיל ל-<b>{days} ימים</b> (עד {until}). ❤️"
        ),
        "status_premium": "⭐ <b>סטטוס:</b> פרימיום עד <b>{until}</b>. חיפוש ללא הגבלה.",
        "status_free_available": "🔍 <b>סטטוס:</b> יש לך חיפוש ניסיון חינמי אחד זמין.",
        "status_free_used": "🔍 <b>סטטוס:</b> חיפוש הניסיון החינמי כבר נוצל. פתח גישה ללא הגבלה ל-24 שעות תמורת {stars} ⭐.",
        "free_trial_used": "\n\n<i>✅ זה היה חיפוש בדיקה. בפעם הבאה — {stars} ⭐ לגישה ללא הגבלה ל-24 שעות.</i>",
        "disclaimer": "ℹ️ <i>בוט מבוסס בינה מלאכותית — המידע עשוי להיות חלקי. תמיד בדקו עם המארגן.</i>",
        "error": "⚠️ משהו השתבש. נסה שוב.",
        # Partner finder
        "btn_partner": "🤝 מצא שותף לפרקטיקה",
        "partner_ask_role": "🕺 <b>מה התפקיד שלך?</b>",
        "partner_role_leader": "מוביל",
        "partner_role_follower": "עוקב/ת",
        "partner_role_both": "שניהם",
        "partner_role_label_leader": "מוביל",
        "partner_role_label_follower": "עוקב/ת",
        "partner_role_label_both": "מוביל/עוקב",
        "partner_ask_city": (
            "🏙 <b>לאיזו עיר אתה נוסע לפרקטיקה?</b>\n\n"
            "<i>שתף מיקום או הכנס שם עיר.</i>"
        ),
        "partner_city_use_last": "השתמש ב-{city}",
        "partner_city_type": "הכנס עיר",
        "partner_share_location": "שתף מיקום",
        "partner_ask_note": (
            "✏️ <b>כמה מילים על עצמך?</b>\n"
            "<i>רמה, סגנון, כל דבר שימושי — אופציונלי.</i>"
        ),
        "partner_note_skip": "דלג",
        "partner_list_header": "🤝 <b>מחפשים שותף ב-{city} היום:</b>\n",
        "partner_list_empty": (
            "🤝 אף אחד לא מחפש שותף ב-<b>{city}</b> כרגע.\n\n"
            "הבקשה שלך נשמרה — אשלח הודעה כשמישהו יופיע."
        ),
        "partner_remove_btn": "מצאתי שותף ✓",
        "partner_refresh_btn": "רענן",
        "partner_removed": "הבקשה שלך הוסרה.",
        "partner_already": (
            "כבר יש לך בקשה פעילה ב-<b>{city}</b> כ-{role}.\n\n"
            "עדכן או הסר אותה תחילה."
        ),
        "partner_notify_msg": (
            "👋 מישהו מחפש שותף לפרקטיקה ב-<b>{city}</b> היום!\n"
            "פתח את הבוט לצפייה ברשימה: /partner"
        ),
        "partner_nudge_msg": (
            "מצאת שותף לפרקטיקה ב-<b>{city}</b>?\n\n"
            "אם כן — לחץ למטה כדי להסיר את הבקשה."
        ),
        "partner_nudge_yes": "כן, הסר אותי ✓",
        "partner_nudge_no": "עדיין מחפש",
        "partner_nudge_still": "הבנתי — נשאר ברשימה.",
        "partner_no_username": (
            "⚠️ אין לך שם משתמש ב-Telegram.\n"
            "אחרים לא יוכלו לפנות אליך ישירות.\n\n"
            "אפשר להגדיר ב: הגדרות Telegram ← עריכת פרופיל ← שם משתמש."
        ),
        "partner_location_failed": "לא הצלחתי לזהות עיר מהמיקום. הכנס שם עיר:",
        "partner_city_failed": "לא הצלחתי לאמת את שם העיר כרגע. נסה שוב:",
    },
    "es": {
        "welcome": (
            "💃 <b>Milonga Finder</b>\n\n"
            "Te ayudo a encontrar milongas de tango en cualquier ciudad para hoy."
        ),
        "menu_prompt": "¿Qué deseas hacer?",
        "btn_find": "🔍 Buscar milongas hoy",
        "btn_donate": "☕ Apoyar el proyecto",
        "ask_city": "🏙 <b>Ingresa el nombre de la ciudad:</b>\n<i>por ejemplo: Budapest, Tel Aviv, Buenos Aires</i>",
        "searching": "🔍 Buscando milongas en <b>{city}</b>…\n<i>Esto puede tardar unos minutos mientras buscamos en internet.</i>",
        "no_events": (
            "😕 No se encontraron milongas ni prácticas en <b>{city}</b> hoy.\n\n"
            "Prueba otra ciudad o vuelve mañana."
        ),
        "city_not_found": (
            "🌍 Ciudad <b>{city}</b> no encontrada.\n\n"
            "Verifica la ortografía o prueba en inglés (ej: <i>Moscow</i>, <i>Tbilisi</i>)."
        ),
        "events_header": "💃 <b>Tango en {city}</b>\n📅 {date}\n",
        "back": "↩️ Volver",
        "donate_text": (
            "☕ <b>Apoyar Milonga Finder</b>\n\n"
            "Si el bot te ayuda a bailar más — ¡invítame un café!\n"
            "Cada ⭐ Estrella mantiene el bot en marcha."
        ),
        "donate_title": "Apoyar Milonga Finder",
        "donate_50": "☕ 50 ⭐",
        "donate_250": "🥐 250 ⭐",
        "donate_500": "🌟 500 ⭐",
        "donate_custom": "✏️ Cualquier monto",
        "ask_stars_amount": "Ingresa el monto en Stars (mínimo 50):",
        "invalid_stars": "⚠️ Ingresa un número válido (mínimo 50 Stars).",
        "close": "✖ Cerrar",
        "donate_desc_tip": "Una propina para apoyar Milonga Finder ☕",
        "donate_desc_30": "30 días de búsquedas ilimitadas en Milonga Finder",
        "donate_desc_90": "90 días de búsquedas ilimitadas en Milonga Finder",
        "donate_thanks": "🙏 ¡Muchas gracias! Tu apoyo es muy importante. ❤️",
        "paywall_button": "🔓 Desbloquear 24h — {stars} ⭐",
        "paywall_invoice_title": "Acceso ilimitado por 24 horas",
        "paywall_invoice_desc": "Desbloquea búsquedas ilimitadas de milongas por 24 horas",
        "paywall_thanks": "✅ ¡Acceso ilimitado desbloqueado por 24 horas!\nBuscando en <b>{city}</b>…",
        "paywall_unlocked": "✅ ¡Acceso ilimitado desbloqueado por 24 horas! Envíame una ciudad para buscar.",
        "rate_limit": (
            "⏳ Ya usaste tu única búsqueda de prueba gratuita.\n\n"
            "Desbloquea búsquedas ilimitadas por 24 horas por {stars} ⭐."
        ),
        "premium_granted": (
            "🎉 ¡Gracias! Búsquedas ilimitadas activadas por <b>{days} días</b> (hasta {until}). ❤️"
        ),
        "status_premium": "⭐ <b>Estado:</b> Premium hasta <b>{until}</b>. Búsquedas ilimitadas.",
        "status_free_available": "🔍 <b>Estado:</b> Tienes tu búsqueda de prueba gratuita disponible.",
        "status_free_used": "🔍 <b>Estado:</b> Ya usaste tu búsqueda de prueba gratuita. Desbloquea 24h ilimitadas por {stars} ⭐.",
        "free_trial_used": "\n\n<i>✅ Esa fue una búsqueda de prueba. La próxima vez, desbloquea 24h ilimitadas por {stars} ⭐.</i>",
        "disclaimer": "ℹ️ <i>Bot de IA — la información puede ser incompleta. Verifica siempre con el organizador.</i>",
        "error": "⚠️ Algo salió mal. Inténtalo de nuevo.",
        # Partner finder
        "btn_partner": "🤝 Buscar pareja para práctica",
        "partner_ask_role": "🕺 <b>¿Cuál es tu rol?</b>",
        "partner_role_leader": "Líder",
        "partner_role_follower": "Seguidor/a",
        "partner_role_both": "Puedo ambos",
        "partner_role_label_leader": "líder",
        "partner_role_label_follower": "seguidor/a",
        "partner_role_label_both": "líder/seguidor",
        "partner_ask_city": (
            "🏙 <b>¿A qué ciudad vas a practicar?</b>\n\n"
            "<i>Comparte tu ubicación o escribe el nombre de la ciudad.</i>"
        ),
        "partner_city_use_last": "Usar {city}",
        "partner_city_type": "Ingresar ciudad",
        "partner_share_location": "Compartir ubicación",
        "partner_ask_note": (
            "✏️ <b>¿Algo sobre ti?</b>\n"
            "<i>Nivel, estilo, lo que sea útil — opcional.</i>"
        ),
        "partner_note_skip": "Omitir",
        "partner_list_header": "🤝 <b>Buscan pareja en {city} hoy:</b>\n",
        "partner_list_empty": (
            "🤝 Nadie más busca pareja en <b>{city}</b> ahora.\n\n"
            "Tu solicitud está guardada — te avisaré cuando alguien aparezca."
        ),
        "partner_remove_btn": "Encontré pareja ✓",
        "partner_refresh_btn": "Actualizar",
        "partner_removed": "Tu solicitud fue eliminada.",
        "partner_already": (
            "Ya tienes una solicitud activa en <b>{city}</b> como {role}.\n\n"
            "Actualízala o elimínala primero."
        ),
        "partner_notify_msg": (
            "👋 ¡Alguien busca pareja para práctica en <b>{city}</b> hoy!\n"
            "Abre el bot para ver la lista: /partner"
        ),
        "partner_nudge_msg": (
            "¿Encontraste pareja para practicar en <b>{city}</b>?\n\n"
            "Si es así — toca abajo para eliminar tu solicitud."
        ),
        "partner_nudge_yes": "Sí, quitarme ✓",
        "partner_nudge_no": "Sigo buscando",
        "partner_nudge_still": "Entendido — sigues en la lista.",
        "partner_no_username": (
            "⚠️ No tienes nombre de usuario en Telegram.\n"
            "Otros no podrán contactarte directamente.\n\n"
            "Puedes configurarlo en: Ajustes de Telegram → Editar perfil → Nombre de usuario."
        ),
        "partner_location_failed": "No pude detectar la ciudad por tu ubicación. Escribe el nombre de la ciudad:",
        "partner_city_failed": "No pude verificar el nombre de la ciudad ahora. Inténtalo de nuevo:",
    },
}


def get_lang(language_code: str | None) -> str:
    if not language_code:
        return "en"
    return _LANG_MAP.get(language_code.split("-")[0].lower(), "en")


def t(lang: str, key: str) -> str:
    return MSG.get(lang, MSG["en"]).get(key, MSG["en"].get(key, key))
