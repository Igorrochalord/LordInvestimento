import yfinance as yf
import json
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from apscheduler.schedulers.background import BackgroundScheduler

TOKEN = "7217509449:AAEMm44cURd-m-EfRuSabxa0qUjE-_2BEic"
symbols_file = "/home/igor-rocha/Projetos/LordInvestidor/symbols.json"

acoes_principais = {
    "PETR4.SA": "⛽",
    "VALE3.SA": "🛢️",
    "ITUB4.SA": "🏦",
    "BBDC4.SA": "💳",
    "ABEV3.SA": "🍺",
}

def load_symbols():
    try:
        with open(symbols_file, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return {}

def save_symbols(symbols):
    try:
        with open(symbols_file, "w") as file:
            json.dump(symbols, file)
    except Exception as e:
        print(f"Erro ao salvar o arquivo: {e}")

def get_price_variation(symbol):
    ticker = yf.Ticker(symbol)
    data = ticker.history(period="5d")
    if len(data) < 2:
        return None, None, None

    previous_close = data['Close'].iloc[-2]
    current_price = data['Close'].iloc[-1]
    change = current_price - previous_close
    emoji = "🔼" if change > 0 else "🔽"

    icon = acoes_principais.get(symbol, "📊")
    return current_price, change, emoji, icon

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mensagem_boas_vindas = "Bem-vindo! Aqui estão os preços de algumas ações do IBOVESPA:\n\n"
    for symbol, icon in acoes_principais.items():
        price, change, emoji, _ = get_price_variation(symbol)
        if price is not None:
            mensagem_boas_vindas += (
                f"{icon} {symbol}: R${price:.2f} {emoji} "
                f"({change:+.2f})\n"
            )
        else:
            mensagem_boas_vindas += f"{icon} {symbol}: Dados indisponíveis\n"

    mensagem_boas_vindas += "\nUse /add para adicionar os símbolos que deseja acompanhar."
    mensagem_boas_vindas += "\nExemplo: /add PETR4.SA VALE3.SA BTC-USD"
    await update.message.reply_text(mensagem_boas_vindas)

async def add_symbol(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_chat.id
    new_symbols = context.args
    if len(new_symbols) > 10:
        await update.message.reply_text("Você pode acompanhar até 10 símbolos.")
        return

    symbols = load_symbols()
    if str(user_id) in symbols:
        symbols[str(user_id)].extend(new_symbols)
    else:
        symbols[str(user_id)] = new_symbols

    symbols[str(user_id)] = symbols[str(user_id)][:4]
    save_symbols(symbols)
    await update.message.reply_text(f"Símbolos adicionados: {', '.join(new_symbols)}")

async def remove_symbol(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_chat.id
    symbol_to_remove = context.args[0] if context.args else None
    if not symbol_to_remove:
        await update.message.reply_text("Por favor, forneça o símbolo para remover (exemplo: /remove PETR4.SA).")
        return

    symbols = load_symbols()
    user_symbols = symbols.get(str(user_id), [])

    if symbol_to_remove in user_symbols:
        user_symbols.remove(symbol_to_remove)
        symbols[str(user_id)] = user_symbols
        save_symbols(symbols)
        await update.message.reply_text(f"Símbolo {symbol_to_remove} removido com sucesso.")
    else:
        await update.message.reply_text(f"Símbolo {symbol_to_remove} não encontrado na sua lista.")

async def show_symbols(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_chat.id
    symbols = load_symbols()

    if str(user_id) not in symbols or not symbols[str(user_id)]:
        await update.message.reply_text("Você ainda não adicionou nenhum símbolo. Use /add para começar!")
    else:
        user_symbols = symbols[str(user_id)]
        mensagem = "Você está acompanhando os seguintes símbolos:\n"
        
        for symbol in user_symbols:
            price, change, emoji, icon = get_price_variation(symbol)
            if price is not None:
                mensagem += f"{icon} {symbol}: R${price:.2f} {emoji} ({change:+.2f})\n"
            else:
                mensagem += f"{symbol}: Dados indisponíveis\n"
        
        await update.message.reply_text(mensagem)

async def enviar_updates(application: Application):
    symbols = load_symbols()
    updates = []
    for user_id, user_symbols in symbols.items():
        mensagem = "Atualizações de preços:\n"
        for symbol in user_symbols:
            price, change, emoji, icon = get_price_variation(symbol)
            if price is not None:
                mensagem += f"{icon} {symbol}: R${price:.2f} {emoji} ({change:+.2f})\n"
            else:
                mensagem += f"{symbol}: Dados indisponíveis\n"
        updates.append((user_id, mensagem))

    for user_id, message in updates:
        await application.bot.send_message(chat_id=user_id, text=message)

def start_scheduler(application: Application):
    scheduler = BackgroundScheduler()
    scheduler.add_job(lambda: application.create_task(enviar_updates(application)), 'interval', minutes=30)
    scheduler.start()

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_message = (
        "Bem-vindo ao bot de acompanhamento de ações!\n\n"
        "Aqui estão os comandos disponíveis:\n\n"
        "/start - Inicia o bot e exibe as principais ações do IBOVESPA.\n"
        "/add <símbolos> - Adiciona símbolos para acompanhar (exemplo: /add PETR4.SA VALE3.SA).\n"
        "/show - Exibe os símbolos que você está acompanhando com as variações de preço.\n"
        "/remove <símbolo> - Remove um símbolo da sua lista de acompanhamento.\n"
        "/news - Exibe as últimas notícias financeiras (a ser implementado como um canal).\n"
        "/help - Exibe esta mensagem de ajuda.\n\n"
        "Você pode acompanhar até 4 símbolos simultaneamente.\n"
        "Os símbolos disponíveis incluem ações da B3 e criptomoedas (exemplo: BTC-USD, ETH-USD).\n"
        "Use /add para começar a acompanhar suas ações e criptomoedas favoritas."
    )

    await update.message.reply_text(help_message)

def main():
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("add", add_symbol))
    application.add_handler(CommandHandler("remove", remove_symbol))
    application.add_handler(CommandHandler("show", show_symbols))
    application.add_handler(CommandHandler("help", help_command))

    start_scheduler(application)
    application.run_polling()

if __name__ == "__main__":
    main()
