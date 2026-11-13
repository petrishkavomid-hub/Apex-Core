const BOT_TOKEN = "8813383592:AAEq3jtBj3G9qeSr3KRSvUhOEFpmCHYfuog";
const ADMIN_ID = 5347874574;

const MAIN_MENU = {
  keyboard: [
    [{ text: "⭐ Оценить Apex AI" }, { text: "💬 Оставить отзыв" }],
    [{ text: "💡 Предложить идею" }, { text: "🛠 Сообщить о баге" }],
    [{ text: "📥 Скачать Apex AI" }]
  ],
  resize_keyboard: true
};

const STARS_MENU = {
  inline_keyboard: [
    [
      { text: "1 ⭐", callback_data: "rate_1" },
      { text: "2 ⭐", callback_data: "rate_2" },
      { text: "3 ⭐", callback_data: "rate_3" },
      { text: "4 ⭐", callback_data: "rate_4" },
      { text: "5 ⭐", callback_data: "rate_5" }
    ]
  ]
};

async function tg(method, body) {
  const host = "api.telegram." + "org";
  return fetch(`https://${host}/bot${BOT_TOKEN}/${method}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body)
  });
}

export default {
  async fetch(request) {
    if (request.method !== "POST") {
      const res = await tg("setWebhook", { url: new URL(request.url).origin });
      return new Response(await res.text());
    }

    const update = await request.json();

    if (update.callback_query) {
      const cq = update.callback_query;
      const from = cq.from;
      const stars = cq.data.replace("rate_", "");
      const userTag = from.username ? `@${from.username}` : `${from.first_name} (ID: ${from.id})`;

      await tg("answerCallbackQuery", { callback_query_id: cq.id, text: `Спасибо за ${stars} ⭐!` });
      await tg("editMessageText", {
        chat_id: cq.message.chat.id,
        message_id: cq.message.message_id,
        text: `✅ Вы поставили оценку: ${"⭐".repeat(Number(stars))} (${stars}/5)\n\nСпасибо за поддержку проекта Apex AI by Derek Stealth! Вы также можете написать пару слов в разделе «💬 Оставить отзыв».`
      });

      await tg("sendMessage", {
        chat_id: ADMIN_ID,
        text: `⭐ НОВАЯ ОЦЕНКА ПРИЛОЖЕНИЯ!\n\nОценка: ${"⭐".repeat(Number(stars))} (${stars}/5)\nОт: ${userTag}\nUserID: #id${from.id}`
      });
      return new Response("OK");
    }

    if (update.message) {
      const msg = update.message;
      const chatId = msg.chat.id;
      const text = msg.text || "";
      const userTag = msg.from.username ? `@${msg.from.username}` : `${msg.from.first_name} (ID: ${msg.from.id})`;

      if (chatId === ADMIN_ID && msg.reply_to_message && msg.reply_to_message.text) {
        const match = msg.reply_to_message.text.match(/#id(\d+)/);
        if (match) {
          const targetUserId = Number(match);
          await tg("sendMessage", {
            chat_id: targetUserId,
            text: `📩 Ответ от разработчика Derek Stealth:\n\n${text}`
          });
          await tg("sendMessage", { chat_id: ADMIN_ID, text: "✅ Ответ отправлен пользователю!" });
          return new Response("OK");
        }
      }

      if (text === "/start") {
        await tg("sendMessage", {
          chat_id: chatId,
          text: "Здравствуйте! Это официальный бот поддержки и обратной связи сервиса Apex AI Assistant (разработчик — Derek Stealth).\n\nЗдесь вы можете:\n⭐ Оценить работу ассистента по шкале от 1 до 5\n💬 Оставить свой отзыв о приложении\n💡 Предложить идею для будущих обновлений\n🛠 Сообщить об обнаруженной ошибке или задать вопрос техподдержке\n📥 Перейти к скачиванию актуальной версии\n\nВыберите нужный раздел в меню ниже 👇",
          reply_markup: MAIN_MENU
        });
      } else if (text === "⭐ Оценить Apex AI") {
        await tg("sendMessage", {
          chat_id: chatId,
          text: "Оцените работу Apex AI Assistant по шкале от 1 до 5 звёзд:",
          reply_markup: STARS_MENU
        });
      } else if (text === "📥 Скачать Apex AI") {
        await tg("sendMessage", {
          chat_id: chatId,
          text: "📥 Актуальная сборка Apex AI Assistant всегда доступна в нашем официальном канале:\n👉 @Apexassistantcore",
          reply_markup: MAIN_MENU
        });
      } else if (text === "💬 Оставить отзыв") {
        await tg("sendMessage", {
          chat_id: chatId,
          text: "✍️ Напишите ваш отзыв одним следующим сообщением — он сразу попадёт разработчику!",
          reply_markup: MAIN_MENU
        });
      } else if (text === "💡 Предложить идею") {
        await tg("sendMessage", {
          chat_id: chatId,
          text: "💡 Опишите вашу идею для нового обновления одним сообщением:",
          reply_markup: MAIN_MENU
        });
      } else if (text === "🛠 Сообщить о баге") {
        await tg("sendMessage", {
          chat_id: chatId,
          text: "🛠 Опишите проблему и укажите модель вашего смартфона одним сообщением:",
          reply_markup: MAIN_MENU
        });
      } else if (text.length > 1) {
        await tg("sendMessage", {
          chat_id: ADMIN_ID,
          text: `📨 НОВОЕ ОБРАЩЕНИЕ В БОТА\n\nОт: ${userTag}\nUserID: #id${msg.from.id}\n\nСообщение:\n${text}\n\n(Чтобы ответить человеку, сделайте «Ответить» на это сообщение)`
        });
        await tg("sendMessage", {
          chat_id: chatId,
          text: "✅ Принято! Ваше сообщение передано разработчику Derek Stealth. Спасибо за обратную связь!",
          reply_markup: MAIN_MENU
        });
      }
    }
    return new Response("OK");
  }
};
